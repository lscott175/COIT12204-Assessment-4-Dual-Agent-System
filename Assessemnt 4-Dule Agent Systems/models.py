from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field, ValidationError


class MessageSchema(BaseModel):
    sender: str = Field(..., description="ID or role of the sending entity")
    receiver: str = Field(..., description="ID or role of the receiving entity")
    intent: Literal[
        "propose_plan",
        "validate_itinerary",
        "request_revision",
        "approve_plan",
        "finalise_output",
    ] = Field(..., description="The communicative intent of the message")
    content: Dict[str, Any] = Field(
        ..., description="The payload data (itinerary, critique, or stats)"
    )
    constraints: Optional[Dict[str, Any]] = Field(
        default=None, description="Operational constraints like budgets or formats"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class AgentResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None