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
    "requests.request",
    "requests.Session.post",
    "requests.Session.put",
    "requests.Session.request",
    "httpx.post",
    "httpx.put",
    "httpx.request",
    "httpx.Client.post",
    "httpx.Client.put",
    "httpx.Client.request",
    "httpx.AsyncClient.post",
    "httpx.AsyncClient.put",
    "httpx.AsyncClient.request",
    "aiohttp.ClientSession.post",
    "aiohttp.ClientSession.put",
    "aiohttp.ClientSession.request",
    "urllib.request.urlopen",
    "urllib.request.Request",
}
PY_EXEC_CALLS = {
    "os.system",
    "os.popen",
    "subprocess.run",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "subprocess.Popen",
    "asyncio.create_subprocess_shell",
    "eval",
    "exec",
}
SECRET_PATH_PATTERNS = [r"~?/\.ssh", r"\.env\b", r"authorized_keys", r"id_rsa", r"\.npmrc\b"]
SHELL_SOURCE_PATTERNS = [r"\$[A-Z_][A-Z0-9_]*", r"\.env\b", r"~?/\.ssh", r"authorized_keys", r"id_rsa"]
SHELL_NETWORK_PATTERNS = [r"curl\b", r"wget\b", r"nc\b", r"scp\b", r"rsync\b", r"python\s+-c.*requests\.post"]
SHELL_EXEC_PATTERNS = [r"bash\s+-c", r"sh\s+-c", r"eval\b", r"source\b", r"\.\s+"]
JS_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
JS_SOURCE_PATTERNS = [
    re.compile(r"\bprocess\.env\.[A-Z0-9_]+\b"),
    re.compile(r"\bprocess\.env\[['\"][A-Z0-9_]+['\"]\]"),
    re.compile(r"\bDeno\.env\.get\s*\("),
    re.compile(r"\bBun\.env\.[A-Z0-9_]+\b"),
]
JS_SECRET_FILE_PATTERNS = [
    re.compile(r"['\"][^'\"]*\.env[^'\"]*['\"]", re.IGNORECASE),
    re.compile(r"['\"][^'\"]*id_rsa[^'\"]*['\"]", re.IGNORECASE),
    re.compile(r"['\"][^'\"]*authorized_keys[^'\"]*['\"]", re.IGNORECASE),
    re.compile(r"['\"][^'\"]*\.ssh[^'\"]*['\"]", re.IGNORECASE),
]
JS_NETWORK_PATTERNS = [
    re.compile(r"\bfetch\s*\("),
    re.compile(r"\baxios\.(?:post|put|get)\s*\("),
    re.compile(r"\bgot\.(?:post|put|get)\s*\("),
    re.compile(r"\brequest\.(?:post|put|get)\s*\("),
    re.compile(r"\b(?:http|https)\.request\s*\("),
    re.compile(r"\b[A-Za-z_$][\w$]*\.(?:post|put|request)\s*\("),
]
JS_EXEC_PATTERNS = [
    re.compile(r"\b(?:exec|execSync|spawn|spawnSync|execa|execaCommand|execaCommandSync)\s*\("),
]
JS_FUNCTION_PATTERNS = [
    re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+\w+\s*\(([^)]*)\)\s*\{?"),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>\s*\{?"),
]


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

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
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

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        taint = self._taint_from_expr(node.value)
        if taint is not None:
            for name in _extract_names(node.target):
                self.taints[name] = taint
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = _call_name(node)
        if _is_python_network_sink(call_name) and "DATAFLOW_SECRET_TO_NETWORK" in self.rules:
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
        if _is_python_exec_sink(call_name) and "DATAFLOW_TAINTED_TO_EXEC" in self.rules:
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
        if isinstance(node, ast.Attribute):
            base = self._taint_from_expr(node.value, include_function_args=include_function_args)
            if base is not None:
                return base
            return None
        if isinstance(node, ast.Subscript) and _looks_like_os_environ(node):
            return Taint(kind="env", lineno=node.lineno, detail="os.environ access")
        if isinstance(node, ast.Subscript):
            return self._taint_from_expr(node.value, include_function_args=include_function_args)
        if isinstance(node, ast.Call):
            call_name = _call_name(node)
            if call_name in PY_SOURCE_CALLS:
                return Taint(kind="env", lineno=node.lineno, detail=call_name)
            if call_name == "open" and node.args:
                secret_path = _string_constant(node.args[0])
                if secret_path and _is_secret_path(secret_path):
                    return Taint(kind="secret-file", lineno=node.lineno, detail=secret_path)
            if call_name in {"Path", "pathlib.Path"} and node.args:
                secret_path = _string_constant(node.args[0])
                if secret_path and _is_secret_path(secret_path):
                    return Taint(kind="secret-file", lineno=node.lineno, detail=secret_path)
            if isinstance(node.func, ast.Attribute) and node.func.attr in {"read_text", "read_bytes"}:
                return self._taint_from_expr(node.func.value, include_function_args=include_function_args)
            if call_name in {"Path.read_text", "Path.read_bytes", "pathlib.Path.read_text", "pathlib.Path.read_bytes"}:
                if isinstance(node.func, ast.Attribute):
                    return self._taint_from_expr(node.func.value, include_function_args=include_function_args)
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
            elif path.suffix.lower() in JS_EXTENSIONS:
                findings.extend(self._scan_javascript(path, workspace))
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

    def _scan_javascript(self, path: Path, workspace: PreparedWorkspace) -> list[Finding]:
        try:
            text = read_text(path)
        except OSError:
            return []
        findings: list[Finding] = []
        lines = text.splitlines()
        taints: dict[str, Taint] = {}
        brace_depth = 0
        function_stack: list[tuple[int, set[str]]] = []

        for idx, line in enumerate(lines, start=1):
            while function_stack and brace_depth < function_stack[-1][0]:
                function_stack.pop()

            for name, taint in _js_assignment_taints(line, idx, taints):
                taints[name] = taint

            params = _js_function_params(line)
            if params is not None:
                function_stack.append((brace_depth + line.count("{"), params))

            active_args = function_stack[-1][1] if function_stack else set()
            statement = _collect_js_statement(lines, idx)
            network_taint = _js_taint_for_sink(statement, taints, set(), idx)
            if network_taint and _contains_js_sink(statement, JS_NETWORK_PATTERNS) and "DATAFLOW_JS_SECRET_TO_NETWORK" in self.rules:
                findings.append(
                    _finding_from_call(
                        rule=self.rules["DATAFLOW_JS_SECRET_TO_NETWORK"],
                        lineno=idx,
                        text=text,
                        detail=network_taint.detail,
                        override_title="Sensitive source flows to network sink in JS/TS",
                    )
                )

            exec_taint = _js_taint_for_sink(statement, taints, active_args, idx)
            if exec_taint and _contains_js_sink(statement, JS_EXEC_PATTERNS) and "DATAFLOW_JS_INPUT_TO_EXEC" in self.rules:
                findings.append(
                    _finding_from_call(
                        rule=self.rules["DATAFLOW_JS_INPUT_TO_EXEC"],
                        lineno=idx,
                        text=text,
                        detail=exec_taint.detail,
                    )
                )
            brace_depth += line.count("{") - line.count("}")

        for finding in findings:
            finding.evidence.file = workspace.relpath(path)
        return _dedupe_line_findings(findings)



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



def _is_python_network_sink(call_name: str | None) -> bool:
    if call_name is None:
        return False
    if call_name in PY_NETWORK_CALLS:
        return True
    return call_name.endswith((".post", ".put", ".urlopen", ".request"))



def _is_python_exec_sink(call_name: str | None) -> bool:
    if call_name is None:
        return False
    if call_name in PY_EXEC_CALLS:
        return True
    return call_name.endswith(
        (
            ".run",
            ".call",
            ".check_call",
            ".check_output",
            ".Popen",
            ".popen",
            ".create_subprocess_shell",
        )
    )



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



def _js_assignment_taints(line: str, lineno: int, taints: dict[str, Taint]) -> list[tuple[str, Taint]]:
    match = re.match(r"^\s*(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(.+?);?\s*$", line)
    if not match:
        return []
    name, rhs = match.groups()
    taint = _js_taint_from_rhs(rhs, lineno, taints)
    if taint is None:
        return []
    return [(name, taint)]



def _js_taint_from_rhs(rhs: str, lineno: int, taints: dict[str, Taint]) -> Taint | None:
    for pattern in JS_SOURCE_PATTERNS:
        if pattern.search(rhs):
            return Taint(kind="env", lineno=lineno, detail="js env access")
    if ("readFileSync" in rhs or "readFile(" in rhs or "readFile " in rhs) and any(
        pattern.search(rhs) for pattern in JS_SECRET_FILE_PATTERNS
    ):
        return Taint(kind="secret-file", lineno=lineno, detail="js secret file read")
    for name, taint in taints.items():
        if re.search(rf"\b{re.escape(name)}\b", rhs):
            return taint
    return None



def _js_function_params(line: str) -> set[str] | None:
    for pattern in JS_FUNCTION_PATTERNS:
        match = pattern.match(line)
        if not match:
            continue
        params = {
            param.strip()
            for param in match.group(1).split(",")
            if param.strip() and re.match(r"^[A-Za-z_$][\w$]*$", param.strip())
        }
        return params
    return None



def _contains_js_sink(line: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(pattern.search(line) for pattern in patterns)



def _js_taint_for_sink(
    line: str,
    taints: dict[str, Taint],
    function_args: set[str],
    lineno: int,
) -> Taint | None:
    for pattern in JS_SOURCE_PATTERNS:
        if pattern.search(line):
            return Taint(kind="env", lineno=lineno, detail="js env access")
    if ("readFileSync" in line or "readFile(" in line or "readFile " in line) and any(
        pattern.search(line) for pattern in JS_SECRET_FILE_PATTERNS
    ):
        return Taint(kind="secret-file", lineno=lineno, detail="js secret file read")
    for name, taint in taints.items():
        if re.search(rf"\b{re.escape(name)}\b", line):
            return taint
    for arg in function_args:
        if re.search(rf"\b{re.escape(arg)}\b", line):
            return Taint(kind="function-arg", lineno=lineno, detail=f"function argument: {arg}")
    return None



def _dedupe_line_findings(findings: list[Finding]) -> list[Finding]:
    seen: set[tuple[str, str | None, int | None]] = set()
    unique: list[Finding] = []
    for finding in findings:
        key = (finding.rule_id, finding.evidence.file, finding.evidence.line_start)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique



def _collect_js_statement(lines: list[str], line_number: int, window: int = 6) -> str:
    start = max(0, line_number - 1)
    chunk = []
    balance = 0
    for line in lines[start : min(len(lines), start + window)]:
        chunk.append(line)
        balance += line.count("(") - line.count(")")
        if balance <= 0 and (";" in line or ")" in line):
            break
    return "\n".join(chunk)
