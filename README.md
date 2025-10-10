# QA Copilot - GenAI-Verified Test Generator

> **Automatically generates only those tests that truly catch bugs proven by increased mutation score or branch coverage while staying fully offline and CI-friendly.**

![status-badge](https://img.shields.io/badge/status-active-brightgreen)
![python-badge](https://img.shields.io/badge/python-3.10%2B-blue)

---

## Table of Contents
- [Key Value Proposition](#key-value-proposition)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Use on Your Repo](#use-on-your-repo)
- [CLI Reference](#cli-reference)
- [How It Works](#how-it-works)
- [Metrics & Acceptance Criteria](#metrics--acceptance-criteria)
- [Design Principles & Guardrails](#design-principles--guardrails)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

---

## Key Value Proposition
- **More signal, less noise**: Targets risky, **uncovered branches** first.
- **Evidence-based**: Each test must **earn its keep** if mutation score or coverage doesn’t improve, it’s reverted.
- **Offline-first**: No cloud dependency. Optional small local LLM can be added later, strictly template-constrained.
- **CI-ready**: Deterministic runs, time budgets, JSON/HTML artifacts, and a keep/revert **ledger**.

---

## Features
- **Analyzer**: Coverage (line+branch), cyclomatic complexity (radon), git churn → combined **risk score**.
- **Generator (LLM-free baseline)**: Heuristic boundary inputs from extracted predicates; writes to `tests/autogen/`.
- **Validator (advanced)**:
  - Coverage before/after
  - Mutation testing via **mutmut** (JSON parsing for real mutation score)
  - **Greedy per-test keep/revert** loop with threshold + time budget
  - **Ledger** at `.qa_copilot_ledger.json` (audit trail)
- **Reporter**: HTML report with KPIs, ledger, and top targets (SARIF export planned).
- **Safety**: Read-only codebase; writes only to `tests/autogen/`. No network calls required.

---

## System Architecture

**Flow:** Analyzer → Generator → Validator → Reporter  
- Analyzer extracts predicates & uncovered lines, computes risk (coverage gaps + CC + churn).  
- Generator emits pytest files via a strict template (no free-form code).  
- Validator accepts a test **only if** mutation score increases (≥ threshold) or branch coverage increases; else reverts.  
- Reporter outputs HTML + JSON with KPIs and decisions.

---

## Requirements
- Python **3.10+**
- Git (for churn): `git --version`
- Python packages: `pytest`, `coverage`, `radon`, `gitpython`, `jinja2`, `lxml`, `mutmut` (for mutation), optional `z3-solver`
- Install via `requirements.txt`

---

## Installation
```bash
git clone <your-repo-url> qa-copilot
cd qa-copilot
python -m venv .venv
# mac/linux
source .venv/bin/activate
# windows
# .venv\Scripts\activate
pip install -r requirements.txt
```

Sanity checks:
```bash
python -V
pytest --version
coverage --version
radon --version
git --version
```

---

## Project Structure
```
qa-copilot/
├─ qa_copilot.py               # entrypoint: python -m qa_copilot <cmd>
├─ requirements.txt
├─ Makefile
├─ README.md
├─ app/
│  ├─ __init__.py
│  ├─ cli.py                   # CLI: analyze/generate/validate/report
│  ├─ analyzer/
│  │  ├─ coverage_reader.py    # coverage.xml → covered lines
│  │  ├─ complexity.py         # radon CC
│  │  ├─ churn.py              # git churn (last N days)
│  │  ├─ locator.py            # AST → predicates, uncovered spans
│  │  └─ risk.py               # risk scoring
│  ├─ generator/
│  │  ├─ heuristics.py         # boundary inputs from predicates
│  │  └─ test_synth.py         # pytest template writer
│  ├─ validator/
│  │  └─ mutate.py             # coverage+mutmut; keep/revert; ledger
│  └─ report/
│     └─ html.py               # HTML report with KPIs + ledger
└─ example/
   └─ target_repo/
      ├─ pyproject.toml
      ├─ pkg/
      │  ├─ __init__.py
      │  └─ math_utils.py
      └─ tests/
         └─ test_math_utils.py
```

Artifacts written **inside the target repo**:
- `.qa_copilot_targets.json` — ranked targets (analyze)
- `.qa_copilot_created.json` — generated test files (generate)
- `.qa_copilot_validate.json` — validation summary (validate)
- `.qa_copilot_ledger.json` — **per-test** keep/revert ledger (validate)
- `tests/autogen/test_autogen_*.py` — accepted test files

---

## Quick Start
```bash
make demo
# or manual steps:
coverage run -m pytest -q example/target_repo
coverage xml -o example/target_repo/coverage.xml
python -m qa_copilot analyze example/target_repo --coverage example/target_repo/coverage.xml
python -m qa_copilot generate example/target_repo --top-k 3
python -m qa_copilot validate example/target_repo --mut --time-budget 5 --keep-threshold 2.0
python -m qa_copilot report example/target_repo --out report
```
Open **`report/index.html`**.

---

## Use on Your Repo

1) Generate `coverage.xml` in your project:
```bash
cd /path/to/your_repo
coverage run -m pytest
coverage xml
```

2) Run the copilot:
```bash
# from QA Copilot root (or anywhere)
python -m qa_copilot analyze /path/to/your_repo --coverage /path/to/your_repo/coverage.xml
python -m qa_copilot generate /path/to/your_repo --top-k 8 --write-dir tests/autogen
python -m qa_copilot validate /path/to/your_repo --mut --time-budget 10 --keep-threshold 2.0
python -m qa_copilot report /path/to/your_repo --out /path/to/your_repo/qa_report
```

---

## CLI Reference
```text
qa_copilot analyze <repo> [--coverage PATH]
    Load coverage + radon + churn; extract AST predicates; rank risky targets.
    → writes <repo>/.qa_copilot_targets.json

qa_copilot generate <repo> [--top-k 5] [--write-dir tests/autogen]
    Synthesize minimal pytest files (heuristics).
    → writes tests to <repo>/<write-dir>
    → writes <repo>/.qa_copilot_created.json

qa_copilot validate <repo> [--mut] [--time-budget 10] [--keep-threshold 2.0]
    Greedy per-test acceptance loop:
      keep test if mutation score ↑ (≥ threshold) OR branch coverage ↑
      else revert test file.
    → writes <repo>/.qa_copilot_validate.json
    → writes <repo>/.qa_copilot_ledger.json

qa_copilot report <repo> [--out report] [--sarif]
    Generate HTML (and SARIF later).
```

**Key Flags**
- `--mut` (validator): enable mutation testing with **mutmut** (first run warms cache).
- `--time-budget`: soft limit (minutes) for validator.
- `--keep-threshold`: minimum **mutation score delta (points)** to keep a test.
- `--write-dir`: where tests are written (default `tests/autogen`).

---

## How It Works

1) **Targeting**  
   Reads `coverage.xml` → finds **uncovered** lines inside functions, combines with **CC** (radon) + **git churn** to compute a **risk score**, and picks top-K targets.

2) **Synthesis**  
   Heuristics derive **boundary values** from branch predicates (e.g., `x < 10` → `9, 10, 11`), then emit pytest files using a **strict template**.

3) **Validation (Evidence Gate)**  
   Baseline coverage & mutation recorded. For each new test file:
   - Run coverage & mutation; compute **delta**.
   - **Keep** iff: mutation score increases by ≥ threshold **or** branch coverage increases.
   - **Revert** otherwise.  
   A **ledger** is stored with kept/reverted tests and their deltas.

4) **Reporting**  
   HTML shows KPIs (coverage Δ, mutation Δ), ledger tables, and top targets. JSON artifacts are also saved.

---

## Metrics & Acceptance Criteria
- **Mutation score Δ**: +**10–20 pts** on a medium module within **≤ 10 min** (with cache/time budget).  
- **Branch coverage Δ**: +**5–15 pts** where branch gaps exist.  
- **Retention**: ≥ **70%** of generated tests are kept after validation.  
- **Determinism**: Same seed → same accepted set and deltas.

---

## Design Principles & Guardrails
- **LLM-optional**: Baseline is fully offline. If used later, LLM is **template-constrained** and **AST-scoped**.  
- **Evidence-based acceptance**: No test merges without measurable improvement.  
- **Write boundaries**: Writes only to `tests/autogen/`.  
- **No network**: No external calls required.  
- **Reproducible**: Time budgets, seeds, cached mutation runs.

---

## Troubleshooting

**Coverage shows 0%**  
- Ensure imports resolve in your repo (see example `pyproject.toml`).  
- Run `coverage run -m pytest` **inside** the target repo, then `coverage xml`.

**Mutation runs are slow**  
- First run populates the cache; subsequent runs speed up.  
- Limit scope (future flag), increase threshold, or shorten `--time-budget`.

**Generated tests fail to import modules**  
- Validate `Generator._module_path` logic or add `pythonpath = ["."]` in your `pyproject.toml`.  
- Consider editable installs (`pip install -e .`) for larger repos.

**No targets found**  
- Ensure `coverage.xml` corresponds to the same repo path you pass to `analyze`.

---

## Roadmap
- **Flake Detector**: rerun accepted tests N× with fixed seeds; quarantine flaky cases.  
- **Module-Scoped Mutation**: mutate only modules touched by each candidate test.  
- **Z3 Branch Unlocking**: synthesize inputs for stubborn predicates.  
- **Coverage-Guided Prompting / CEGIS-lite**: feedback loop to refine inputs.  
- **SARIF Export**: PR annotations for risky lines and accepted tests.  
- **Optional Local LLM**: assert-message polish under strict constraints.

---
