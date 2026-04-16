from __future__ import annotations

from app import main


def test_run_uses_default_host_and_port(monkeypatch) -> None:
    calls = {}

    def fake_run(app_target: str, *, host: str, port: int, reload: bool, workers: int, log_level: str) -> None:
        calls["app_target"] = app_target
        calls["host"] = host
        calls["port"] = port
        calls["reload"] = reload
        calls["workers"] = workers
        calls["log_level"] = log_level

    monkeypatch.setattr(main.uvicorn, "run", fake_run)
    monkeypatch.setattr(main, "DEFAULT_WEB_HOST", "127.0.0.1")
    monkeypatch.setattr(main, "DEFAULT_WEB_PORT", 18110)
    monkeypatch.setattr(
        main.argparse.ArgumentParser,
        "parse_args",
        lambda self: type("Args", (), {"host": None, "port": None, "reload": False, "workers": None, "log_level": None})(),
    )
    monkeypatch.delenv("SKILLLINT_WEB_HOST", raising=False)
    monkeypatch.delenv("SKILLLINT_WEB_PORT", raising=False)
    monkeypatch.delenv("SKILLLINT_WEB_RELOAD", raising=False)
    monkeypatch.delenv("SKILLLINT_WEB_WORKERS", raising=False)
    monkeypatch.delenv("SKILLLINT_WEB_LOG_LEVEL", raising=False)

    main.run()

    assert calls == {
        "app_target": "app.main:app",
        "host": "127.0.0.1",
        "port": 18110,
        "reload": False,
        "workers": 1,
        "log_level": "info",
    }


def test_run_allows_cli_override_for_external_access(monkeypatch) -> None:
    calls = {}

    def fake_run(app_target: str, *, host: str, port: int, reload: bool, workers: int, log_level: str) -> None:
        calls["host"] = host
        calls["port"] = port
        calls["reload"] = reload
        calls["workers"] = workers
        calls["log_level"] = log_level

    monkeypatch.setattr(main.uvicorn, "run", fake_run)
    monkeypatch.setattr(
        main.argparse.ArgumentParser,
        "parse_args",
        lambda self: type("Args", (), {"host": "0.0.0.0", "port": 19000, "reload": False, "workers": 2, "log_level": "warning"})(),
    )

    main.run()

    assert calls["host"] == "0.0.0.0"
    assert calls["port"] == 19000
    assert calls["reload"] is False
    assert calls["workers"] == 2
    assert calls["log_level"] == "warning"


def test_run_reads_env_when_cli_not_set(monkeypatch) -> None:
    calls = {}

    def fake_run(app_target: str, *, host: str, port: int, reload: bool, workers: int, log_level: str) -> None:
        calls["host"] = host
        calls["port"] = port
        calls["reload"] = reload
        calls["workers"] = workers
        calls["log_level"] = log_level

    monkeypatch.setattr(main.uvicorn, "run", fake_run)
    monkeypatch.setattr(
        main.argparse.ArgumentParser,
        "parse_args",
        lambda self: type("Args", (), {"host": None, "port": None, "reload": False, "workers": None, "log_level": None})(),
    )
    monkeypatch.setenv("SKILLLINT_WEB_HOST", "0.0.0.0")
    monkeypatch.setenv("SKILLLINT_WEB_PORT", "18111")
    monkeypatch.setenv("SKILLLINT_WEB_RELOAD", "true")
    monkeypatch.setenv("SKILLLINT_WEB_WORKERS", "1")
    monkeypatch.setenv("SKILLLINT_WEB_LOG_LEVEL", "debug")

    main.run()

    assert calls["host"] == "0.0.0.0"
    assert calls["port"] == 18111
    assert calls["reload"] is True
    assert calls["workers"] == 1
    assert calls["log_level"] == "debug"


def test_run_rejects_reload_with_multiple_workers(monkeypatch) -> None:
    monkeypatch.setattr(
        main.argparse.ArgumentParser,
        "parse_args",
        lambda self: type("Args", (), {"host": None, "port": None, "reload": True, "workers": 2, "log_level": None})(),
    )

    try:
        main.run()
    except ValueError as exc:
        assert "reload mode" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError")
