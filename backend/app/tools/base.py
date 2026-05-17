import json
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    success: bool
    data: Any | None = None
    error_message: str | None = None

    def to_observation(self) -> str:
        if self.success:
            payload = json.dumps(self.data) if isinstance(self.data, (dict, list)) else self.data
            return f"SUCCESS: {payload}"
        return f"ERROR: {self.error_message}"
