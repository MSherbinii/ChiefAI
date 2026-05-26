"""
Structured output models for each Chief agent.
PydanticAI enforces these schemas — no free-form text responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class HealthRecommendation(BaseModel):
    """Pulse agent structured response."""
    summary: str = Field(description="2-3 sentence summary of health status")
    action: str = Field(description="Single most important action for today")
    status: Literal['ok', 'med', 'high', 'crit'] = Field(description="Overall health status")
    recovery_score: Optional[float] = Field(default=None, ge=0, le=100)
    sleep_hours: Optional[float] = Field(default=None, ge=0, le=24)
    workout_recommendation: Optional[str] = None
    confidence: Literal['high', 'medium', 'low'] = 'medium'
    data_sources: list[str] = Field(default_factory=list, description="Which data sources were used")


class CommunicationAnalysis(BaseModel):
    """Echo agent structured response."""
    summary: str = Field(description="2-3 sentence summary of comms status")
    stale_count: int = Field(ge=0, description="Number of threads needing attention")
    most_urgent: Optional[str] = Field(default=None, description="Subject of most urgent thread")
    action: str = Field(description="Single most important action")
    draft_available: bool = False
    draft_content: Optional[str] = None
    confidence: Literal['high', 'medium', 'low'] = 'medium'
    data_sources: list[str] = Field(default_factory=list)


class ProjectStatus(BaseModel):
    """Forge agent structured response."""
    summary: str = Field(description="2-3 sentence summary of project velocity")
    active_projects: int = Field(ge=0)
    commits_this_week: int = Field(ge=0)
    velocity_trend: Literal['improving', 'stable', 'declining', 'no_data']
    top_repo: Optional[str] = None
    next_action: str = Field(description="Single highest-value next action")
    deadline_risk: Optional[str] = Field(default=None, description="Project at risk if any")
    confidence: Literal['high', 'medium', 'low'] = 'medium'
    data_sources: list[str] = Field(default_factory=list)


class ChiefResponse(BaseModel):
    """General Chief orchestrator response."""
    reply: str = Field(description="Natural language response to user")
    agent: str = Field(description="Which agent handled this")
    action_required: bool = False
    action_type: Optional[str] = None
    context_capsule: Optional[dict] = None
    confidence: Literal['high', 'medium', 'low'] = 'medium'


class GuardrailViolation(BaseModel):
    """Returned when a guardrail blocks a response."""
    blocked: bool = True
    reason: str
    safe_response: str = "I can't help with that in this context."
