"""FastAPI app for the VinDine Concierge prototype."""

from dotenv import load_dotenv

load_dotenv()

from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.constraint_classifier import build_clarification_questions
from src.data_loader import get_dataset_summary, load_restaurants
from src.error_router import (
    route_error,
    save_correction_signal,
    score_adjustments_for_reason,
)
from src.llm_client import is_llm_available
from src.llm_explainer import generate_explanations
from src.logger import get_logger
from src.preference_parser import parse_user_text
from src.ranking_engine import rank_restaurants
from src.schemas import (
    ApiErrorResponse,
    ClarificationQuestion,
    ErrorRoute,
    FeedbackRequest,
    HumanRole,
    ParsePreferencesRequest,
    ParsedConstraints,
    RecommendationCard,
    RecommendationRequest,
    RecommendationResponse,
    Restaurant,
)
from src.uncertainty import assess_uncertainty

api_logger = get_logger("api")


app = FastAPI(
    title="VinDine Concierge API",
    description="Data and integration contract MVP for resort dining recommendations.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Return a consistent error shape for unexpected backend failures."""
    return JSONResponse(
        status_code=500,
        content=ApiErrorResponse(message="Internal API error", detail=str(exc)).model_dump(),
    )


def _restaurants_or_500() -> list[Restaurant]:
    try:
        return load_restaurants()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict:
    """Report service and dataset readiness."""
    restaurants = _restaurants_or_500()
    return {
        "status": "ok",
        "service": "VinDine Concierge API",
        "dataset_loaded": True,
        "restaurant_count": len(restaurants),
    }


@app.get("/restaurants", response_model=list[Restaurant])
def list_restaurants(
    brand_area: Annotated[str | None, Query()] = None,
    accept_voucher: Annotated[bool | None, Query()] = None,
    cuisine: Annotated[str | None, Query()] = None,
    max_price: Annotated[int | None, Query(ge=0)] = None,
    stroller_accessible: Annotated[bool | None, Query()] = None,
) -> list[Restaurant]:
    """Return restaurants with optional filters for frontend exploration."""
    restaurants = _restaurants_or_500()
    if brand_area:
        restaurants = [item for item in restaurants if item.brand_area == brand_area]
    if accept_voucher is not None:
        restaurants = [item for item in restaurants if item.accept_voucher is accept_voucher]
    if cuisine:
        restaurants = [item for item in restaurants if cuisine in item.cuisine_types]
    if max_price is not None:
        restaurants = [item for item in restaurants if item.avg_price_vnd <= max_price]
    if stroller_accessible is not None:
        restaurants = [item for item in restaurants if item.stroller_accessible is stroller_accessible]
    return restaurants


@app.get("/restaurants/{restaurant_id}", response_model=Restaurant)
def get_restaurant(restaurant_id: str) -> Restaurant:
    """Return one restaurant by id for card detail views."""
    for restaurant in _restaurants_or_500():
        if restaurant.id == restaurant_id:
            return restaurant
    raise HTTPException(status_code=404, detail=f"Restaurant not found: {restaurant_id}")


@app.get("/dataset/summary")
def dataset_summary() -> dict:
    """Return aggregate counts proving the dataset is diverse enough for demos."""
    return get_dataset_summary(_restaurants_or_500())


def _error_route(
    status: str,
    fallback_suggestions: list[str],
    has_risky_recommendation: bool,
) -> ErrorRoute | None:
    if status == "needs_clarification":
        return ErrorRoute(
            type="low_confidence",
            user_message="Mình cần thêm thông tin trước khi chốt gợi ý đáng tin cậy.",
            next_action="ask_clarification",
            recover_options=[
                "Cho biết khu/sảnh hiện tại",
                "Cho biết loại voucher nếu có",
                "Nêu rõ ngân sách hoặc khẩu vị ưu tiên",
            ],
            learning_signal="Parser lacks important context such as location or voucher_type.",
        )
    if status == "no_match":
        return ErrorRoute(
            type="no_match",
            user_message="Chưa tìm thấy lựa chọn thỏa các điều kiện cứng hiện tại.",
            next_action="relax_constraint",
            recover_options=fallback_suggestions,
            learning_signal="Ranking has no candidate after hard filters.",
        )
    if has_risky_recommendation:
        return ErrorRoute(
            type="risky_recommendation",
            user_message="Có gợi ý dùng được nhưng còn trade-off cần người dùng kiểm tra.",
            next_action="human_review",
            recover_options=[
                "Kiểm tra lại voucher tại quầy trước khi đi",
                "Xác nhận nhóm đồng ý khoảng cách đi bộ",
                "Kiểm tra thực đơn/menu trước khi đi",
            ],
            learning_signal="Top recommendation has missing_info or notable trade_offs.",
        )
    return None


def _debug(mode: str, parser: str, restaurants: list[Restaurant]) -> dict:
    return {
        "mode": mode,
        "parser": parser,
        "ranker": "rank_restaurants",
        "restaurant_count": len(restaurants),
    }


def _response_payload(
    *,
    status: str,
    parsed_constraints: ParsedConstraints,
    recommendations: list[RecommendationCard],
    fallback_suggestions: list[str],
    clarification_questions: list[ClarificationQuestion],
    uncertainty: dict,
    error_route: ErrorRoute | None,
    ai_explanations: dict | None,
    debug: dict,
) -> dict:
    """Return both the legacy response contract and the boss-requested contract."""
    response_type = "clarification" if status == "needs_clarification" else "recommendation"
    if status in {"no_match", "error"}:
        response_type = status

    legacy = RecommendationResponse(
        status=status,
        parsed_constraints=parsed_constraints,
        clarification_questions=clarification_questions,
        recommendations=recommendations,
        fallback_suggestions=fallback_suggestions,
        ai_explanations=ai_explanations,
        error_route=error_route,
        human_role=HumanRole(),
        debug=debug,
    ).model_dump()
    legacy.update(
        {
            "type": response_type,
            "questions": [question.model_dump() for question in clarification_questions],
            "top_results": [card.model_dump() for card in recommendations],
            "fallback_options": fallback_suggestions,
            "uncertainty": uncertainty,
            "error_flow": route_error(uncertainty, fallback_suggestions),
        }
    )
    return legacy


@app.post("/parse-preferences")
def parse_preferences(request: ParsePreferencesRequest) -> dict:
    """Parse user text into structured constraints and uncertainty."""
    restaurants = _restaurants_or_500()
    rec_request = RecommendationRequest(user_text=request.text)
    parsed = parse_user_text(rec_request)
    if parsed == "off_topic":
        parsed = ParsedConstraints(confidence=0.0)
    uncertainty = assess_uncertainty(rec_request, parsed, restaurants=restaurants)
    return {
        "type": "parse",
        "parsed_constraints": parsed.model_dump(),
        "uncertainty": uncertainty,
    }


@app.post("/recommend")
def recommend(request: RecommendationRequest) -> dict:
    """Parse, route uncertainty, rank restaurants, and return Top 3 or clarification."""
    restaurants = _restaurants_or_500()
    mode = "llm" if is_llm_available() else "regex"
    parser_name = "llm_parser" if mode == "llm" else "regex_parser"
    api_logger.info("Recommend request | mode=%s | text=%s", mode, request.user_text[:80])

    parsed = parse_user_text(request)
    if parsed == "off_topic":
        parsed = ParsedConstraints(confidence=0.0)
        uncertainty = assess_uncertainty(request, parsed, restaurants=restaurants)
        route = ErrorRoute(
            type="missing_data",
            user_message="Xin lỗi, mình chỉ hỗ trợ tìm quán ăn trong resort thôi nhé! Hãy cho mình biết nhu cầu ăn uống của bạn.",
            next_action="ask_clarification",
            recover_options=[
                "Cho biết số người và loại đồ ăn muốn ăn",
                "Nêu vị trí hiện tại trong resort",
                "Cho biết loại voucher nếu có",
            ],
            learning_signal="User input is not related to dining.",
        )
        return _response_payload(
            status="error",
            parsed_constraints=parsed,
            recommendations=[],
            fallback_suggestions=[],
            clarification_questions=[],
            uncertainty=uncertainty,
            error_route=route,
            ai_explanations=None,
            debug=_debug(mode, "off_topic", restaurants),
        )

    recommendations, fallback_suggestions = rank_restaurants(restaurants, parsed)
    clarification_questions = build_clarification_questions(request, parsed)
    uncertainty = assess_uncertainty(
        request,
        parsed,
        recommendations,
        fallback_suggestions,
        restaurants,
    )

    ai_explanations = generate_explanations(parsed, recommendations) if recommendations else None
    if uncertainty["should_ask_clarification"]:
        status = "needs_clarification"
        recommendations = []
        fallback_suggestions = []
        ai_explanations = None
    elif not recommendations:
        status = "no_match"
    else:
        status = "success"

    has_risky = any(
        card.missing_info
        or card.missed_preferences
        or any(keyword in trade_off.lower() for keyword in ["xa", "voucher", "dietary"] for trade_off in card.trade_offs)
        for card in recommendations
    )

    api_logger.info("Recommend result | status=%s | count=%d | mode=%s", status, len(recommendations), mode)
    return _response_payload(
        status=status,
        parsed_constraints=parsed,
        recommendations=recommendations,
        fallback_suggestions=fallback_suggestions,
        clarification_questions=clarification_questions,
        uncertainty=uncertainty,
        error_route=_error_route(status, fallback_suggestions, has_risky),
        ai_explanations=ai_explanations,
        debug=_debug(mode, parser_name, restaurants),
    )


@app.post("/feedback")
def feedback(request: FeedbackRequest) -> dict:
    """Save a rejection/correction signal and return reranked suggestions."""
    restaurants = _restaurants_or_500()
    rec_request = RecommendationRequest(user_text=request.original_text)
    parsed = parse_user_text(rec_request)
    if parsed == "off_topic":
        parsed = ParsedConstraints(confidence=0.0)

    correction_saved = save_correction_signal(request, parsed)
    recommendations, fallback_suggestions = rank_restaurants(
        restaurants,
        parsed,
        rejected_ids=[request.rejected_restaurant_id],
        score_adjustments=score_adjustments_for_reason(request.reason),
    )
    uncertainty = assess_uncertainty(
        rec_request,
        parsed,
        recommendations,
        fallback_suggestions,
        restaurants,
    )
    return {
        "type": "reranked",
        "top_results": [card.model_dump() for card in recommendations],
        "recommendations": [card.model_dump() for card in recommendations],
        "fallback_options": fallback_suggestions,
        "parsed_constraints": parsed.model_dump(),
        "uncertainty": uncertainty,
        "error_flow": route_error(
            uncertainty,
            fallback_suggestions,
            correction_reason=request.reason,
        ),
        "correction_saved": correction_saved,
    }
