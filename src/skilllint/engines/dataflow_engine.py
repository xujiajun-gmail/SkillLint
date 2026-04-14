from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from skilllint.core.workspace import PreparedWorkspace
from skilllint.engines.base import Engine
from skilllint.models import Evidence, Finding
from skilllint.rules.repository import RuleMeta, build_finding, get_rule_repository
from skilllint.rules.selector import RuleSelector
from skilllint.utils.files import extract_snippet, read_text

PY_SOURCE_CALLS = {
    "os.getenv",
    "os.environ.get",
    "dotenv.get_key",
}
PY_NETWORK_CALLS = {
    "requests.post",
    "requests.put",
    "httpx.post",
    "httpx.put",
    "urllib.request.urlopen",
    "urllib.request.Request",
}
PY_EXEC_CALLS = {
    "os.system",
    "subprocess.run",
    "subprocess.Popen",
    "eval",
    "exec",
}
SECRET_PATH_PATTERNS = [r"~?/\.ssh", r"\.env\b", r"authorized_keys", r"id_rsa", r"\.npmrc\b"]
SHELL_SOURCE_PATTERNS = [r"\$[A-Z_][A-Z0-9_]*", r"\.env\b", r"~?/\.ssh", r"authorized_keys", r"id_rsa"]
SHELL_NETWORK_PATTERNS = [r"curl\b", r"wget\b", r"nc\b", r"scp\b", r"rsync\b", r"python\s+-c.*requests\.post"]
SHELL_EXEC_PATTERNS = [r"bash\s+-c", r"sh\s+-c", r"eval\b", r"source\b", r"\.\s+"]


@dataclass
class Taint:
    kind: str
    lineno: int
    detail: str


class PythonTaintAnalyzer(ast.NodeVisitor):
    def __init__(self, text: str, rules: dict[str, RuleMeta]) -> None:
        self.text = text
        self.rules = rules
        self.taints: dict[str, Taint] = {}
        self.findings: list[Finding] = []
        self.current_function_args: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        prev = self.current_function_args.copy()
        self.current_function_args = {arg.arg for arg in node.args.args}
        self.generic_visit(node)
        self.current_function_args = prev

    def visit_Assign(self, node: ast.Assign) -> None:
        taint = self._taint_from_expr(node.value)
        if taint is not None:
            for target in node.targets:
                for name in _extract_names(target):
                    self.taints[name] = taint
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            taint = self._taint_from_expr(node.value)
            if taint is not None:
                for name in _extract_names(node.target):
                    self.taints[name] = taint
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = _call_name(node)
        if call_name in PY_NETWORK_CALLS and "DATAFLOW_SECRET_TO_NETWORK" in self.rules:
            tainted = self._find_tainted_args(node)
            if tainted:
                self.findings.append(
                    _finding_from_call(
                        rule=self.rules["DATAFLOW_SECRET_TO_NETWORK"],
                        lineno=node.lineno,
                        text=self.text,
                        detail=tainted.detail,
                    )
                )
        if call_name in PY_EXEC_CALLS and "DATAFLOW_TAINTED_TO_EXEC" in self.rules:
            tainted = self._find_tainted_args(node, include_function_args=True)
            if tainted:
                title = self.rules["DATAFLOW_TAINTED_TO_EXEC"].title
                if tainted.kind == "function-arg":
                    title = "Untrusted or tainted data flows to execution sink"
                self.findings.append(
                    _finding_from_call(
                        rule=self.rules["DATAFLOW_TAINTED_TO_EXEC"],
                        lineno=node.lineno,
                        text=self.text,
                        detail=tainted.detail,
                        override_title=title,
                    )
                )
        self.generic_visit(node)

    def _find_tainted_args(self, node: ast.Call, include_function_args: bool = False) -> Taint | None:
        for arg in list(node.args) + [kw.value for kw in node.keywords]:
            taint = self._taint_from_expr(arg, include_function_args=include_function_args)
            if taint is not None:
                return taint
        return None

    def _taint_from_expr(self, node: ast.AST, include_function_args: bool = False) -> Taint | None:
        if isinstance(node, ast.Name):
            if node.id in self.taints:
                return self.taints[node.id]
            if include_function_args and node.id in self.current_function_args:
                return Taint(kind="function-arg", lineno=node.lineno, detail=f"function argument: {node.id}")
            return None
        if isinstance(node, ast.Subscript) and _looks_like_os_environ(node):
            return Taint(kind="env", lineno=node.lineno, detail="os.environ access")
        if isinstance(node, ast.Call):
            call_name = _call_name(node)
            if call_name in PY_SOURCE_CALLS:
                return Taint(kind="env", lineno=node.lineno, detail=call_name)
            if call_name == "open" and node.args:
                secret_path = _string_constant(node.args[0])
                if secret_path and _is_secret_path(secret_path):
                    return Taint(kind="secret-file", lineno=node.lineno, detail=secret_path)
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                inner = self._taint_from_expr(arg, include_function_args=include_function_args)
                if inner is not None:
                    return inner
        if isinstance(node, (ast.JoinedStr, ast.BinOp, ast.Dict, ast.List, ast.Tuple, ast.Set)):
            for child in ast.iter_child_nodes(node):
                inner = self._taint_from_expr(child, include_function_args=include_function_args)
                if inner is not None:
                    return inner
        return None


class DataflowEngine(Engine):
    name = "dataflow"

    def __init__(self, selector: RuleSelector | None = None) -> None:
        self.selector = selector or RuleSelector()
        repository = get_rule_repository()
        self.rules = {
            rule.rule_id: rule
            for rule in repository.dataflow_rules
            if self.selector.allows_rule(rule.rule_id, rule.taxonomy)
        }

    def run(self, workspace: PreparedWorkspace) -> list[Finding]:
        findings: list[Finding] = []
        for path in workspace.all_files():
            if not path.is_file():
                continue
            if path.suffix == ".py":
                findings.extend(self._scan_python(path, workspace))
            elif path.suffix in {".sh", ".bash", ".zsh"}:
                findings.extend(self._scan_shell(path, workspace))
        return findings

    def _scan_python(self, path: Path, workspace: PreparedWorkspace) -> list[Finding]:
        try:
            text = read_text(path)
            tree = ast.parse(text)
        except Exception:
            return []
        analyzer = PythonTaintAnalyzer(text, self.rules)
        analyzer.visit(tree)
        for finding in analyzer.findings:
            finding.evidence.file = workspace.relpath(path)
        return analyzer.findings

    def _scan_shell(self, path: Path, workspace: PreparedWorkspace) -> list[Finding]:
        try:
            text = read_text(path)
        except OSError:
            return []
        findings: list[Finding] = []
        has_source = any(re.search(pattern, text) for pattern in SHELL_SOURCE_PATTERNS)
        has_network = any(re.search(pattern, text) for pattern in SHELL_NETWORK_PATTERNS)
        has_exec = any(re.search(pattern, text) for pattern in SHELL_EXEC_PATTERNS)
        rel = workspace.relpath(path)

        if has_source and has_network and "DATAFLOW_SHELL_SECRET_TO_NETWORK" in self.rules:
            line_start, line_end = _first_interesting_lines(text, SHELL_SOURCE_PATTERNS + SHELL_NETWORK_PATTERNS)
            findings.append(
                build_finding(
                    rule=self.rules["DATAFLOW_SHELL_SECRET_TO_NETWORK"],
                    engine=self.name,
                    evidence=Evidence(
                        file=rel,
                        line_start=line_start,
                        line_end=line_end,
                        snippet=extract_snippet(text, line_start, line_end, radius=1),
                    ),
                )
            )
        if has_exec and re.search(r"\$(?:@|\{|[A-Za-z_])", text) and "DATAFLOW_SHELL_INPUT_TO_EXEC" in self.rules:
            line_start, line_end = _first_interesting_lines(text, SHELL_EXEC_PATTERNS)
            findings.append(
                build_finding(
                    rule=self.rules["DATAFLOW_SHELL_INPUT_TO_EXEC"],
                    engine=self.name,
                    evidence=Evidence(
                        file=rel,
                        line_start=line_start,
                        line_end=line_end,
                        snippet=extract_snippet(text, line_start, line_end, radius=1),
                    ),
                )
            )
        return findings



def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts = []
        current: ast.AST | None = func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return None



def _extract_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        names: list[str] = []
        for elt in node.elts:
            names.extend(_extract_names(elt))
        return names
    return []



def _looks_like_os_environ(node: ast.Subscript) -> bool:
    value = node.value
    return (
        isinstance(value, ast.Attribute)
        and isinstance(value.value, ast.Name)
        and value.value.id == "os"
        and value.attr == "environ"
    )



def _string_constant(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None



def _is_secret_path(path: str) -> bool:
    lowered = path.lower()
    return any(re.search(pattern, lowered) for pattern in SECRET_PATH_PATTERNS)



def _finding_from_call(
    *,
    rule: RuleMeta,
    lineno: int,
    text: str,
    detail: str,
    override_title: str | None = None,
) -> Finding:
    snippet = extract_snippet(text, lineno, lineno, radius=1)
    finding = build_finding(
        rule=rule,
        engine="dataflow",
        evidence=Evidence(line_start=lineno, line_end=lineno, snippet=snippet),
        metadata={"taint_detail": detail},
    )
    if override_title:
        finding.title = override_title
    return finding



def _first_interesting_lines(text: str, patterns: list[str]) -> tuple[int, int]:
    for idx, line in enumerate(text.splitlines(), start=1):
        if any(re.search(pattern, line) for pattern in patterns):
            return idx, idx
    return 1, 1
