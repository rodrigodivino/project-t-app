import pytest
from unittest.mock import MagicMock

from app.sources.service import execute_query


def test_execute_query_rejects_non_select():
    db = MagicMock()
    with pytest.raises(ValueError, match="Only SELECT"):
        execute_query(db, "DELETE FROM post_rede_social_himark")


def test_execute_query_rejects_insert():
    db = MagicMock()
    with pytest.raises(ValueError, match="Only SELECT"):
        execute_query(db, "INSERT INTO post_rede_social_himark VALUES (1, 'a', 'b', 'c', 'd')")


def test_execute_query_runs_select():
    db = MagicMock()
    mock_result = MagicMock()
    mock_result.keys.return_value = ["time", "location", "account", "message"]
    mock_result.fetchall.return_value = [
        ("2020-04-06", "Broadview", "user1", "hello"),
    ]
    db.execute.return_value = mock_result
    rows = execute_query(db, "SELECT * FROM post_rede_social_himark LIMIT 1")
    assert len(rows) == 1
    assert rows[0]["location"] == "Broadview"
    assert rows[0]["message"] == "hello"
