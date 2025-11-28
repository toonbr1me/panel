"""Test for database URL normalization to ensure async drivers are used."""



def test_normalize_sqlite_url_without_driver():
    """Test that sqlite:// URLs are normalized to sqlite+aiosqlite://"""
    from app.db.base import normalize_database_url

    result = normalize_database_url("sqlite:///db.sqlite3")
    assert result == "sqlite+aiosqlite:///db.sqlite3"


def test_normalize_sqlite_url_already_has_driver():
    """Test that sqlite+aiosqlite:// URLs are not modified"""
    from app.db.base import normalize_database_url

    result = normalize_database_url("sqlite+aiosqlite:///db.sqlite3")
    assert result == "sqlite+aiosqlite:///db.sqlite3"


def test_normalize_sqlite_memory_url():
    """Test that sqlite:///:memory: URLs are normalized correctly"""
    from app.db.base import normalize_database_url

    result = normalize_database_url("sqlite:///:memory:")
    assert result == "sqlite+aiosqlite:///:memory:"


def test_normalize_postgresql_url_unchanged():
    """Test that PostgreSQL URLs are not modified"""
    from app.db.base import normalize_database_url

    url = "postgresql+asyncpg://user:pass@localhost:5432/db"
    result = normalize_database_url(url)
    assert result == url


def test_normalize_mysql_url_unchanged():
    """Test that MySQL URLs are not modified"""
    from app.db.base import normalize_database_url

    url = "mysql+asyncmy://root:pass@127.0.0.1/db"
    result = normalize_database_url(url)
    assert result == url


def test_normalize_absolute_path_sqlite():
    """Test normalization of SQLite URL with absolute path"""
    from app.db.base import normalize_database_url

    result = normalize_database_url("sqlite:////var/lib/data/db.sqlite3")
    assert result == "sqlite+aiosqlite:////var/lib/data/db.sqlite3"
