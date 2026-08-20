"""
Point tests at a throwaway SQLite file so pytest does not need MySQL or LLM keys.
Must set DATABASE_URL before any backend module import.
"""
import os
from pathlib import Path

_TEST_DB = Path(__file__).resolve().parent / "_ava_test.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB.as_posix()

import pytest
from fastapi.testclient import TestClient

from seed import seed_job_roles


@pytest.fixture(scope="session", autouse=True)
def _sqlite_roles():
    seed_job_roles()
    yield
    if _TEST_DB.exists():
        try:
            _TEST_DB.unlink()
        except OSError:
            pass


@pytest.fixture
def client():
    from main import app, SESSIONS

    SESSIONS.clear()
    with TestClient(app) as test_client:
        yield test_client
    SESSIONS.clear()
