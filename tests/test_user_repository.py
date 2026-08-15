from src.server.db.repository.user_repository import normalize_user_id


def test_normalize_user_id_for_postgres_integer_primary_key():
    assert normalize_user_id("42") == 42
    assert normalize_user_id(7) == 7
    assert normalize_user_id("invalid") == "invalid"
