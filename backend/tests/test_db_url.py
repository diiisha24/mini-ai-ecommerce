"""Managed Postgres providers hand back connection strings in whatever scheme they
feel like - this must always resolve to the psycopg3 driver we actually have installed."""

from app.db import normalize_database_url


def test_leaves_explicit_psycopg_url_untouched():
    url = "postgresql+psycopg://user:pw@host:5432/db"
    assert normalize_database_url(url) == url


def test_adds_psycopg_driver_to_plain_postgresql_url():
    url = "postgresql://user:pw@host:5432/db"
    assert normalize_database_url(url) == "postgresql+psycopg://user:pw@host:5432/db"


def test_normalizes_legacy_postgres_scheme():
    # Render, Heroku, and others sometimes use the old "postgres://" scheme.
    url = "postgres://user:pw@host:5432/db"
    assert normalize_database_url(url) == "postgresql+psycopg://user:pw@host:5432/db"
