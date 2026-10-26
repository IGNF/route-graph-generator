import time
from os import getenv

import psycopg2
from psycopg2 import OperationalError, DatabaseError, InterfaceError
from psycopg2.extras import DictCursor

TIMEOUT = int(getenv("SQL_STATEMENT_TIMEOUT", 0))
RETRY = int(getenv("SQL_STATEMENT_RETRY_ATTEMPTS", 3))
DELAY = int(getenv("SQL_DELAY_BETWEEN_STATEMENTS", 30))
# TCP keepalives: keep idle connections alive through firewalls/NAT and detect dead connections quickly
KEEPALIVES_IDLE = int(getenv("SQL_KEEPALIVES_IDLE", 60))
KEEPALIVES_INTERVAL = int(getenv("SQL_KEEPALIVES_INTERVAL", 10))
KEEPALIVES_COUNT = int(getenv("SQL_KEEPALIVES_COUNT", 5))


def database_retry_decorator(func):
    def wrapper(self, *args, **kwargs):
        attempt = 1
        while attempt <= RETRY:
            try:
                self.ensure_connection()
                yield from func(self, *args, **kwargs)
                return

            except (OperationalError, DatabaseError, InterfaceError) as e:
                if attempt >= RETRY:
                    self.logger.error(f"Query failed after {RETRY} attempts: {str(e).rstrip()}")
                    raise e

                self.logger.error(
                    f"Attempt {attempt}/{RETRY} failed ({str(e).rstrip()}), retrying in {DELAY} seconds"
                )
                time.sleep(DELAY)
                attempt += 1
                try:
                    if self._connection:
                        self._connection.rollback()
                except Exception as e:
                    self.logger.error(f"Connection rollback failed {str(e).rstrip()}")
        return

    return wrapper


class DatabaseManager:
    def __init__(self, db_configs, logger):
        self.logger = logger
        self._work_db_config = db_configs
        self._connection = self.connect_working_db()

    def connect_working_db(self):
        """
        Fonction de connexion à la BDD de travail

        Parameters
        ----------
        config: dict
            dictionnaire correspondant à la configuration décrite dans le fichier passé en argument
        db_configs: dict
            dictionnaire correspondant aux configurations des bdd
        Returns
        -------
        connection: psycopg2.connection
            connection à la bdd de travail

        """
        # Récupération des paramètres de la bdd
        host = self._work_db_config.get("host")
        dbname = self._work_db_config.get("database")
        user = self._work_db_config.get("user")
        password = self._work_db_config.get("password")
        port = self._work_db_config.get("port")
        connect_args = "host=%s dbname=%s user=%s password=%s port=%s" % (host, dbname, user, password, port)

        connect_kwargs = {
            "keepalives": 1,
            "keepalives_idle": KEEPALIVES_IDLE,
            "keepalives_interval": KEEPALIVES_INTERVAL,
            "keepalives_count": KEEPALIVES_COUNT,
        }
        if TIMEOUT:
            connect_kwargs["options"] = f"-c statement_timeout={TIMEOUT * 1000}"

        self.logger.info("Connecting to work database")
        connection = psycopg2.connect(connect_args, **connect_kwargs)
        connection.set_client_encoding("UTF8")

        return connection

    def disconnect_working_db(self):
        """
        Fonction de connexion à la BDD de travail

        Parameters
        ----------
        connection: psycopg2.connection
            connection à la bdd de travail
        logger: logging.Logger
        """
        if self._connection:
            self._connection.close()
            self.logger.info("Connection to work database closed")

    def ensure_connection(self):
        """
        Ensure the connection is alive; reconnect if needed.
        """
        try:
            if self._connection is None or getattr(self._connection, "closed", 1) != 0:
                self.logger.info("Connection is closed or missing; reconnecting")
                self._connection = self.connect_working_db()
            else:
                with self._connection.cursor() as cur:
                    cur.execute("SELECT 1")
        except Exception as e:
            self.logger.error(
                f"Something is wrong with the connection: {str(e).rstrip()}; reconnecting in {DELAY} seconds")
            self.disconnect_working_db()
            time.sleep(DELAY)
            self._connection = self.connect_working_db()

    # IMPORTANT:
    # Streaming SELECTs must NOT use retry logic.
    # If the connection drops, the cursor state is unrecoverable.
    def execute_select_fetch_multiple(self, query, batchsize=1, show_duration=False):
        """
        Streaming SELECT using a named server-side cursor.
        No retry. No reconnect. No commit.
        Fail fast if the connection drops (old behavior).
        """
        self.ensure_connection()
        cursor_name = f"cursor_{int(time.time() * 1000)}"
        try:
            with self._connection.cursor(cursor_factory=DictCursor, name=cursor_name) as cursor:
                if show_duration:
                    self.logger.info(f"SQL: {query}")
                    st = time.time()
                    cursor.execute(query)
                    self.logger.info(
                        "Execution ended. Elapsed time : %s seconds.",
                        time.time() - st
                    )
                else:
                    cursor.execute(query)

                count = cursor.rowcount

                while True:
                    rows = cursor.fetchmany(batchsize)
                    if not rows:
                        break
                    if batchsize == 1:
                        rows = rows.pop()
                    yield rows, count
        finally:
            if self._connection and self._connection.closed == 0:
              try:
                  self._connection.commit()
              except Exception:
                  pass

    @database_retry_decorator
    def execute_select_query(self, query, show_duration=False):
        """
        Plain SELECT fetching all rows in a short transaction, with retry.
        Generator yielding the list of rows once (required by database_retry_decorator).
        """
        if show_duration:
            self.logger.info(f"SQL: {query}")
        st = time.time()
        with self._connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
        self._connection.commit()
        if show_duration:
            self.logger.info("Execution ended. Elapsed time : %s seconds.", time.time() - st)
        yield rows

    def execute_select_fetch_by_id_batches(self, build_query, batchsize, show_duration=False):
        """
        Keyset-paginated SELECT on the "id" column.
        Each batch is an independent short query with retry, so a connection loss
        only replays the current batch instead of failing the whole export.

        Parameters
        ----------
        build_query: callable
            build_query(last_id) must return a query filtered on "id > last_id"
            (no filter when last_id is None) and ordered by id ASC, without LIMIT.
        batchsize: int
        show_duration: bool
            log the query and duration of the first batch only

        Yields
        ------
        list of rows
        """
        last_id = None
        first = True
        while True:
            query = f"{build_query(last_id)} LIMIT {int(batchsize)}"
            rows = next(self.execute_select_query(query, show_duration=show_duration and first))
            first = False
            if not rows:
                return
            yield rows
            if len(rows) < batchsize:
                return
            last_id = rows[-1]["id"]

    # the method below should be used as a generator function otherwise use execute_update
    @database_retry_decorator
    def execute_update_query(self, query, params=None, isolation_level=None, show_duration=False):
        self.ensure_connection()
        if show_duration :
            self.logger.info("SQL: {}".format(query))
        st_execute = time.time()
        with self._connection.cursor(cursor_factory=DictCursor) as cursor:
            old_isolation_level = self._connection.isolation_level
            try:
                if isolation_level is not None:
                    self._connection.set_isolation_level(isolation_level)
                cursor.execute(query, params)
                self._connection.commit()
            finally:
                self._connection.set_isolation_level(old_isolation_level)
            if show_duration:
                et_execute = time.time()
                self.logger.info("Execution ended. Elapsed time : %s seconds." % (et_execute - st_execute))
        yield  # the decorator database_retry_decorator only supports generators
        return

    def execute_update(self, query, params=None, isolation_level=None):
        next(self.execute_update_query(query, params=params, isolation_level=isolation_level), None)

    def execute_select_fetch_one(self, query, show_duration=False):
        try:
            gen = self.execute_select_fetch_multiple(query, 1, show_duration)
            row, count = next(gen, (None, None))
            return row, count
        finally:
            gen.close()  # Ensure the generator is closed to free resources
