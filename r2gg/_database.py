import time
from os import getenv

import psycopg2
from psycopg2 import OperationalError, DatabaseError, InterfaceError
from psycopg2.extras import DictCursor
import logging

TIMEOUT = int(getenv("SQL_STATEMENT_TIMEOUT", 0))
RETRY = int(getenv("SQL_STATEMENT_RETRY_ATTEMPTS", 3))
DELAY = int(getenv("SQL_DELAY_BETWEEN_STATEMENTS", 30))


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
                    return

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

        self.logger.info("Connecting to work database")
        connection = psycopg2.connect(connect_args)
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

    def execute_select_query(self, cursor, query, show_duration):
        if TIMEOUT:
            cursor.execute("SET statement_timeout = %s", (1000 * TIMEOUT,))  # timeout in milliseconds

        if show_duration:
            self.logger.info("SQL: {}".format(query))
            st_execute = time.time()
            cursor.execute(query)
            et_execute = time.time()
            self.logger.info("Execution ended. Elapsed time : %s seconds." % (et_execute - st_execute))
        else:
            cursor.execute(query)

    @database_retry_decorator
    def execute_select_fetch_multiple(self, query, batchsize=1, show_duration=False):
        with self._connection.cursor(cursor_factory=DictCursor) as cursor:
            self.execute_select_query(cursor, query, show_duration)
            rows = cursor.fetchmany(batchsize)
            count = cursor.rowcount
            while rows:
                if batchsize == 1:
                    rows = rows.pop()
                yield rows, count
                rows = cursor.fetchmany(batchsize)
            self._connection.commit()
            return

    # the method below should be used as a generator function otherwise use execute_update
    @database_retry_decorator
    def execute_update_query(self, query, params=None, isolation_level=None, show_duration=False):
        if show_duration :
            self.logger.info("SQL: {}".format(query))
        st_execute = time.time()
        with self._connection.cursor(cursor_factory=DictCursor) as cursor:
            old_isolation_level = self._connection.isolation_level
            if isolation_level is not None:
                self._connection.set_isolation_level(isolation_level)
            cursor.execute(query, params)
            self._connection.commit()
            if show_duration:
                et_execute = time.time()
                self.logger.info("Execution ended. Elapsed time : %s seconds." % (et_execute - st_execute))
            self._connection.set_isolation_level(old_isolation_level)
        yield  # the decorator database_retry_decorator only supports generators
        return

    def execute_update(self, query, params=None, isolation_level=None):
        next(self.execute_update_query(query, params=params, isolation_level=isolation_level), None)

    def execute_select_fetch_one(self, query, show_duration=False):
        gen = self.execute_select_fetch_multiple(query, 1, show_duration)
        row, count = next(gen, (None, None))
        return row, count
