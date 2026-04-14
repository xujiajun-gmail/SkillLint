from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

from skilllint.core.workspace import PreparedWorkspace
from skilllint.engines.base import Engine
from skilllint.models import Evidence, Finding
from skilllint.rules.repository import build_finding, get_rule_repository
from skilllint.rules.selector import RuleSelector
from skilllint.utils.files import IGNORED_DIRS, is_probably_binary

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
GITHUB_DANGEROUS_TRIGGER_RE = re.compile(r"^\s*pull_request_target\s*:", re.IGNORECASE)
DOCKER_REMOTE_ADD_RE = re.compile(r"^\s*ADD\s+https?://", re.IGNORECASE)
DOCKER_REMOTE_PIPE_RE = re.compile(r"^\s*RUN\s+.*(?:curl|wget).*\|\s*(?:bash|sh)\b", re.IGNORECASE)


class PackageEngine(Engine):
    name = "package"

    def __init__(self, selector: RuleSelector | None = None) -> None:
        self.selector = selector or RuleSelector()
        repository = get_rule_repository()
        self.rules = {rule.rule_id: rule for rule in repository.package_rules}

    def run(self, workspace: PreparedWorkspace) -> list[Finding]:
        findings: list[Finding] = []
        files = workspace.all_files()
        skill_files = [path for path in files if path.name == "SKILL.md"]

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
            rel = workspace.relpath(path)
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            if path.is_symlink():
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
            elif path.name == "pyproject.toml":
                findings.extend(self._scan_pyproject(path, rel))
            elif _looks_like_python_dependency_manifest(path):
                findings.extend(self._scan_python_dependency_manifest(path, rel))
            elif _looks_like_dockerfile(path):
                findings.extend(self._scan_dockerfile(path, rel))

        return findings

    def _finding(self, rule_id: str, evidence: Evidence | None = None) -> Finding | None:
        rule = self.rules[rule_id]
        if not self.selector.allows_rule(rule.rule_id, rule.taxonomy):
            return None
        return build_finding(rule=rule, engine=self.name, evidence=evidence)

    def _scan_package_json(self, path: Path, rel: str) -> list[Finding]:
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
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        findings: list[Finding] = []
        for idx, line in enumerate(lines, start=1):
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
        return findings

    def _scan_dockerfile(self, path: Path, rel: str) -> list[Finding]:
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



def _looks_like_startup_artifact(path: Path) -> bool:
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



def _github_action_ref_is_pinned(ref: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{40}", ref))



def _iter_pyproject_remote_dependencies(data: dict[str, Any]) -> list[tuple[str, str]]:
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
