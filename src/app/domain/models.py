"""Domain models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4


@dataclass
class PromptRecord:
    """Represents a prompt and its response."""
    
    prompt_text: str
    response_text: str
    project_name: str
    project_goal: str
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.now)
    terminal_type: str = "Terminal"
    session_id: Optional[UUID] = None
    labels: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def add_label(self, label: str) -> None:
        """Add a label to the prompt record."""
        if label not in self.labels:
            self.labels.append(label)