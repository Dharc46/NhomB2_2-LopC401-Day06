"""FastAPI app for the VinDine Concierge data/glue slice."""

from dotenv import load_dotenv

load_dotenv()

from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.constraint_classifier import build_clarification_questions
from src.data_loader import get_dataset_summary, load_restaurants
from src.llm_client import is_llm_available
from src.llm_explainer import generate_explanations
from src.logger import get_logger
from src.preference_parser import parse_user_text
from src.ranking_engine import rank_restaurants
from src.schemas import (
    ApiErrorResponse,
    ClarificationQuestion,
    ErrorRoute,
    HumanRole,
    ParsedConstraints,
    RecommendationRequest,
    RecommendationResponse,
    Restaurant,
)

api_logger = get_logger("api")


app = FastAPI(
    title="VinDine Concierge API",
    description="Data and integration contract MVP for resort dining recommendations.",
    version="0.1.0",
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
        content=ApiErrorResponse(
            message="Internal API error", detail=str(exc)
        ).model_dump(),
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
        restaurants = [
            item for item in restaurants if item.accept_voucher is accept_voucher
        ]
    if cuisine:
        restaurants = [item for item in restaurants if cuisine in item.cuisine_types]
    if max_price is not None:
        restaurants = [item for item in restaurants if item.avg_price_vnd <= max_price]
    if stroller_accessible is not None:
        restaurants = [
            item
            for item in restaurants
            if item.stroller_accessible is stroller_accessible
        ]
    return restaurants


@app.get("/restaurants/{restaurant_id}", response_model=Restaurant)
def get_restaurant(restaurant_id: str) -> Restaurant:
    """Return one restaurant by id for card detail views."""
    for restaurant in _restaurants_or_500():
        if restaurant.id == restaurant_id:
            return restaurant
    raise HTTPException(
        status_code=404, detail=f"Restaurant not found: {restaurant_id}"
    )


@app.get("/dataset/summary")
def dataset_summary() -> dict:
    """Return aggregate counts proving the dataset is diverse enough for demos."""
    return get_dataset_summary(_restaurants_or_500())


def _clarification_questions(
    request: RecommendationRequest, confidence: float
) -> list[ClarificationQuestion]:
    questions: list[ClarificationQuestion] = []
    if not request.current_zone and confidence < 0.6:
        questions.append(
            ClarificationQuestion(
                id="current_zone",
                question="Bạn đang ở khu/sảnh nào trong Vinpearl?",
                options=["Cổng chính", "Sảnh resort", "Harbour", "Food Court"],
            )
        )
    if "voucher" in request.user_text.lower() and not request.voucher_type:
        questions.append(
            ClarificationQuestion(
                id="voucher_type",
                question="Voucher của bạn là buffet, meal credit hay discount?",
                options=["buffet", "meal_credit", "combo", "discount"],
            )
        )
    return questions[:2]


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
            learning_signal="Parser thiếu context quan trọng như vị trí hoặc voucher_type.",
        )
    if status == "no_match":
        return ErrorRoute(
            type="no_match",
            user_message="Chưa tìm thấy lựa chọn thỏa các điều kiện cứng hiện tại.",
            next_action="relax_constraint",
            recover_options=fallback_suggestions,
            learning_signal="Ranking không có candidate sau hard filters.",
        )
    if has_risky_recommendation:
        return ErrorRoute(
            type="risky_recommendation",
            user_message="Có gợi ý dùng được nhưng còn trade-off cần người dùng kiểm tra.",
            next_action="human_review",
            recover_options=[
                "Kiểm tra lại voucher tại quầy",
                "Xác nhận nhóm chấp nhận khoảng cách đi bộ",
                "Kiểm tra dietary/menu trước khi đi",
            ],
            learning_signal="Top recommendation có missing_info hoặc trade_offs đáng chú ý.",
        )
    return None


@app.post("/recommend", response_model=RecommendationResponse)
def recommend(request: RecommendationRequest) -> RecommendationResponse:
    """Parse a group request, rank restaurants, and return cards or fallback guidance."""
    restaurants = _restaurants_or_500()
    mode = "llm" if is_llm_available() else "regex"
    api_logger.info("Recommend request | mode=%s | text=%s", mode, request.user_text[:80])

    parsed_constraints = parse_user_text(request)

    if parsed_constraints == "off_topic":
        api_logger.info("Off-topic request rejected")
        return RecommendationResponse(
            status="error",
            parsed_constraints=ParsedConstraints(confidence=0.0),
            recommendations=[],
            fallback_suggestions=[],
            error_route=ErrorRoute(
                type="missing_data",
                user_message="Xin lỗi, mình chỉ hỗ trợ tìm quán ăn trong resort thôi nhé! Hãy cho mình biết nhu cầu ăn uống của bạn.",
                next_action="ask_clarification",
                recover_options=[
                    "Cho biết số người và loại đồ ăn muốn ăn",
                    "Nêu vị trí hiện tại trong resort",
                    "Cho biết loại voucher nếu có",
                ],
                learning_signal="User input not related to dining.",
            ),
            human_role=HumanRole(),
            debug={"mode": mode, "parser": "off_topic", "restaurant_count": len(restaurants)},
        )

    if request.correction:
        from src.fallback_handler import generate_correction_adjustments

        rejected_ids, score_adjustments = generate_correction_adjustments(
            request.correction, parsed_constraints
        )
        recommendations, fallback_suggestions = rank_restaurants(
            restaurants, parsed_constraints, rejected_ids, score_adjustments
        )
    else:
        recommendations, fallback_suggestions = rank_restaurants(
            restaurants, parsed_constraints
        )

    ai_explanations = None
    if recommendations:
        ai_explanations = generate_explanations(parsed_constraints, recommendations)

    clarification_questions = build_clarification_questions(request, parsed_constraints)

    has_meaningful_constraints = bool(
        parsed_constraints.preferred_cuisines
        or parsed_constraints.dietary_needs
        or parsed_constraints.budget_per_person
        or parsed_constraints.voucher_required
        or parsed_constraints.party_size
    )

    if not recommendations:
        status = "no_match"
    elif not has_meaningful_constraints and clarification_questions:
        status = "needs_clarification"
        recommendations = []
        ai_explanations = None
    else:
        status = "success"

    has_risky_recommendation = any(
        card.missing_info
        or any(
            keyword in trade_off.lower()
            for keyword in ["xa", "voucher", "dietary", "khong dung", "không dùng"]
            for trade_off in card.trade_offs
        )
        for card in recommendations
    )

    api_logger.info(
        "Recommend result | status=%s | count=%d | mode=%s",
        status, len(recommendations), mode,
    )

    return RecommendationResponse(
        status=status,
        parsed_constraints=parsed_constraints,
        clarification_questions=clarification_questions,
        recommendations=recommendations,
        fallback_suggestions=fallback_suggestions,
        ai_explanations=ai_explanations,
        error_route=_error_route(
            status, fallback_suggestions, has_risky_recommendation
        ),
        human_role=HumanRole(),
        debug={
            "mode": mode,
            "parser": "llm_parser" if mode == "llm" else "regex_parser",
            "ranker": "rank_restaurants",
            "restaurant_count": len(restaurants),
        },
    )
