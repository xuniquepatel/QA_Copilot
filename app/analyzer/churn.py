import pathlib
from git import Repo

class Churn:
    def __init__(self, repo_root: pathlib.Path, days: int = 90):
        self.repo_root = repo_root
        self.days = days

    def compute(self):
        data = {}
        try:
            repo = Repo(str(self.repo_root), search_parent_directories=True)
            for commit in repo.iter_commits(since=f"{self.days}.days"):
                for f in commit.stats.files.keys():
                    path = (self.repo_root / f).resolve()
                    data[str(path)] = data.get(str(path), 0) + 1
        except Exception:
            pass
        return data
