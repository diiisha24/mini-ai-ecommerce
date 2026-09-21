from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

settings = get_settings()


def normalize_database_url(url: str) -> str:
    """Managed Postgres providers (Render, Railway, Heroku-style, ...) hand back a plain
    postgres:// or postgresql:// connection string with no driver suffix. SQLAlchemy
    defaults an unsuffixed postgresql:// URL to the psycopg2 dialect, which isn't
    installed here - this project uses psycopg 3 (the `psycopg[binary]` package,
    imported as `psycopg`). Force the +psycopg driver regardless of what scheme we're
    handed, so this works the same locally and against any managed provider."""
    plain_scheme = "postgresql://"
    if url.startswith("postgres://"):
        url = plain_scheme + url[len("postgres://") :]
    if url.startswith(plain_scheme) and "+psycopg" not in url:
        url = "postgresql+psycopg://" + url[len(plain_scheme) :]
    return url


engine = create_engine(normalize_database_url(settings.database_url), echo=False)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
