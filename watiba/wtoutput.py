from dataclasses import dataclass, field
from typing import List


@dataclass
class WTOutput:
    """Captured output and execution metadata for a Watiba command."""

    stdout: List[str] = field(default_factory=list)
    stderr: List[str] = field(default_factory=list)
    exit_code: int = 0
    cwd: str = "."
