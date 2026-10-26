import logging
from unittest import mock

import pytest
from psycopg2 import OperationalError

import r2gg._database as db_module
from r2gg._database import DatabaseManager


def make_manager(results):
    """DatabaseManager whose cursor.fetchall() returns (or raises) the given results in order."""
    with mock.patch.object(DatabaseManager, "connect_working_db", return_value=mock.MagicMock(closed=0)):
        manager = DatabaseManager({}, logging.getLogger("test"))
    manager.ensure_connection = mock.MagicMock()
    cursor = manager._connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.side_effect = results
    return manager, cursor


def build_query(last_id):
    return "SELECT * FROM t ORDER BY id" if last_id is None else f"SELECT * FROM t WHERE id > {last_id} ORDER BY id"


def test_keyset_pagination_uses_last_id():
    manager, cursor = make_manager([
        [{"id": 1}, {"id": 2}],
        [{"id": 5}, {"id": 7}],
        [{"id": 9}],
    ])

    batches = list(manager.execute_select_fetch_by_id_batches(build_query, 2))

    assert [[r["id"] for r in b] for b in batches] == [[1, 2], [5, 7], [9]]
    queries = [c.args[0] for c in cursor.execute.call_args_list]
    assert queries == [
        "SELECT * FROM t ORDER BY id LIMIT 2",
        "SELECT * FROM t WHERE id > 2 ORDER BY id LIMIT 2",
        "SELECT * FROM t WHERE id > 7 ORDER BY id LIMIT 2",
    ]


def test_keyset_pagination_retries_failed_batch(monkeypatch):
    monkeypatch.setattr(db_module, "DELAY", 0)
    manager, cursor = make_manager([
        [{"id": 1}, {"id": 2}],
        OperationalError("could not receive data from server: Connection timed out"),
        [{"id": 3}],
    ])

    batches = list(manager.execute_select_fetch_by_id_batches(build_query, 2))

    assert [[r["id"] for r in b] for b in batches] == [[1, 2], [3]]
    queries = [c.args[0] for c in cursor.execute.call_args_list]
    assert queries[1] == queries[2] == "SELECT * FROM t WHERE id > 2 ORDER BY id LIMIT 2"


def test_keyset_pagination_raises_after_max_retries(monkeypatch):
    monkeypatch.setattr(db_module, "DELAY", 0)
    monkeypatch.setattr(db_module, "RETRY", 2)
    manager, _ = make_manager([OperationalError("boom"), OperationalError("boom")])

    with pytest.raises(OperationalError):
        list(manager.execute_select_fetch_by_id_batches(build_query, 2))
