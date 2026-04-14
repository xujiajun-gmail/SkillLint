from __future__ import annotations

from pathlib import Path

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

        return findings

    def _finding(self, rule_id: str, evidence: Evidence | None = None) -> Finding | None:
        rule = self.rules[rule_id]
        if not self.selector.allows_rule(rule.rule_id, rule.taxonomy):
            return None
        return build_finding(rule=rule, engine=self.name, evidence=evidence)



def _looks_like_startup_artifact(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    if path.name in STARTUP_ARTIFACT_NAMES or path.suffix.lower() in STARTUP_ARTIFACT_SUFFIXES:
        return True
    return bool(lowered_parts & {"launchagents", "launchdaemons", "systemd", "init.d"})



def _looks_like_ci_workflow(path: Path) -> bool:
    lowered_parts = [part.lower() for part in path.parts]
    return all(part in lowered_parts for part in WORKFLOW_PARTS) and path.suffix.lower() in {".yml", ".yaml"}
