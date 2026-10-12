"""Shared pytest fixtures."""
import pytest

from aceest import create_app


@pytest.fixture
def app(tmp_path):
    """A fresh app backed by a throwaway SQLite file for every test."""
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.db"),
        # A cheap hash keeps the suite fast; production uses scrypt.
        "PASSWORD_HASH_METHOD": "pbkdf2:sha256:1000",
    })
    yield app


@pytest.fixture
def client(app):
    return app.test_client()
