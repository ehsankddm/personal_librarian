"""Action Request - Full specification per ACTION_REQUEST.md."""

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, UTC
from enum import Enum
import uuid


class ActionType(str, Enum):
    """Types of actions that require gatekeeping."""

    # Network actions
    NETWORK_FETCH = "network.fetch"
    NETWORK_UPLOAD = "network.upload"

    # Filesystem actions
    FILESYSTEM_WRITE = "filesystem.write"
    FILESYSTEM_DELETE = "filesystem.delete"

    # Process actions
    PROCESS_SPAWN = "process.spawn"

    # Compute actions
    COMPUTE_HEAVY = "compute.heavy"

    # Domain-specific actions
    BACKUP_SYNC = "backup.sync"
    DELIVERY_KINDLE_SEND = "delivery.kindle_send"
    METADATA_LOOKUP_EXTERNAL = "metadata.lookup_external"

    # Agent actions
    AGENT_CREATION = "agent_creation"


class Reversibility(str, Enum):
    """Reversibility level of an action."""

    REVERSIBLE = "reversible"
    SOFT_REVERSIBLE = "soft_reversible"
    IRREVERSIBLE = "irreversible"


class DataSensitivity(str, Enum):
    """Data sensitivity level."""

    NONE = "none"  # No user data
    LOW = "low"  # Filenames, book titles
    MEDIUM = "medium"  # Book contents but encrypted
    HIGH = "high"  # Plaintext content, credentials


@dataclass
class ActionRequest:
    """
    ActionRequest specification per ACTION_REQUEST.md.

    This is the only legal way for any agent to cause side effects in the real world.
    It provides privacy, cost, safety guarantees, auditability, and controlled evolution.
    """

    # Identity fields
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    requester_agent_id: str = ""
    requester_role: str = ""

    # Action specification
    action_type: ActionType = None
    details: dict[str, Any] = field(default_factory=dict)

    # Rationale fields
    justification: str = ""  # English explanation of why action is needed
    user_impact: str = ""  # English description of how this affects user
    data_sensitivity: DataSensitivity = DataSensitivity.NONE

    # Resource estimates
    estimated_cost_eur: float = 0.0
    estimated_runtime_sec: float = 0.0

    # Safety fields
    reversibility: Reversibility = Reversibility.REVERSIBLE
    requires_user_approval: bool = False

    # Timestamp
    timestamp_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self):
        """Validate the action request after initialization."""
        if not self.request_id:
            self.request_id = str(uuid.uuid4())
        if not self.timestamp_utc:
            self.timestamp_utc = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "request_id": self.request_id,
            "requester_agent_id": self.requester_agent_id,
            "requester_role": self.requester_role,
            "action_type": self.action_type.value if self.action_type else None,
            "details": self.details,
            "justification": self.justification,
            "user_impact": self.user_impact,
            "data_sensitivity": self.data_sensitivity.value if self.data_sensitivity else None,
            "estimated_cost_eur": self.estimated_cost_eur,
            "estimated_runtime_sec": self.estimated_runtime_sec,
            "reversibility": self.reversibility.value if self.reversibility else None,
            "requires_user_approval": self.requires_user_approval,
            "timestamp_utc": self.timestamp_utc,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionRequest":
        """Create from dictionary."""
        # Convert enum values back to enums
        if "action_type" in data and isinstance(data["action_type"], str):
            data["action_type"] = ActionType(data["action_type"])
        if "data_sensitivity" in data and isinstance(data["data_sensitivity"], str):
            data["data_sensitivity"] = DataSensitivity(data["data_sensitivity"])
        if "reversibility" in data and isinstance(data["reversibility"], str):
            data["reversibility"] = Reversibility(data["reversibility"])

        return cls(**data)

    def get_human_readable_summary(self) -> str:
        """Generate a human-readable summary for approval requests."""
        return f"""
Action Request: {self.action_type.value if self.action_type else "Unknown"}

Requester: {self.requester_agent_id} ({self.requester_role})

Justification: {self.justification}

User Impact: {self.user_impact}

Data Sensitivity: {self.data_sensitivity.value if self.data_sensitivity else "Unknown"}
Cost: €{self.estimated_cost_eur:.2f}
Runtime: {self.estimated_runtime_sec:.1f}s
Reversibility: {self.reversibility.value if self.reversibility else "Unknown"}

Requires Approval: {self.requires_user_approval}
Request ID: {self.request_id}
        """.strip()
