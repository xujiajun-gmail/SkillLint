from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

PROFILE_PRESETS: dict[str, dict[str, Any]] = {
    # balanced：默认体验优先，避免在日常扫描里默认启用较重的 dataflow。
    "balanced": {
        "engines": {
            "regex": {"enabled": True},
            "package": {"enabled": True},
            "semantic": {"enabled": True, "use_llm": False},
            "dataflow": {"enabled": False},
        }
    },
    "strict": {
        "engines": {
            "regex": {"enabled": True},
            "package": {"enabled": True},
            "semantic": {"enabled": True, "use_llm": False},
            "dataflow": {"enabled": True},
        }
    },
    "marketplace-review": {
        # marketplace-review 更强调“分发/声明/供应链”相关风险。
        "engines": {
            "regex": {"enabled": True},
            "package": {"enabled": True},
            "semantic": {"enabled": True, "use_llm": False},
            "dataflow": {"enabled": True},
        },
        "rules": {
            "include_taxonomies": [
                "SLT-A05",
                "SLT-C01",
                "SLT-C02",
                "SLT-C03",
                "SLT-C04",
                "SLT-E03",
            ]
        },
    },
    "ci": {
        # ci profile 聚焦自动化工作流劫持、远程指令与执行链风险。
        "engines": {
            "regex": {"enabled": True},
            "package": {"enabled": True},
            "semantic": {"enabled": True, "use_llm": False},
            "dataflow": {"enabled": True},
        },
        "rules": {
            "include_taxonomies": [
                "SLT-A03",
                "SLT-B03",
                "SLT-B05",
                "SLT-C01",
                "SLT-C02",
                "SLT-D01",
                "SLT-E02",
            ]
        },
    },
}


class WorkspaceConfig(BaseModel):
    root: str = ".skilllint-work"
    keep_artifacts: bool = False


class InputsConfig(BaseModel):
    allow_remote: bool = True
    download_timeout_seconds: int = 60
    max_archive_size_mb: int = 100


class OutputsConfig(BaseModel):
    format: str = "both"
    json_file: str = "result.json"
    markdown_file: str = "report.md"
    sarif_file: str = "result.sarif.json"
    include_snippets: bool = True
    report_language: str = "auto"


class EngineSwitch(BaseModel):
    enabled: bool = True
    use_llm: bool = False


class EnginesConfig(BaseModel):
    regex: EngineSwitch = Field(default_factory=lambda: EngineSwitch(enabled=True))
    package: EngineSwitch = Field(default_factory=lambda: EngineSwitch(enabled=True))
    semantic: EngineSwitch = Field(default_factory=lambda: EngineSwitch(enabled=True, use_llm=False))
    dataflow: EngineSwitch = Field(default_factory=lambda: EngineSwitch(enabled=False))


class RulesConfig(BaseModel):
    include_rule_ids: list[str] = Field(default_factory=list)
    exclude_rule_ids: list[str] = Field(default_factory=list)
    include_taxonomies: list[str] = Field(default_factory=list)
    exclude_taxonomies: list[str] = Field(default_factory=list)


class LLMConfig(BaseModel):
    provider: str = "openai"
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    max_context_chars: int = 12000
    temperature: float = 0.0
    debug: bool = False


class SeverityConfig(BaseModel):
    fail_on: str | None = None


class SkillLintConfig(BaseModel):
    version: int = 1
    profile: str = "balanced"
    language: str = "auto"
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    inputs: InputsConfig = Field(default_factory=InputsConfig)
    outputs: OutputsConfig = Field(default_factory=OutputsConfig)
    engines: EnginesConfig = Field(default_factory=EnginesConfig)
    rules: RulesConfig = Field(default_factory=RulesConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    severity: SeverityConfig = Field(default_factory=SeverityConfig)


class UnknownProfileError(ValueError):
    pass


def available_profiles() -> list[str]:
    return sorted(PROFILE_PRESETS)


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}



def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        existing = result.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            result[key] = _deep_merge(existing, value)
        else:
            result[key] = value
    return result



def load_config(path: str | Path | None = None, profile: str | None = None) -> SkillLintConfig:
    """加载默认配置、应用 profile，再叠加用户配置文件。

    合并顺序：
    1. config/skilllint.default.yaml
    2. profile preset
    3. 用户传入的 config 文件
    4. CLI 在外层再做最终覆盖
    """
    base_path = Path("config/skilllint.default.yaml")
    base = _read_yaml(base_path)
    override = _read_yaml(Path(path)) if path is not None else {}

    selected_profile = profile or override.get("profile") or base.get("profile") or "balanced"
    preset = PROFILE_PRESETS.get(selected_profile)
    if preset is None:
        raise UnknownProfileError(f"Unknown SkillLint profile: {selected_profile}")

    merged = _deep_merge(base, preset)
    merged = _deep_merge(merged, override)
    merged["profile"] = selected_profile
    return SkillLintConfig.model_validate(merged)
