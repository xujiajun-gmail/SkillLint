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
    """工作区相关配置。"""
    root: str = ".skilllint-work"
    keep_artifacts: bool = False


class InputsConfig(BaseModel):
    """输入源相关配置。

    当前主要影响 URL 下载和归档大小约束；后续如果增加对象存储、认证下载等能力，
    也会沿用这一层。
    """
    allow_remote: bool = True
    download_timeout_seconds: int = 60
    max_archive_size_mb: int = 100


class OutputsConfig(BaseModel):
    """报告输出配置。"""
    format: str = "both"
    json_file: str = "result.json"
    markdown_file: str = "report.md"
    sarif_file: str = "result.sarif.json"
    include_snippets: bool = True
    report_language: str = "auto"


class EngineSwitch(BaseModel):
    """单个检测引擎的开关配置。"""
    enabled: bool = True
    use_llm: bool = False


class EnginesConfig(BaseModel):
    regex: EngineSwitch = Field(default_factory=lambda: EngineSwitch(enabled=True))
    package: EngineSwitch = Field(default_factory=lambda: EngineSwitch(enabled=True))
    semantic: EngineSwitch = Field(default_factory=lambda: EngineSwitch(enabled=True, use_llm=False))
    dataflow: EngineSwitch = Field(default_factory=lambda: EngineSwitch(enabled=False))


class RulesConfig(BaseModel):
    """规则筛选配置。

    include/exclude 规则与 taxonomy 会在扫描入口统一转成 RuleSelector，
    后续各引擎共享同一套裁剪逻辑。
    """
    include_rule_ids: list[str] = Field(default_factory=list)
    exclude_rule_ids: list[str] = Field(default_factory=list)
    include_taxonomies: list[str] = Field(default_factory=list)
    exclude_taxonomies: list[str] = Field(default_factory=list)


class LLMConfig(BaseModel):
    """LLM 语义分析配置。"""
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
    """SkillLint 顶层配置对象。"""
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
    # 用排序后结果，保证 CLI 展示和测试快照稳定。
    return sorted(PROFILE_PRESETS)


def _read_yaml(path: Path) -> dict[str, Any]:
    # 不存在时返回空 dict，便于做“默认配置 + 可选 override”组合。
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}



def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    # 配置采用递归合并：
    # - dict 与 dict 深合并
    # - 其他值（包括 list）由 override 整体覆盖
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

    # 合并后强制回写 profile 名称，避免外层只拿到“展开后的配置”而看不到来源 profile。
    merged = _deep_merge(base, preset)
    merged = _deep_merge(merged, override)
    merged["profile"] = selected_profile
    return SkillLintConfig.model_validate(merged)
