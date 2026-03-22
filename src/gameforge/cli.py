"""GameForge CLI — AI Game Development Studio.

Usage:
    gf producer <gdd_path> [--output-dir ./output] [--llm] [--analyze-only]
    gf producer normalize <gdd_path> [--output normalized.md] [--llm]
    gf run <gdd_path> [--model claude-sonnet-4-6] [--dry-run]
"""

import click
from pathlib import Path


@click.group()
@click.version_option(version="0.1.0")
def main():
    """gf — GameForge: Turn a GDD into a playable game with multi-agent AI."""
    pass


# ── Producer Commands ──

@main.group()
def producer():
    """Producer commands: analyze, normalize, and plan from a GDD."""
    pass


@producer.command("analyze")
@click.argument("gdd_path", type=click.Path(exists=True))
def producer_analyze(gdd_path: str):
    """Analyze a GDD and show what's present/missing."""
    from gameforge.producer.normalizer import analyze_gdd, print_analysis

    with open(gdd_path, encoding="utf-8") as f:
        gdd = f.read()

    analysis = analyze_gdd(gdd)
    print_analysis(analysis)


@producer.command("normalize")
@click.argument("gdd_path", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output path for normalized GDD")
@click.option("--llm", is_flag=True, help="Use LLM to generate missing sections")
def producer_normalize(gdd_path: str, output: str | None, llm: bool):
    """Normalize a GDD: check missing sections and fill them in."""
    from gameforge.producer.normalizer import normalize_gdd

    with open(gdd_path, encoding="utf-8") as f:
        gdd = f.read()

    llm_fn = None
    if llm:
        llm_fn = _get_ollama_fn()

    if output is None:
        output = str(Path(gdd_path).with_suffix(".normalized.md"))

    normalize_gdd(gdd, output_path=output, llm_fn=llm_fn)


@producer.command("plan")
@click.argument("gdd_path", type=click.Path(exists=True))
@click.option("--output-dir", "-o", default="./output", help="Output directory")
@click.option("--llm", is_flag=True, help="Use LLM for plan generation")
def producer_plan(gdd_path: str, output_dir: str, llm: bool):
    """Generate execution plan: normalized GDD + milestone JSONs."""
    from gameforge.producer.producer import produce_full, produce_from_template

    if llm:
        llm_fn = _get_ollama_fn()
        gdd_path_out, milestone_paths = produce_full(gdd_path, output_dir, llm_fn=llm_fn)
    else:
        gdd_path_out, milestone_paths = produce_full(gdd_path, output_dir)


# ── Run Command (future) ──

@main.command("run")
@click.argument("gdd_path", type=click.Path(exists=True))
@click.option("--model", default="claude-sonnet-4-6", help="LLM model for agents")
@click.option("--dry-run", is_flag=True, help="Show plan without executing")
@click.option("--milestone", "-m", default=None, help="Run a specific milestone only")
def run(gdd_path: str, model: str, dry_run: bool, milestone: str | None):
    """Run GameForge on a GDD — full pipeline."""
    click.echo(f"📄 GDD: {gdd_path}")
    click.echo(f"🤖 Model: {model}")

    if dry_run:
        click.echo("🔍 Dry run — generating plan only")
        from gameforge.producer.producer import produce_full
        produce_full(gdd_path, "./output")
    else:
        click.echo("🚀 Starting GameForge pipeline...")
        click.echo("⚠️  Translator + Orchestrator not yet implemented.")
        click.echo("    Run `gf producer plan <gdd>` to generate the execution plan first.")


# ── Helpers ──

def _get_ollama_fn():
    """Get an ollama LLM function."""
    import requests

    def ollama_fn(prompt: str) -> str:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "qwen2.5:7b", "prompt": prompt, "stream": False},
            timeout=120,
        )
        return resp.json().get("response", "")

    return ollama_fn


if __name__ == "__main__":
    main()
