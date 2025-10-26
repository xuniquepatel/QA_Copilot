import pathlib, subprocess, json, time, shutil

class Validator:
    def __init__(self, repo_root: pathlib.Path, use_mut: bool = False, keep_threshold: float = 2.0, minutes: int = 10):
        self.repo_root = repo_root
        self.use_mut = use_mut
        self.keep_threshold = float(keep_threshold)
        self.minutes = int(minutes)
        self.created_path = repo_root/".qa_copilot_created.json"
        self.ledger_path = repo_root/".qa_copilot_ledger.json"

    def run(self):
        start = time.time()
        created = []
        if self.created_path.exists():
            created = json.loads(self.created_path.read_text())
        ledger = {"kept": [], "reverted": [], "baseline": {}, "final": {}}

        # Baselines
        base_cov = self._coverage_percent()
        base_mut = self._mutation_score() if self.use_mut else 0.0
        ledger["baseline"] = {"coverage": base_cov, "mutation": base_mut}

        cov_now, mut_now = base_cov, base_mut

        # Greedy per-test acceptance: keep only if improves mutation (>= threshold) OR coverage increases
        for test_file in created:
            if (time.time() - start) > self.minutes * 60:
                break  # time budget reached

            # Ensure the test exists (generator wrote it)
            tpath = pathlib.Path(test_file)
            if not tpath.exists():
                continue

            # Evaluate with this test present
            cov_after = self._coverage_percent()
            mut_after = self._mutation_score() if self.use_mut else 0.0

            delta_cov = cov_after - cov_now
            delta_mut = mut_after - mut_now

            accept = (delta_mut >= self.keep_threshold) or (delta_cov > 0.0)

            if accept:
                ledger["kept"].append({
                    "file": test_file,
                    "delta_mutation_pts": round(delta_mut, 3),
                    "delta_coverage_pts": round(delta_cov, 3)
                })
                cov_now, mut_now = cov_after, mut_after
            else:
                # revert this test file
                try:
                    tpath.unlink(missing_ok=True)
                except Exception:
                    pass
                ledger["reverted"].append({
                    "file": test_file,
                    "reason": "no improvement",
                    "delta_mutation_pts": round(delta_mut, 3),
                    "delta_coverage_pts": round(delta_cov, 3)
                })

        # Final snapshot
        final_cov = self._coverage_percent()
        final_mut = self._mutation_score() if self.use_mut else 0.0
        ledger["final"] = {"coverage": final_cov, "mutation": final_mut}

        # persist ledger
        self.ledger_path.write_text(json.dumps(ledger, indent=2))

        return {
            "coverage_before": base_cov,
            "coverage_after": final_cov,
            "coverage_delta": round(final_cov - base_cov, 3),
            "mutation_before": base_mut,
            "mutation_after": final_mut,
            "mutation_delta": round(final_mut - base_mut, 3),
            "kept": len(ledger["kept"]),
            "reverted": len(ledger["reverted"]),
            "time_sec": int(time.time() - start)
        }

    def _coverage_percent(self) -> float:
        try:
            subprocess.check_call(["coverage", "run", "-m", "pytest", "-q", str(self.repo_root)],
                                  cwd=str(self.repo_root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            out = subprocess.check_output(["coverage", "report"], cwd=str(self.repo_root), text=True)
            for line in out.strip().splitlines():
                if line.startswith("TOTAL") and "%" in line:
                    return float(line.split()[-1].strip('%'))
        except Exception:
            pass
        return 0.0

    def _mutation_score(self) -> float:
        """
        Returns mutation score in percentage using mutmut.
        Uses JSON output when available; falls back to text scraping.
        """
        try:
            # Run mutmut silently; cache speeds up repeated runs
            subprocess.check_call(["mutmut", "run", "--silent"], cwd=str(self.repo_root),
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Try JSON
            try:
                out_json = subprocess.check_output(["mutmut", "results", "--json"], cwd=str(self.repo_root), text=True)
                data = json.loads(out_json)
                killed = int(data.get("killed", 0))
                survived = int(data.get("survived", 0))
            except Exception:
                # Fallback: text summary
                out = subprocess.check_output(["mutmut", "results"], cwd=str(self.repo_root), text=True)
                killed = survived = 0
                for line in out.splitlines():
                    s = line.strip().split()
                    if not s:
                        continue
                    if s[0].lower().startswith("killed"):
                        killed = int(s[-1])
                    if s[0].lower().startswith("survived"):
                        survived = int(s[-1])
            total = killed + survived
            return (killed / total * 100.0) if total else 0.0
        except Exception:
            return 0.0
