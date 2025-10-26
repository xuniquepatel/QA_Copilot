import ast, pathlib

class Locator:
    def __init__(self, repo_root: pathlib.Path, coverage):
        self.repo_root = repo_root
        self.coverage = coverage or {"covered": {}, "totals": {}}

    def find_targets(self):
        """Scan .py files; for each function, compute uncovered lines & simple predicates."""
        targets = []
        for path in self.repo_root.rglob("*.py"):
            # skip tests & venv/site-packages
            s = str(path)
            if "tests/" in s or "/.venv/" in s or "/site-packages/" in s:
                continue
            try:
                src = path.read_text(encoding="utf-8")
                tree = ast.parse(src)
            except Exception:
                continue
            cov_set = self.coverage["covered"].get(str(path.resolve()), set())

            class FuncVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.items = []
                def visit_FunctionDef(self, node: ast.FunctionDef):
                    lines = set(range(node.lineno, getattr(node, 'end_lineno', node.lineno)+1))
                    uncovered = sorted(list(lines - set(cov_set)))
                    preds = []
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Compare):
                            preds.append(ast.get_source_segment(src, sub) or "compare")
                        if isinstance(sub, ast.If):
                            preds.append("if:" + (ast.get_source_segment(src, sub.test) or "cond"))
                    if uncovered:
                        self.items.append({"function": node.name, "uncovered": uncovered,
                                           "predicates": preds, "file": str(path.resolve())})
            v = FuncVisitor()
            v.visit(tree)
            targets.extend(v.items)
        targets.sort(key=lambda t: len(t["uncovered"]), reverse=True)
        return targets
