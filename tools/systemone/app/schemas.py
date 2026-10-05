"""System One request/response shapes (typesafe-compatible)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, RootModel


JsonValue = Any


class NoulCriteria(BaseModel):
    true: JsonValue | None = None
    false: JsonValue | None = None


class NoulQuestion(BaseModel):
    type: Literal["noul"] = "noul"
    instructions: JsonValue | None = None
    criteria: NoulCriteria | None = None


class ChoiceQuestion(BaseModel):
    type: Literal["choice"] = "choice"
    criteria: dict[str, JsonValue]
    instructions: JsonValue | None = None


class ScoreQuestion(BaseModel):
    type: Literal["score"] = "score"
    criteria: list[JsonValue] = Field(min_length=2, max_length=10)
    instructions: JsonValue | None = None


DecisionQuestion = Annotated[
    NoulQuestion | ChoiceQuestion | ScoreQuestion,
    Field(discriminator="type"),
]


class NoulAnswer(BaseModel):
    type: Literal["noul"] = "noul"
    noul: float


class ChoiceAnswer(BaseModel):
    type: Literal["choice"] = "choice"
    choice: str
    confidence: float
    probabilities: dict[str, float]


class ScoreAnswer(BaseModel):
    type: Literal["score"] = "score"
    score: float
    confidence: float
    probabilities: dict[str, float]
    legend: dict[str, JsonValue] = Field(default_factory=dict)


DecisionAnswer = Annotated[
    NoulAnswer | ChoiceAnswer | ScoreAnswer,
    Field(discriminator="type"),
]


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float | None = None


class SystemOneRequest(BaseModel):
    state: JsonValue
    questions: dict[str, DecisionQuestion] = Field(min_length=1)
    model: str | None = None


class SystemOneResponse(BaseModel):
    model: str
    answers: dict[str, DecisionAnswer]
    usage: Usage = Field(default_factory=Usage)
    id: str | None = None
    provider: str | None = None


class ModelMetadata(BaseModel):
    name: str
    description: str | None = None


class ModelMetadataList(BaseModel):
    models: list[ModelMetadata]


class QuestionsMap(RootModel[dict[str, DecisionQuestion]]):
    root: dict[str, DecisionQuestion]
