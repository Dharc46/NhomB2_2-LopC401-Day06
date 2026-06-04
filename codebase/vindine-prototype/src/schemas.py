"""Shared API and dataset schemas for VinDine Concierge."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


PriceTier = Literal["budget", "mid", "premium", "luxury"]
SourceStatus = Literal["verified_name", "realistic_mock", "synthetic"]
ResponseStatus = Literal["success", "needs_clarification", "no_match", "error"]
ConfidenceLabel = Literal["low", "medium", "high"]
ErrorRouteType = Literal["low_confidence", "no_match", "risky_recommendation", "missing_data"]
NextAction = Literal["ask_clarification", "relax_constraint", "show_fallback", "human_review"]


class GroupSuitability(BaseModel):
    kids: int = Field(ge=1, le=5)
    elderly: int = Field(ge=1, le=5)
    large_group: int = Field(ge=1, le=5)
    couple: int = Field(ge=1, le=5)


class OpeningHours(BaseModel):
    breakfast: str | None = None
    lunch: str | None = None
    dinner: str | None = None
    all_day: str | None = None


class Restaurant(BaseModel):
    id: str
    name: str
    brand_area: str
    zone: str
    location_hint: str
    distance_text: str
    distance_minutes: int = Field(ge=0)
    accept_voucher: bool
    voucher_types: list[str]
    avg_price_vnd: int = Field(ge=0)
    price_tier: PriceTier
    cuisine_types: list[str]
    menu_tags: list[str]
    dietary_tags: list[str]
    group_suitability: GroupSuitability
    stroller_accessible: bool
    wheelchair_accessible: bool
    quiet_level: int = Field(ge=1, le=5)
    crowd_level: int = Field(ge=1, le=5)
    indoor: bool
    outdoor: bool
    opening_hours: OpeningHours
    best_for: list[str]
    avoid_if: list[str]
    source_status: SourceStatus
    source_note: str
    last_checked: str

    @field_validator("id")
    @classmethod
    def id_must_be_kebab_case(cls, value: str) -> str:
        if not value or value != value.lower() or " " in value:
            raise ValueError("id must be non-empty kebab-case")
        return value


class RecommendationRequest(BaseModel):
    user_text: str = Field(min_length=1)
    current_zone: str | None = None
    voucher_type: str | None = None
    party_size: int | None = Field(default=None, ge=1)
    correction: str | None = None


class ParsedConstraints(BaseModel):
    party_size: int | None = None
    current_zone: str | None = None
    has_kids: bool = False
    has_elderly: bool = False
    needs_stroller: bool = False
    needs_wheelchair: bool = False
    budget_per_person: int | None = None
    voucher_required: bool = False
    voucher_type: str | None = None
    preferred_cuisines: list[str] = Field(default_factory=list)
    dietary_needs: list[str] = Field(default_factory=list)
    quiet_preferred: bool = False
    max_distance_minutes: int | None = None
    hard_constraints: list[str] = Field(default_factory=list)
    soft_preferences: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class RecommendationCard(BaseModel):
    restaurant_id: str
    name: str
    fit_score: float
    rank: int
    zone: str
    brand_area: str
    distance_text: str
    avg_price_vnd: int
    accept_voucher: bool
    voucher_match: bool
    reasons: list[str]
    trade_offs: list[str]
    least_satisfied_person: str | None = None
    confidence: float = Field(ge=0, le=1)
    confidence_label: ConfidenceLabel
    missing_info: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    source_status: SourceStatus


class ClarificationQuestion(BaseModel):
    id: str
    question: str
    options: list[str] = Field(default_factory=list)


class ErrorRoute(BaseModel):
    type: ErrorRouteType
    user_message: str
    next_action: NextAction
    recover_options: list[str]
    learning_signal: str | None = None


class HumanRole(BaseModel):
    decider: str = "Người đại diện nhóm chọn quán cuối cùng"
    reviewer: str = "Người dùng kiểm tra voucher/khoảng cách/dietary trước khi đi"
    rescuer: str = "Người dùng reject gợi ý sai và yêu cầu re-rank"
    trainer: str = "Correction được log để cải thiện ranking"


class RecommendationResponse(BaseModel):
    status: ResponseStatus
    parsed_constraints: ParsedConstraints
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    recommendations: list[RecommendationCard] = Field(default_factory=list)
    fallback_suggestions: list[str] = Field(default_factory=list)
    error_route: ErrorRoute | None = None
    human_role: HumanRole = Field(default_factory=HumanRole)
    debug: dict[str, Any] | None = None


class ApiErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    message: str
    detail: Any | None = None
