from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TurnIntent = Literal[
    "problem_statement",
    "agent_option_selection",
    "user_introduced_metaphor",
    "refinement_request",
    "ambiguous",
]


class MetaphorChoice(BaseModel):
    label: Literal["A", "B", "C"]
    text: str = Field(min_length=1)


class ArtifactMetadata(BaseModel):
    clarifier_asked: bool = False
    internal_candidate_count: int = 0
    selected_option: Literal["A", "B", "C"] | None = None


class ArtifactView(BaseModel):
    artifact_type: str
    content: str
    metadata: ArtifactMetadata | None = None
    choices: list[MetaphorChoice] = Field(default_factory=list)


class SessionContextUpdate(BaseModel):
    active_metaphor_seed: str | None = None
    last_user_intent: TurnIntent | None = None
    sensory_mode: str | None = None
    suggestion_basis: str | None = None


class StartSessionRequest(BaseModel):
    mode: str


class MessageRequest(BaseModel):
    token: str
    content: str


class ChatResponse(BaseModel):
    token: str
    mode: str
    state: str
    assistant_message: str
    artifacts: list[ArtifactView] = Field(default_factory=list)
