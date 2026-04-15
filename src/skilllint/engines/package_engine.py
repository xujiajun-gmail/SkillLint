from __future__ import annotations

import ipaddress
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

from skilllint.core.workspace import PreparedWorkspace
from skilllint.engines.base import Engine
from skilllint.models import Evidence, Finding
from skilllint.rules.repository import build_finding, get_rule_repository
from skilllint.rules.selector import RuleSelector
from skilllint.utils.files import (
    IGNORED_DIRS,
    extract_snippet,
    is_ignored_noise_artifact,
    is_probably_binary,
    line_range_for_offset,
    read_text,
)

SAFE_HIDDEN_NAMES = {".gitignore", ".gitattributes", ".editorconfig", ".prettierrc", ".eslintrc", ".npmrc"}
ARCHIVE_EXTS = {".zip", ".tar", ".gz", ".7z", ".jar"}
BINARY_EXTS = {".exe", ".dll", ".so", ".dylib", ".bin", ".wasm"}
BENIGN_BINARY_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf", ".woff", ".woff2", ".ttf", ".otf"}
STARTUP_ARTIFACT_NAMES = {".bashrc", ".zshrc", ".profile", "rc.local"}
STARTUP_ARTIFACT_SUFFIXES = {".service", ".plist"}
WORKFLOW_PARTS = {".github", "workflows"}
INSTALL_SCRIPT_NAMES = {"install.sh", "bootstrap.sh", "setup.sh"}
PACKAGE_JSON_SCRIPT_KEYS = {"preinstall", "install", "postinstall", "prepare", "prepublish", "prepublishOnly"}
REMOTE_DEPENDENCY_PREFIXES = ("git+", "git://", "github:", "http://", "https://", "ssh://", "git@")
PYTHON_DIRECT_DEPENDENCY_RE = re.compile(r"(?:^|\s)(?:git\+|hg\+|svn\+|bzr\+|https?://)", re.IGNORECASE)
GITHUB_ACTION_USES_RE = re.compile(
    r"^\s*-\s*uses:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_./-]+)?@([^\s#]+))"
)
GITHUB_DANGEROUS_TRIGGER_RE = re.compile(r"^\s*(pull_request_target|issue_comment|workflow_run)\s*:", re.IGNORECASE)
GITHUB_WRITE_PERMISSION_RE = re.compile(
    r"^\s*(contents|actions|packages|pull-requests|issues|discussions|checks|statuses|deployments)\s*:\s*write\s*$",
    re.IGNORECASE,
)
GITHUB_PERMISSIONS_INLINE_RE = re.compile(r"^\s*permissions\s*:\s*write-all\s*$", re.IGNORECASE)
GITHUB_PERMISSIONS_BLOCK_RE = re.compile(r"^(\s*)permissions\s*:\s*$", re.IGNORECASE)
DOCKER_REMOTE_ADD_RE = re.compile(r"^\s*ADD\s+https?://", re.IGNORECASE)
DOCKER_REMOTE_PIPE_RE = re.compile(r"^\s*RUN\s+.*(?:curl|wget).*\|\s*(?:bash|sh)\b", re.IGNORECASE)
ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")
NETWORK_CLAIM_TERMS = [
    "works offline",
    "never connects to the network",
    "does not use the network",
    "offline",
    "never uses the network",
]
SHELL_CLAIM_TERMS = [
    "does not execute commands",
    "does not use a shell",
    "never uses shell",
    "does not execute shell",
    "never executes commands",
]
READ_ONLY_CLAIM_TERMS = [
    "read-only",
    "only reads",
    "does not modify",
    "只读",
    "仅做读取",
    "不会修改",
]
RISKY_PERMISSION_TERMS = {
    "shell access": "shell access",
    "unrestricted network": "unrestricted network",
    "network access": "network access",
    "full filesystem": "full filesystem",
    "write project files": "write project files",
}
METADATA_ENDPOINT_HOSTS = {"169.254.169.254", "metadata.google.internal", "100.100.100.200"}


class PackageEngine(Engine):
    name = "package"

    def __init__(self, selector: RuleSelector | None = None) -> None:
        self.selector = selector or RuleSelector()
        repository = get_rule_repository()
        self.rules = {rule.rule_id: rule for rule in repository.package_rules}

    def run(self, workspace: PreparedWorkspace) -> list[Finding]:
        # package engine 关注“包里带了什么”，而不是“代码究竟怎么执行”。
        # 它是供应链/分发层风险的第一道审计。
        findings: list[Finding] = []
        files = workspace.all_files()
        skill_files = [path for path in files if path.name == "SKILL.md"]
        primary_skill = skill_files[0] if skill_files else None
        primary_skill_rel = workspace.relpath(primary_skill) if primary_skill is not None else "SKILL.md"
        skill_text = _safe_read_text(primary_skill) if primary_skill is not None else ""
        skill_title = _skill_title(skill_text)

        if not skill_files:
            finding = self._finding("PACKAGE_MISSING_SKILL_MD")
            if finding is not None:
                findings.append(finding)
        elif len(skill_files) > 1:
            for skill_file in skill_files[1:]:
                finding = self._finding(
                    "PACKAGE_MULTIPLE_SKILL_MD",
                    evidence=Evidence(file=workspace.relpath(skill_file)),
                )
                if finding is not None:
                    findings.append(finding)

        for path in workspace.normalized_dir.rglob("*"):
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            if is_ignored_noise_artifact(path):
                continue
            rel = workspace.relpath(path)
            if path.is_symlink():
                # symlink 是需要显式暴露的风险信号，因此不沿链接继续扫描目标内容。
                finding = self._finding(
                    "PACKAGE_SYMLINK_PRESENT",
                    evidence=Evidence(file=rel, snippet=str(path.readlink())),
                )
                if finding is not None:
                    findings.append(finding)
                continue
            if path.is_dir():
                continue
            if path.name.startswith(".") and path.name not in SAFE_HIDDEN_NAMES:
                finding = self._finding("PACKAGE_HIDDEN_FILE", evidence=Evidence(file=rel))
                if finding is not None:
                    findings.append(finding)
            if path.suffix.lower() in ARCHIVE_EXTS:
                finding = self._finding("PACKAGE_ARCHIVE_EMBEDDED", evidence=Evidence(file=rel))
                if finding is not None:
                    findings.append(finding)
            elif path.suffix.lower() in BINARY_EXTS or (
                is_probably_binary(path) and path.suffix.lower() not in BENIGN_BINARY_EXTS
            ):
                finding = self._finding("PACKAGE_BINARY_PRESENT", evidence=Evidence(file=rel))
                if finding is not None:
                    findings.append(finding)
            elif path.name in INSTALL_SCRIPT_NAMES:
                finding = self._finding("PACKAGE_INSTALL_SCRIPT_PRESENT", evidence=Evidence(file=rel))
                if finding is not None:
                    findings.append(finding)

            if _looks_like_startup_artifact(path):
                finding = self._finding("PACKAGE_SYSTEM_STARTUP_ARTIFACT", evidence=Evidence(file=rel))
                if finding is not None:
                    findings.append(finding)
            elif _looks_like_ci_workflow(path):
                finding = self._finding("PACKAGE_CI_WORKFLOW_PRESENT", evidence=Evidence(file=rel))
                if finding is not None:
                    findings.append(finding)
                findings.extend(self._scan_ci_workflow(path, rel))
            elif path.name == "package.json":
                findings.extend(self._scan_package_json(path, rel))
            elif path.name == "skill.json" or _looks_like_codex_plugin_manifest(path):
                findings.extend(
                    self._scan_skill_manifest(
                        path=path,
                        rel=rel,
                        skill_text=skill_text,
                        skill_title=skill_title,
                        skill_rel=primary_skill_rel,
                    )
                )
            elif path.name == "pyproject.toml":
                findings.extend(self._scan_pyproject(path, rel))
            elif _looks_like_python_dependency_manifest(path):
                findings.extend(self._scan_python_dependency_manifest(path, rel))
            elif _looks_like_dockerfile(path):
                findings.extend(self._scan_dockerfile(path, rel))
            if path.name in {"SKILL.md", "skill.json", "plugin.json"}:
                findings.extend(self._scan_hidden_unicode(path, rel))

        return findings

    def _finding(self, rule_id: str, evidence: Evidence | None = None) -> Finding | None:
        # package engine 内部大量复用“按 rule_id 取 catalog 元数据并构造 finding”的逻辑，
        # 抽成统一入口可避免每处重复 selector 判断。
        rule = self.rules[rule_id]
        if not self.selector.allows_rule(rule.rule_id, rule.taxonomy):
            return None
        return build_finding(rule=rule, engine=self.name, evidence=evidence)

    def _scan_package_json(self, path: Path, rel: str) -> list[Finding]:
        # 这里同时看两类风险：
        # 1) lifecycle script（安装时自动执行）
        # 2) remote/VCS dependency（供应链来源不透明）
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []

        findings: list[Finding] = []
        scripts = data.get("scripts")
        if isinstance(scripts, dict):
            for name, command in scripts.items():
                if name not in PACKAGE_JSON_SCRIPT_KEYS or not isinstance(command, str):
                    continue
                finding = self._finding(
                    "PACKAGE_MANIFEST_LIFECYCLE_SCRIPT",
                    evidence=Evidence(
                        file=rel,
                        snippet=f"{name}: {command}",
                    ),
                )
                if finding is not None:
                    finding.metadata["manifest_script"] = name
                    findings.append(finding)

        for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
            deps = data.get(section)
            if not isinstance(deps, dict):
                continue
            for name, version in deps.items():
                if not isinstance(version, str):
                    continue
                if not _is_remote_dependency_spec(version):
                    continue
                finding = self._finding(
                    "PACKAGE_REMOTE_DEPENDENCY",
                    evidence=Evidence(
                        file=rel,
                        snippet=f"{section}.{name}: {version}",
                    ),
                )
                if finding is not None:
                    finding.metadata["dependency_name"] = name
                    finding.metadata["dependency_section"] = section
                    findings.append(finding)
        return findings

    def _scan_python_dependency_manifest(self, path: Path, rel: str) -> list[Finding]:
        # requirements*.txt 不需要做复杂解析；识别最危险的直连远程依赖即可。
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []

        findings: list[Finding] = []
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not PYTHON_DIRECT_DEPENDENCY_RE.search(stripped):
                continue
            finding = self._finding(
                "PACKAGE_REMOTE_DEPENDENCY",
                evidence=Evidence(
                    file=rel,
                    line_start=idx,
                    line_end=idx,
                    snippet=stripped,
                ),
            )
            if finding is not None:
                finding.metadata["dependency_section"] = path.name
                findings.append(finding)
        return findings

    def _scan_pyproject(self, path: Path, rel: str) -> list[Finding]:
        # pyproject 的依赖声明形态很多，因此拆到辅助函数里按不同生态逐层遍历。
        if tomllib is None:
            return []
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []

        findings: list[Finding] = []

        for section_name, requirement in _iter_pyproject_remote_dependencies(data):
            finding = self._finding(
                "PACKAGE_REMOTE_DEPENDENCY",
                evidence=Evidence(
                    file=rel,
                    snippet=f"{section_name}: {requirement}",
                ),
            )
            if finding is not None:
                finding.metadata["dependency_section"] = section_name
                findings.append(finding)

        return findings

    def _scan_ci_workflow(self, path: Path, rel: str) -> list[Finding]:
        # GitHub Actions 用简单文本解析而不是完整 YAML AST：
        # 优点是实现轻、容错高、足够覆盖当前重点信号；
        # 缺点是对更复杂语义场景的理解有限。
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        findings: list[Finding] = []
        permissions_indent: int | None = None
        for idx, line in enumerate(lines, start=1):
            if permissions_indent is not None:
                current_indent = _leading_spaces(line)
                stripped = line.strip()
                if stripped and current_indent <= permissions_indent:
                    permissions_indent = None
                elif stripped and GITHUB_WRITE_PERMISSION_RE.match(line):
                    finding = self._finding(
                        "PACKAGE_CI_ELEVATED_PERMISSIONS",
                        evidence=Evidence(
                            file=rel,
                            line_start=idx,
                            line_end=idx,
                            snippet=line.strip(),
                        ),
                    )
                    if finding is not None:
                        findings.append(finding)

            action_match = GITHUB_ACTION_USES_RE.match(line)
            if action_match and not _github_action_ref_is_pinned(action_match.group(2)):
                finding = self._finding(
                    "PACKAGE_CI_UNPINNED_ACTION",
                    evidence=Evidence(
                        file=rel,
                        line_start=idx,
                        line_end=idx,
                        snippet=line.strip(),
                    ),
                )
                if finding is not None:
                    finding.metadata["action_ref"] = action_match.group(1)
                    findings.append(finding)
            if GITHUB_DANGEROUS_TRIGGER_RE.match(line):
                finding = self._finding(
                    "PACKAGE_CI_DANGEROUS_TRIGGER",
                    evidence=Evidence(
                        file=rel,
                        line_start=idx,
                        line_end=idx,
                        snippet=line.strip(),
                    ),
                )
                if finding is not None:
                    findings.append(finding)
            if GITHUB_PERMISSIONS_INLINE_RE.match(line):
                finding = self._finding(
                    "PACKAGE_CI_ELEVATED_PERMISSIONS",
                    evidence=Evidence(
                        file=rel,
                        line_start=idx,
                        line_end=idx,
                        snippet=line.strip(),
                    ),
                )
                if finding is not None:
                    findings.append(finding)
            block_match = GITHUB_PERMISSIONS_BLOCK_RE.match(line)
            if block_match:
                permissions_indent = len(block_match.group(1))
        return findings

    def _scan_dockerfile(self, path: Path, rel: str) -> list[Finding]:
        # 当前只抓最危险、最稳定的 bootstrap 形态，避免把普通 Dockerfile 过度误报。
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        findings: list[Finding] = []
        for idx, line in enumerate(lines, start=1):
            if not (DOCKER_REMOTE_ADD_RE.search(line) or DOCKER_REMOTE_PIPE_RE.search(line)):
                continue
            finding = self._finding(
                "PACKAGE_DOCKER_REMOTE_BOOTSTRAP",
                evidence=Evidence(
                    file=rel,
                    line_start=idx,
                    line_end=idx,
                    snippet=line.strip(),
                ),
            )
            if finding is not None:
                findings.append(finding)
        return findings

    def _scan_skill_manifest(
        self,
        *,
        path: Path,
        rel: str,
        skill_text: str,
        skill_title: str | None,
        skill_rel: str,
    ) -> list[Finding]:
        raw = _safe_read_text(path)
        try:
            data = json.loads(raw)
        except Exception:
            return []
        if not isinstance(data, dict):
            return []

        findings: list[Finding] = []
        permissions = [item for item in data.get("permissions", []) if isinstance(item, str)]
        lowered_permissions = [item.lower() for item in permissions]
        for permission in permissions:
            if permission.lower() not in RISKY_PERMISSION_TERMS:
                continue
            finding = self._finding(
                "PACKAGE_MANIFEST_RISKY_PERMISSION",
                evidence=_manifest_value_evidence(rel=rel, raw=raw, value=permission),
            )
            if finding is not None:
                finding.metadata["permission"] = permission
                findings.append(finding)

        startup_hook = _manifest_startup_hook(data)
        if startup_hook is not None:
            finding = self._finding(
                "PACKAGE_MANIFEST_STARTUP_HOOK",
                evidence=_manifest_value_evidence(rel=rel, raw=raw, value=startup_hook),
            )
            if finding is not None:
                finding.metadata["hook"] = startup_hook
                findings.append(finding)

        for endpoint in _manifest_endpoints(data):
            endpoint_type = _classify_endpoint(endpoint)
            if endpoint_type is None:
                continue
            rule_id = (
                "PACKAGE_MANIFEST_METADATA_ENDPOINT"
                if endpoint_type == "metadata"
                else "PACKAGE_MANIFEST_LOCAL_ENDPOINT"
            )
            finding = self._finding(
                rule_id,
                evidence=_manifest_value_evidence(rel=rel, raw=raw, value=endpoint),
            )
            if finding is not None:
                finding.metadata["endpoint"] = endpoint
                findings.append(finding)

        repository = data.get("repository")
        if isinstance(repository, str) and _looks_like_floating_reference(repository):
            finding = self._finding(
                "PACKAGE_MANIFEST_FLOATING_REFERENCE",
                evidence=_manifest_value_evidence(rel=rel, raw=raw, value=repository),
            )
            if finding is not None:
                finding.metadata["repository"] = repository
                findings.append(finding)

        manifest_name = data.get("name")
        if isinstance(manifest_name, str) and skill_title and _titles_conflict(manifest_name, skill_title):
            finding = self._finding(
                "PACKAGE_MANIFEST_IDENTITY_MISMATCH",
                evidence=_manifest_value_evidence(rel=rel, raw=raw, value=manifest_name),
            )
            if finding is not None:
                finding.metadata["manifest_name"] = manifest_name
                finding.metadata["skill_title"] = skill_title
                findings.append(finding)

        lowered_skill = skill_text.lower()
        has_network_capability = bool(_manifest_endpoints(data)) or any("network" in item for item in lowered_permissions)
        has_shell_capability = startup_hook is not None or any("shell" in item for item in lowered_permissions)
        has_write_capability = any(
            term in item for item in lowered_permissions for term in ["full filesystem", "write"]
        )

        if skill_text and has_network_capability and any(term in lowered_skill for term in NETWORK_CLAIM_TERMS):
            findings.extend(
                self._build_alignment_findings(
                    "PACKAGE_MANIFEST_UNDERDECLARED_NETWORK",
                    skill_rel,
                    skill_text,
                    NETWORK_CLAIM_TERMS,
                )
            )
        if skill_text and has_shell_capability and any(term in lowered_skill for term in SHELL_CLAIM_TERMS):
            findings.extend(
                self._build_alignment_findings(
                    "PACKAGE_MANIFEST_UNDERDECLARED_SHELL",
                    skill_rel,
                    skill_text,
                    SHELL_CLAIM_TERMS,
                )
            )
        if skill_text and has_write_capability and any(term in lowered_skill for term in READ_ONLY_CLAIM_TERMS):
            findings.extend(
                self._build_alignment_findings(
                    "PACKAGE_MANIFEST_UNDERDECLARED_WRITE",
                    skill_rel,
                    skill_text,
                    READ_ONLY_CLAIM_TERMS,
                )
            )

        return findings

    def _scan_hidden_unicode(self, path: Path, rel: str) -> list[Finding]:
        text = _safe_read_text(path)
        if not text:
            return []
        match = ZERO_WIDTH_RE.search(text)
        if match is None:
            return []
        line_start, line_end = line_range_for_offset(text, match.start(), match.end())
        finding = self._finding(
            "PACKAGE_HIDDEN_UNICODE_MARKER",
            evidence=Evidence(
                file=rel,
                line_start=line_start,
                line_end=line_end,
                snippet=extract_snippet(text, line_start, line_end, radius=1),
            ),
        )
        return [finding] if finding is not None else []

    def _build_alignment_findings(self, rule_id: str, rel: str, text: str, terms: list[str]) -> list[Finding]:
        for term in terms:
            offset = text.lower().find(term)
            if offset == -1:
                continue
            line_start, line_end = line_range_for_offset(text, offset, offset + len(term))
            finding = self._finding(
                rule_id,
                evidence=Evidence(
                    file=rel,
                    line_start=line_start,
                    line_end=line_end,
                    snippet=extract_snippet(text, line_start, line_end, radius=1),
                ),
            )
            return [finding] if finding is not None else []
        return []



def _looks_like_startup_artifact(path: Path) -> bool:
    # 启动项判断兼顾“文件名命中”和“目录语义命中”。
    lowered_parts = {part.lower() for part in path.parts}
    if path.name in STARTUP_ARTIFACT_NAMES or path.suffix.lower() in STARTUP_ARTIFACT_SUFFIXES:
        return True
    return bool(lowered_parts & {"launchagents", "launchdaemons", "systemd", "init.d"})



def _looks_like_ci_workflow(path: Path) -> bool:
    lowered_parts = [part.lower() for part in path.parts]
    return all(part in lowered_parts for part in WORKFLOW_PARTS) and path.suffix.lower() in {".yml", ".yaml"}



def _is_remote_dependency_spec(version: str) -> bool:
    lowered = version.strip().lower()
    return lowered.startswith(REMOTE_DEPENDENCY_PREFIXES)



def _looks_like_python_dependency_manifest(path: Path) -> bool:
    name = path.name.lower()
    return name.startswith("requirements") and path.suffix.lower() == ".txt"



def _looks_like_dockerfile(path: Path) -> bool:
    return path.name.lower() == "dockerfile"


def _looks_like_codex_plugin_manifest(path: Path) -> bool:
    lowered = [part.lower() for part in path.parts]
    return path.name == "plugin.json" and ".codex-plugin" in lowered



def _github_action_ref_is_pinned(ref: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{40}", ref))



def _leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))



def _iter_pyproject_remote_dependencies(data: dict[str, Any]) -> list[tuple[str, str]]:
    """从 pyproject.toml 中提取远程依赖声明。

    这里覆盖：
    - PEP 621 project.dependencies
    - poetry dependencies/group
    - uv sources
    - build-system.requires
    """
    items: list[tuple[str, str]] = []

    project = data.get("project")
    if isinstance(project, dict):
        for requirement in project.get("dependencies", []) or []:
            if isinstance(requirement, str) and _is_remote_requirement_string(requirement):
                items.append(("project.dependencies", requirement))
        optional = project.get("optional-dependencies", {})
        if isinstance(optional, dict):
            for group, requirements in optional.items():
                if not isinstance(requirements, list):
                    continue
                for requirement in requirements:
                    if isinstance(requirement, str) and _is_remote_requirement_string(requirement):
                        items.append((f"project.optional-dependencies.{group}", requirement))

    tool = data.get("tool")
    if isinstance(tool, dict):
        poetry = tool.get("poetry")
        if isinstance(poetry, dict):
            for dep_group_name in ("dependencies", "dev-dependencies"):
                deps = poetry.get(dep_group_name)
                if isinstance(deps, dict):
                    for dep_name, dep_spec in deps.items():
                        if _is_remote_pyproject_dependency_spec(dep_spec):
                            items.append((f"tool.poetry.{dep_group_name}.{dep_name}", _render_dependency_spec(dep_spec)))
                group = poetry.get("group")
                if isinstance(group, dict):
                    for group_name, group_data in group.items():
                        if not isinstance(group_data, dict):
                            continue
                        deps = group_data.get("dependencies")
                        if not isinstance(deps, dict):
                            continue
                        for dep_name, dep_spec in deps.items():
                            if _is_remote_pyproject_dependency_spec(dep_spec):
                                items.append(
                                    (
                                        f"tool.poetry.group.{group_name}.dependencies.{dep_name}",
                                        _render_dependency_spec(dep_spec),
                                    )
                                )
        uv = tool.get("uv")
        if isinstance(uv, dict):
            sources = uv.get("sources")
            if isinstance(sources, dict):
                for dep_name, dep_spec in sources.items():
                    if _is_remote_pyproject_dependency_spec(dep_spec):
                        items.append((f"tool.uv.sources.{dep_name}", _render_dependency_spec(dep_spec)))

    build_system = data.get("build-system")
    if isinstance(build_system, dict):
        for requirement in build_system.get("requires", []) or []:
            if isinstance(requirement, str) and _is_remote_requirement_string(requirement):
                items.append(("build-system.requires", requirement))

    return items



def _is_remote_requirement_string(value: str) -> bool:
    lowered = value.strip().lower()
    return " @ http://" in lowered or " @ https://" in lowered or "git+" in lowered



def _is_remote_pyproject_dependency_spec(value: Any) -> bool:
    if isinstance(value, str):
        return _is_remote_requirement_string(value) or _is_remote_dependency_spec(value)
    if isinstance(value, dict):
        return any(key in value for key in ("git", "url"))
    return False



def _render_dependency_spec(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _manifest_startup_hook(data: dict[str, Any]) -> str | None:
    hooks = data.get("hooks")
    if isinstance(hooks, dict):
        for key in ("startup", "bootstrap", "install"):
            value = hooks.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _manifest_endpoints(data: dict[str, Any]) -> list[str]:
    endpoints = data.get("endpoints")
    if not isinstance(endpoints, list):
        return []
    return [item for item in endpoints if isinstance(item, str)]


def _classify_endpoint(endpoint: str) -> str | None:
    parsed = urlparse(endpoint)
    host = parsed.hostname
    if not host:
        return None
    if host in METADATA_ENDPOINT_HOSTS:
        return "metadata"
    if host in {"localhost", "::1"}:
        return "local"
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return "local" if host.endswith(".local") else None
    if str(ip) in METADATA_ENDPOINT_HOSTS:
        return "metadata"
    if ip.is_loopback or ip.is_private or ip.is_link_local:
        return "local"
    return None


def _looks_like_floating_reference(value: str) -> bool:
    lowered = value.strip().lower().rstrip("/")
    return lowered.endswith("/latest") or lowered.endswith(":latest")


def _skill_title(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return None


def _name_tokens(value: str) -> set[str]:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return {
        token
        for token in normalized.split()
        if len(token) >= 3 and token not in {"skill", "helper", "agent", "tool"}
    }


def _titles_conflict(left: str, right: str) -> bool:
    left_tokens = _name_tokens(left)
    right_tokens = _name_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    return left_tokens.isdisjoint(right_tokens)


def _safe_read_text(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return read_text(path)
    except OSError:
        return ""


def _manifest_value_evidence(*, rel: str, raw: str, value: str) -> Evidence:
    """为 manifest 中的字符串值构造带源码定位的证据。

    这里不依赖完整 JSON AST 位置信息，而是采用“原文查找 + 行号反推”的轻量方案，
    足以满足 skill.json / plugin.json 这类小文件的定位需求。
    """
    offset = raw.find(value)
    if offset == -1:
        return Evidence(file=rel, snippet=value)
    line_start, line_end = line_range_for_offset(raw, offset, offset + len(value))
    return Evidence(
        file=rel,
        line_start=line_start,
        line_end=line_end,
        snippet=extract_snippet(raw, line_start, line_end, radius=1),
    )
