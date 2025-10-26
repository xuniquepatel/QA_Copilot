import pathlib, subprocess, json

class Complexity:
    def __init__(self, repo_root: pathlib.Path):
        self.repo_root = repo_root

    def compute(self):
        """Return {filepath: [ {name, complexity, ...}, ... ]} via radon cc JSON."""
        try:
            out = subprocess.check_output(["radon", "cc", "-j", str(self.repo_root)], text=True)
            return json.loads(out)
        except Exception:
            return {}
