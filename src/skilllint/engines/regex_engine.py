from __future__ import annotations

import re

from skilllint.core.workspace import PreparedWorkspace
from skilllint.engines.base import Engine
from skilllint.models import Evidence, Finding
from skilllint.rules.repository import build_finding, get_rule_repository
from skilllint.rules.selector import RuleSelector
from skilllint.utils.files import extract_snippet, is_text_file, line_range_for_offset, read_text

IGNORED_REGEX_FILENAMES = {"LICENSE", "LICENSE.txt", "COPYING", "NOTICE"}


class RegexEngine(Engine):
    name = "regex"

    def __init__(self, selector: RuleSelector | None = None) -> None:
        self.selector = selector or RuleSelector()
        self.rules = [
            rule
            for rule in get_rule_repository().regex_rules
            if self.selector.allows_rule(rule.rule_id, rule.taxonomy)
        ]

    def run(self, workspace: PreparedWorkspace) -> list[Finding]:
        findings: list[Finding] = []
        seen: set[tuple[str, str, int, int]] = set()
        per_file_rule_counts: dict[tuple[str, str], int] = {}
        for path in workspace.all_files():
            # regex engine 只看文本文件，避免在二进制/许可证里制造大量噪声。
            if not path.is_file() or not is_text_file(path):
                continue
            if path.name in IGNORED_REGEX_FILENAMES:
                continue
            try:
                text = read_text(path)
            except OSError:
                continue
            if not text:
                continue
            rel = workspace.relpath(path)
            for rule in self.rules:
                if not rule.applies_to_path(rel):
                    continue
                count_key = (rule.rule_id, rel)
                # re.finditer 提供所有命中位置，后续再结合 rule 限额、上下文 suppression 做裁剪。
                for match in re.finditer(rule.pattern, text, rule.compiled_flags):
                    if rule.max_matches_per_file is not None and per_file_rule_counts.get(count_key, 0) >= rule.max_matches_per_file:
                        break
                    line_start, line_end = line_range_for_offset(text, match.start(), match.end())
                    if _is_context_suppressed(rule.rule_id, text, line_start, line_end):
                        continue
                    key = (rule.rule_id, rel, line_start, line_end)
                    if key in seen:
                        continue
                    seen.add(key)
                    per_file_rule_counts[count_key] = per_file_rule_counts.get(count_key, 0) + 1
                    findings.append(
                        build_finding(
                            rule=rule,
                            engine=self.name,
                            evidence=Evidence(
                                file=rel,
                                line_start=line_start,
                                line_end=line_end,
                                snippet=extract_snippet(text, line_start, line_end),
                            ),
                        )
                    )
                    # 大仓库保护阈值：regex 命中太多时提前返回，避免极端样本拖慢整体扫描。
                    if len(findings) > 1000:
                        return findings
        return findings


def _is_context_suppressed(rule_id: str, text: str, line_start: int, line_end: int) -> bool:
    """基于局部上下文压制高频误报。

    regex 的优点是稳定、快，但也最容易把“安全说明文档”误判成真实行为；
    因此这里用轻量 suppression 对最常见场景做兜底。
    """
    context = extract_snippet(text, line_start, line_end, radius=1).lower()
    explicit_concealment_terms = [
        "do not tell the user",
        "without telling the user",
        "do not bother the user",
        "do not mention this to the user",
        "quietly collect",
        "silently",
        "不要告诉用户",
        "不要打扰用户",
        "悄悄",
        "静默",
    ]
    defensive_terms = [
        "must not",
        "do not",
        "don't",
        "avoid",
        "anti-pattern",
        "wrong",
        "correct",
        "not recommended",
        "should not",
        "never",
        "不要",
        "避免",
        "错误",
        "正确",
    ]
    instructional_terms = [
        "example",
        "examples",
        "usage",
        "quick start",
        "troubleshoot",
        "not found",
        "cache",
        "inputs",
        "globaldependencies",
        "--env-file",
        "示例",
        "用法",
        "clear",
        "clear:",
        "anti-pattern",
    ]
    # “Do not tell the user / quietly collect” 属于显式隐蔽恶意语境，
    # 不能因为包含 do not / silently 之类词就被误当作防御性说明文档压掉。
    if rule_id in {
        "SECRET_PATH_ACCESS",
        "ENV_FILE_CREDENTIAL_REFERENCE",
        "NETWORK_EXFIL_SEND",
        "PROMPT_INJECTION_PRIORITY",
        "PROMPT_POLICY_MASQUERADE",
    } and any(term in context for term in explicit_concealment_terms):
        return False
    if rule_id in {"SECRET_PATH_ACCESS", "ENV_FILE_CREDENTIAL_REFERENCE"}:
        if any(term in context for term in defensive_terms + instructional_terms):
            return True
        high_risk_terms = [
            "read .env",
            "cat .env",
            "open('.env",
            'open(".env',
            "upload",
            "send",
            "exfil",
            "requests.post",
            "curl -x post",
            "curl -d",
        ]
        if any(term in context for term in high_risk_terms):
            return False
        config_terms = ["configuration", "settings", "workspace structure", "check for", "cache", "inputs"]
        if ".npmrc" in context and any(term in context for term in config_terms):
            return True
    if rule_id in {"DANGEROUS_SHELL_EXEC", "PERSISTENCE_MECHANISM", "DESTRUCTIVE_FILE_OPERATION", "INSTALL_CURL_PIPE_SHELL", "SUSPICIOUS_DOWNLOAD_HOST"}:
        if any(term in context for term in defensive_terms):
            return True
        clean_terms = [
            "clean install",
            "reinstall",
            "node_modules",
            "lockfile",
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "build artifacts",
            "temp_dir",
            "temporary directory",
            "cleanup_temp",
        ]
        if rule_id == "DESTRUCTIVE_FILE_OPERATION" and any(term in context for term in clean_terms):
            return True
        if rule_id == "SUSPICIOUS_DOWNLOAD_HOST" and "raw.githubusercontent.com" in context and not any(term in context for term in ["curl", "wget", "install", "bootstrap", "setup", ".sh"]):
            return True
    if rule_id == "TRIGGER_HIJACK_ANY_TASK" and any(term in context for term in ["request queue", "processing", "methodology", "protocol", "方案", "方法论"]):
        return True
    return False
