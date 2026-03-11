"""Base Translator interface.

Translators convert a framework-agnostic ExecutionPlan
into runnable multi-agent code for a specific runtime.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from gameforge.models.plan import ExecutionPlan


@dataclass
class ProjectFiles:
    """Generated source files ready to run."""
    files: dict[str, str]  # filename -> content
    entrypoint: str        # which file to run (e.g. "main.py")

    def write(self, output_dir: str) -> None:
        """Write all generated files to disk."""
        from pathlib import Path
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for filename, content in self.files.items():
            filepath = out / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content)


class Translator(ABC):
    """Converts an ExecutionPlan into runnable multi-agent code."""

    @abstractmethod
    def translate(self, plan: ExecutionPlan) -> ProjectFiles:
        """
        Input:  ExecutionPlan (framework-agnostic)
        Output: ProjectFiles (framework-specific, runnable)
        """
        ...
