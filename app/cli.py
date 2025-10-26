import click, json, pathlib
from rich.console import Console
from .analyzer.coverage_reader import CoverageReader
from .analyzer.complexity import Complexity
from .analyzer.churn import Churn
from .analyzer.locator import Locator
from .analyzer.risk import score_targets
from .generator.test_synth import Generator
from .validator.mutate import Validator
from .report.html import HtmlReporter

console = Console()

@click.group()
def main():
    """QA Copilot CLI"""
    pass

@main.command()
@click.argument('repo', type=click.Path(exists=True, file_okay=False))
@click.option('--coverage', type=click.Path(exists=True), help='Path to coverage.xml')
def analyze(repo, coverage):
    """Analyze repo and print top risky targets."""
    repo = pathlib.Path(repo)
    cov = CoverageReader(repo, coverage).load()
    comp = Complexity(repo).compute()
    churn = Churn(repo).compute()
    targets = Locator(repo, cov).find_targets()
    ranked = score_targets(targets, comp, churn)
    console.rule("Top Risky Targets")
    for i, t in enumerate(ranked[:10], 1):
        console.print(f"[bold]{i}.[/bold] {t['file']}::{t['function']} "
                      f"risk={t['risk']:.3f} uncovered={len(t['uncovered'])} "
                      f"preds={t['predicates'][:2]}")
    (repo/".qa_copilot_targets.json").write_text(json.dumps(ranked, indent=2))

@main.command()
@click.argument('repo', type=click.Path(exists=True, file_okay=False))
@click.option('--top-k', default=5, show_default=True)
@click.option('--write-dir', default='tests/autogen', show_default=True)
def generate(repo, top_k, write_dir):
    """Generate test files for top-K risky targets."""
    repo = pathlib.Path(repo)
    ranked = json.loads((repo/".qa_copilot_targets.json").read_text())
    gen = Generator(repo, write_dir)
    created = gen.generate(ranked[:top_k])
    # record created files for validator
    (repo/".qa_copilot_created.json").write_text(json.dumps(created, indent=2))
    console.print(f"[green]Generated {len(created)} test file(s):[/green]")
    for p in created:
        console.print(f" - {p}")

@main.command()
@click.argument('repo', type=click.Path(exists=True, file_okay=False))
@click.option('--mut/--no-mut', default=False, show_default=True, help='Enable mutation testing')
@click.option('--time-budget', default=10, show_default=True, help='Minutes to spend')
@click.option('--keep-threshold', default=2.0, show_default=True, help='Min mutation score delta (pts) to accept')
def validate(repo, mut, time_budget, keep_threshold):
    """Validate generated tests; keep/revert with ledger."""
    repo = pathlib.Path(repo)
    v = Validator(repo, use_mut=mut, keep_threshold=keep_threshold, minutes=time_budget)
    result = v.run()
    (repo/".qa_copilot_validate.json").write_text(json.dumps(result, indent=2))
    console.print("Validation summary:", result)

@main.command()
@click.argument('repo', type=click.Path(exists=True, file_okay=False))
@click.option('--out', default='report', show_default=True)
@click.option('--sarif/--no-sarif', default=False, show_default=True)
def report(repo, out, sarif):
    """Write HTML (and optional SARIF later)."""
    repo = pathlib.Path(repo)
    HtmlReporter(repo, out).write()
    console.print(f"[cyan]Report written to {out}/index.html[/cyan]")
