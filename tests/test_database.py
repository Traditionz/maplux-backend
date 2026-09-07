import pytest

from database import create_all_tables, engine_connect_args, get_db


def test_engine_connect_args():
    assert engine_connect_args("sqlite:///./Maplux.sqlite") == {"check_same_thread": False}
    assert engine_connect_args("postgresql://localhost/maplux") == {}


def test_create_all_tables(monkeypatch):
    called = []
    monkeypatch.setattr(
        "database.Base.metadata.create_all", lambda bind: called.append(bind)
    )
    create_all_tables()
    assert called


def test_get_db_closes_and_rollbacks(monkeypatch):
    events: list[str] = []

    class DummySession:
        def rollback(self) -> None:
            events.append("rollback")

        def close(self) -> None:
            events.append("close")

    monkeypatch.setattr("database.SessionLocal", DummySession)
    gen = get_db()
    session = next(gen)
    assert isinstance(session, DummySession)
    gen.close()
    assert events == ["close"]

    gen = get_db()
    next(gen)
    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("boom"))
    assert "rollback" in events
    assert events[-1] == "close"
