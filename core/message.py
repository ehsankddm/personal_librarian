"""Message types and utilities for agent communication."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Optional
from enum import Enum


class MessageType(str, Enum):
    """Types of messages agents can send."""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ESCALATION = "escalation"
    TELEMETRY = "telemetry"
    BROADCAST = "broadcast"


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


@dataclass
class Message:
    """Standard message structure for agent communication."""

    message_type: MessageType
    sender_id: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    message_id: str = ""
    receiver_id: Optional[str] = None
    task_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)  # For routing by Planner


@dataclass
class Telemetry:
    """Telemetry data for learning."""

    agent_id: str
    action: str
    success: bool
    cost: float
    duration_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Task structure for agent coordination."""

    task_id: str
    description: str
    status: TaskStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    assigned_to: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


def create_message(
    message_type: MessageType,
    sender_id: str,
    content: str,
    receiver_id: Optional[str] = None,
    **metadata,
) -> Message:
    """Helper to create a message."""
    return Message(
        message_type=message_type,
        sender_id=sender_id,
        content=content,
        receiver_id=receiver_id,
        metadata=metadata,
    )
