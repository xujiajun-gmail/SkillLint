from __future__ import annotations

from app import main


def test_run_uses_default_host_and_port(monkeypatch) -> None:
    calls = {}

    def fake_run(app_target: str, *, host: str, port: int, reload: bool) -> None:
        calls["app_target"] = app_target
        calls["host"] = host
        calls["port"] = port
        calls["reload"] = reload

    monkeypatch.setattr(main.uvicorn, "run", fake_run)
    monkeypatch.setattr(main, "DEFAULT_WEB_HOST", "127.0.0.1")
    monkeypatch.setattr(main, "DEFAULT_WEB_PORT", 18110)
    monkeypatch.setattr(main.argparse.ArgumentParser, "parse_args", lambda self: type("Args", (), {"host": None, "port": None})())
    monkeypatch.delenv("SKILLLINT_WEB_HOST", raising=False)
    monkeypatch.delenv("SKILLLINT_WEB_PORT", raising=False)

    main.run()

    assert calls == {
        "app_target": "app.main:app",
        "host": "127.0.0.1",
        "port": 18110,
        "reload": False,
    }


def test_run_allows_cli_override_for_external_access(monkeypatch) -> None:
    calls = {}

    def fake_run(app_target: str, *, host: str, port: int, reload: bool) -> None:
        calls["host"] = host
        calls["port"] = port

    monkeypatch.setattr(main.uvicorn, "run", fake_run)
    monkeypatch.setattr(
        main.argparse.ArgumentParser,
        "parse_args",
        lambda self: type("Args", (), {"host": "0.0.0.0", "port": 19000})(),
    )

    main.run()

    assert calls["host"] == "0.0.0.0"
    assert calls["port"] == 19000


def test_run_reads_env_when_cli_not_set(monkeypatch) -> None:
    calls = {}

    def fake_run(app_target: str, *, host: str, port: int, reload: bool) -> None:
        calls["host"] = host
        calls["port"] = port

    monkeypatch.setattr(main.uvicorn, "run", fake_run)
    monkeypatch.setattr(main.argparse.ArgumentParser, "parse_args", lambda self: type("Args", (), {"host": None, "port": None})())
    monkeypatch.setenv("SKILLLINT_WEB_HOST", "0.0.0.0")
    monkeypatch.setenv("SKILLLINT_WEB_PORT", "18111")

    main.run()

    assert calls["host"] == "0.0.0.0"
    assert calls["port"] == 18111
