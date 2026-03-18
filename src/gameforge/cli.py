"""GameForge CLI — AI Game Development Studio."""

import click


@click.group()
@click.version_option(version="0.1.0")
def main():
    """GameForge — Turn a GDD into a playable game with multi-agent AI."""
    pass


@main.command()
@click.argument("gdd_path", type=click.Path(exists=True))
@click.option("--model", default="claude-sonnet-4-6", help="LLM model for agents")
@click.option("--dry-run", is_flag=True, help="Parse GDD and show plan without executing")
def run(gdd_path: str, model: str, dry_run: bool):
    """Run GameForge on a Game Design Document."""
    click.echo(f"📄 Loading GDD: {gdd_path}")
    click.echo(f"🤖 Model: {model}")

    if dry_run:
        click.echo("🔍 Dry run — showing execution plan only")
    else:
        click.echo("🚀 Starting GameForge pipeline...")

    # TODO: Implement pipeline
    click.echo("⚠️  Not yet implemented. See ARCHITECTURE.md for design.")


@main.command()
@click.argument("gdd_path", type=click.Path(exists=True))
def plan(gdd_path: str):
    """Parse a GDD and show the milestone plan without executing."""
    click.echo(f"📄 Parsing GDD: {gdd_path}")
    # TODO: Implement producer
    click.echo("⚠️  Not yet implemented.")


if __name__ == "__main__":
    main()
