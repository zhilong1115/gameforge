"""GameForge CLI — entry point."""

import json
from pathlib import Path

import click
from rich.console import Console
from rich.syntax import Syntax

console = Console()


@click.group()
def main():
    """GameForge — AI Game Development Studio"""
    pass


@main.command()
@click.argument("game_design", type=click.Path(exists=True))
@click.option("--model", default="claude-opus-4-6", help="LLM model for the Producer")
@click.option("--output", "-o", default="execution_plan.json", help="Output plan file")
@click.option("--provider", type=click.Choice(["anthropic", "openai"]), default="anthropic")
def plan(game_design: str, model: str, output: str, provider: str):
    """Generate an execution plan from a game design document."""
    from gameforge.producer import Producer
    from gameforge.tools.llm import AnthropicClient, OpenAIClient

    console.print(f"[bold]Reading game design:[/bold] {game_design}")

    if provider == "anthropic":
        llm = AnthropicClient(default_model=model)
    else:
        llm = OpenAIClient(default_model=model)

    producer = Producer(llm=llm, model=model)
    execution_plan = producer.generate_plan(game_design)

    # Write plan
    plan_json = execution_plan.model_dump_json(indent=2)
    Path(output).write_text(plan_json)

    console.print(f"\n[green]✅ Plan written to {output}[/green]")
    console.print(f"   Game: {execution_plan.game.name}")
    console.print(f"   Milestones: {len(execution_plan.milestones)}")
    console.print(f"   Adapter needed: {execution_plan.adapter_needed}")

    # Show milestones
    for m in execution_plan.milestones:
        console.print(f"   [{m.id}] {m.name} — {m.goal}")


@main.command()
@click.argument("plan_file", type=click.Path(exists=True))
@click.option("--runtime", type=click.Choice(["autogen"]), default="autogen")
@click.option("--output-dir", "-o", default="./generated", help="Output directory")
def translate(plan_file: str, runtime: str, output_dir: str):
    """Translate an execution plan into runnable multi-agent code."""
    from gameforge.models.plan import ExecutionPlan
    from gameforge.translator import AutoGenTranslator

    console.print(f"[bold]Reading plan:[/bold] {plan_file}")

    plan_data = json.loads(Path(plan_file).read_text())
    plan = ExecutionPlan(**plan_data)

    if runtime == "autogen":
        translator = AutoGenTranslator()
    else:
        raise ValueError(f"Unknown runtime: {runtime}")

    project = translator.translate(plan)
    project.write(output_dir)

    console.print(f"\n[green]✅ Generated {len(project.files)} files in {output_dir}/[/green]")
    console.print(f"   Entrypoint: {project.entrypoint}")
    for filename in project.files:
        console.print(f"   📄 {filename}")


@main.command()
@click.argument("plan_file", type=click.Path(exists=True))
def show(plan_file: str):
    """Pretty-print an execution plan."""
    plan_data = json.loads(Path(plan_file).read_text())
    syntax = Syntax(json.dumps(plan_data, indent=2), "json", theme="monokai")
    console.print(syntax)


if __name__ == "__main__":
    main()
