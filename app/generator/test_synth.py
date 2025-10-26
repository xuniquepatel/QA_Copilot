import pathlib
from .heuristics import boundary_values_from_predicates

TEMPLATE = """\
import pytest
from {{ module_import }} import {{ function }}

@pytest.mark.parametrize("x", {{ values }})
def test_{{ function }}_autogen_branch_edges(x):
    # auto-generated boundary tests (smoke)
    _ = {{ function }}(x)
    assert True
"""

class Generator:
    def __init__(self, repo_root: pathlib.Path, write_dir: str = 'tests/autogen'):
        self.repo_root = repo_root
        self.write_dir = pathlib.Path(repo_root / write_dir)
        self.write_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, ranked_targets):
        created = []
        for t in ranked_targets:
            path = pathlib.Path(t['file'])
            module_import = self._module_path(path)
            fn = t['function']
            values = boundary_values_from_predicates(t.get('predicates', [])) or [0, 1, -1]
            test_code = (TEMPLATE
                         .replace("{{ module_import }}", module_import)
                         .replace("{{ function }}", fn)
                         .replace("{{ values }}", str(values)))
            out = self.write_dir / f"test_autogen_{path.stem}_{fn}.py"
            out.write_text(test_code, encoding='utf-8')
            created.append(str(out))
        return created

    def _module_path(self, file_path: pathlib.Path) -> str:
        # repo_root/pkg/foo.py -> pkg.foo
        rel = file_path.resolve().relative_to(self.repo_root.resolve())
        parts = list(rel.parts)
        parts[-1] = parts[-1].replace('.py', '')
        return ".".join(parts)
