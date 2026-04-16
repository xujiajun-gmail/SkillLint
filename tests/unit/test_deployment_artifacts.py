from __future__ import annotations

from pathlib import Path


def test_deployment_artifacts_exist() -> None:
    assert Path("Dockerfile").exists()
    assert Path(".dockerignore").exists()
    assert Path("compose.yaml").exists()
    assert Path("deploy/systemd/skilllint-web.service").exists()


def test_compose_and_systemd_defaults_reference_18110() -> None:
    compose_text = Path("compose.yaml").read_text(encoding="utf-8")
    service_text = Path("deploy/systemd/skilllint-web.service").read_text(encoding="utf-8")

    assert "18110:18110" in compose_text
    assert 'SKILLLINT_WEB_PORT: "18110"' in compose_text
    assert "SKILLLINT_WEB_PORT=18110" in service_text
