"""Streamlit UI for the VinDine Concierge demo."""

from __future__ import annotations

import requests
import streamlit as st


st.set_page_config(
    page_title="VinDine Concierge",
    page_icon="VD",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #1f2933;
    }

    .block-container {
        max-width: 1220px;
        padding-top: 1.2rem;
        padding-bottom: 2.5rem;
    }

    .hero {
        border-bottom: 1px solid #e3e8ef;
        padding: 0.4rem 0 1rem 0;
        margin-bottom: 1rem;
    }

    .brand-row {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
    }

    .brand-title {
        font-size: 2rem;
        line-height: 1.1;
        font-weight: 800;
        color: #172033;
        letter-spacing: 0;
        margin: 0;
    }

    .brand-subtitle {
        margin-top: 0.45rem;
        max-width: 760px;
        color: #52606d;
        font-size: 0.98rem;
        line-height: 1.55;
    }

    .system-pill {
        display: inline-flex;
        align-items: center;
        border: 1px solid #d7dee8;
        background: #f7f9fc;
        color: #344054;
        border-radius: 999px;
        padding: 0.35rem 0.7rem;
        font-size: 0.82rem;
        font-weight: 600;
        white-space: nowrap;
    }

    .metric-strip {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.6rem;
        margin: 0.8rem 0 1.2rem 0;
    }

    .metric {
        border: 1px solid #e3e8ef;
        border-radius: 8px;
        background: #ffffff;
        padding: 0.75rem 0.85rem;
    }

    .metric-label {
        color: #697586;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }

    .metric-value {
        color: #172033;
        font-weight: 800;
        font-size: 1.05rem;
        margin-top: 0.25rem;
    }

    .recommend-card {
        border: 1px solid #dfe6ee;
        border-radius: 8px;
        background: #ffffff;
        padding: 1rem;
        min-height: 300px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
    }

    .card-rank {
        color: #8a4b12;
        background: #fff4e5;
        border: 1px solid #f4c37d;
        border-radius: 999px;
        padding: 0.22rem 0.5rem;
        font-size: 0.72rem;
        font-weight: 700;
        display: inline-block;
    }

    .card-title {
        color: #172033;
        font-size: 1.05rem;
        font-weight: 800;
        margin: 0.6rem 0 0.25rem 0;
        line-height: 1.25;
    }

    .card-location {
        color: #52606d;
        font-size: 0.82rem;
        line-height: 1.45;
        min-height: 2.35rem;
    }

    .score-row {
        display: flex;
        gap: 0.35rem;
        flex-wrap: wrap;
        margin: 0.75rem 0;
    }

    .badge {
        border-radius: 999px;
        padding: 0.25rem 0.55rem;
        font-size: 0.74rem;
        font-weight: 700;
        display: inline-block;
    }

    .badge-score { background: #e8f5e9; color: #1b6b3a; border: 1px solid #b9dfc1; }
    .badge-mid { background: #eaf3ff; color: #235c9f; border: 1px solid #bfd8f4; }
    .badge-warn { background: #fff4e5; color: #8a4b12; border: 1px solid #f4c37d; }
    .badge-risk { background: #fff1f0; color: #9f2a2a; border: 1px solid #f3c0bc; }

    .detail-line {
        color: #344054;
        font-size: 0.82rem;
        margin: 0.35rem 0;
    }

    .section-kicker {
        font-size: 0.72rem;
        text-transform: uppercase;
        font-weight: 800;
        color: #697586;
        margin-top: 0.8rem;
        margin-bottom: 0.25rem;
    }

    .tag-list {
        display: flex;
        gap: 0.3rem;
        flex-wrap: wrap;
        margin: 0.25rem 0 0.5rem 0;
    }

    .tag {
        background: #f4f6f8;
        border: 1px solid #dfe6ee;
        color: #344054;
        border-radius: 999px;
        padding: 0.18rem 0.45rem;
        font-size: 0.7rem;
        font-weight: 600;
    }

    .note-box {
        border-left: 3px solid #2f80ed;
        background: #f2f7ff;
        color: #344054;
        padding: 0.55rem 0.65rem;
        border-radius: 0 6px 6px 0;
        font-size: 0.8rem;
        line-height: 1.45;
        margin-top: 0.5rem;
    }

    .trade-box {
        border-left: 3px solid #c2410c;
        background: #fff7ed;
        color: #344054;
        padding: 0.55rem 0.65rem;
        border-radius: 0 6px 6px 0;
        font-size: 0.8rem;
        line-height: 1.45;
        margin-top: 0.5rem;
    }

    div[data-testid="stChatMessage"] {
        border: 1px solid #edf1f5;
        border-radius: 8px;
        background: #ffffff;
        padding: 0.7rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


ZONE_OPTIONS = {
    "Not selected": None,
    "Main gate - VinWonders Nha Trang": "sanh chinh",
    "Resort lobby - Hon Tre": "sanh resort",
    "Harbour - Nha Trang": "harbour",
    "Food Court - VinWonders Nha Trang": "food court",
    "Water Park - Phu Quoc": "water park",
    "Grand World - Phu Quoc": "grand world",
    "Folk Island - Nam Hoi An": "folk island",
}

EXAMPLE_PROMPTS = [
    "Nha minh 6 nguoi o sanh Vinpearl, co ong ba va 2 tre em, muon mon Viet hoac pizza, co voucher buffet, di bo duoi 8 phut.",
    "Co voucher Vin, tim quan gan gan cho gia dinh.",
    "7 nguoi, co ong ba, muon yen tinh, co tre em, dung voucher buffet, duoi 70k/nguoi.",
    "5 nguoi, 1 nguoi an chay, 1 nguoi di ung hai san, muon gan cong vien nuoc.",
]

REJECT_REASONS = {
    "Too noisy": "too_noisy",
    "Too far": "too_far",
    "Too expensive": "too_expensive",
    "No kids menu": "no_kids_menu",
    "Voucher risk": "no_voucher",
    "Dietary risk": "dietary_risk",
    "Other": "other",
}


def init_state() -> None:
    """Initialize Streamlit session state."""
    st.session_state.setdefault("api_url", "http://127.0.0.1:8000")
    st.session_state.setdefault("original_query", "")
    st.session_state.setdefault("active_clarification", None)
    st.session_state.setdefault(
        "messages",
        [
            {
                "role": "assistant",
                "content": "Tell me your group's dining needs. I will ask clarifying questions when needed, then rank the best options.",
            }
        ],
    )


def backend_health(api_url: str) -> dict | None:
    """Return backend health payload if available."""
    try:
        response = requests.get(f"{api_url}/health", timeout=2)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        return None
    return None


def call_recommend_api(
    user_text: str,
    current_zone: str | None = None,
    voucher_type: str | None = None,
    correction: str | None = None,
) -> dict:
    """Call FastAPI recommendation endpoint."""
    payload = {
        "text": user_text,
        "current_zone": current_zone,
        "voucher_type": voucher_type,
        "party_size": None,
        "correction": correction,
    }
    try:
        response = requests.post(
            f"{st.session_state.api_url}/recommend",
            json=payload,
            timeout=12,
        )
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        pass
    return {
        "status": "error",
        "type": "error",
        "recommendations": [],
        "fallback_suggestions": [],
        "error_route": {
            "user_message": "Backend is offline. Start FastAPI, then try again.",
            "recover_options": ["Run: py -m uvicorn src.api:app --reload"],
        },
    }


def call_feedback_api(original_text: str, restaurant_id: str, reason: str) -> dict | None:
    """Call feedback endpoint and return reranked response."""
    payload = {
        "original_text": original_text,
        "rejected_restaurant_id": restaurant_id,
        "reason": reason,
    }
    try:
        response = requests.post(f"{st.session_state.api_url}/feedback", json=payload, timeout=12)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        return None
    return None


def format_price(value: int | None) -> str:
    """Format VND price."""
    if value is None:
        return "Unknown"
    return f"{value:,.0f} VND".replace(",", ".")


def add_assistant_message(response: dict, fallback_content: str = "") -> None:
    """Append API response as an assistant chat message."""
    status = response.get("status")
    recs = response.get("recommendations") or response.get("top_results") or []
    questions = response.get("clarification_questions") or response.get("questions") or []

    if status == "success" or response.get("type") == "recommendation":
        content = f"I found {len(recs)} ranked options for your group."
    elif status == "needs_clarification" or response.get("type") == "clarification":
        content = "I need a bit more information before ranking confidently."
    elif status == "no_match":
        content = "No exact match yet. Here are recovery options."
    else:
        route = response.get("error_route") or {}
        content = route.get("user_message") or fallback_content or "Something went wrong."

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": content,
            "recommendations": recs,
            "fallbacks": response.get("fallback_suggestions") or response.get("fallback_options") or [],
            "questions": questions,
            "parsed_constraints": response.get("parsed_constraints"),
            "uncertainty": response.get("uncertainty"),
            "error_route": response.get("error_route"),
            "ai_explanations": response.get("ai_explanations"),
        }
    )
    st.session_state.active_clarification = questions or None


def render_header(health: dict | None) -> None:
    """Render page header."""
    status_text = "Backend online" if health else "Backend offline"
    dataset_text = f"{health.get('restaurant_count')} venues" if health else "No live dataset"
    st.markdown(
        f"""
        <div class="hero">
            <div class="brand-row">
                <div>
                    <h1 class="brand-title">VinDine Concierge</h1>
                    <div class="brand-subtitle">
                        AI-assisted dining decision support for resort groups. It parses needs, asks when uncertain,
                        ranks Top 3 options, explains trade-offs, and lets the human decide.
                    </div>
                </div>
                <span class="system-pill">{status_text}</span>
            </div>
        </div>
        <div class="metric-strip">
            <div class="metric"><div class="metric-label">Dataset</div><div class="metric-value">{dataset_text}</div></div>
            <div class="metric"><div class="metric-label">Decision mode</div><div class="metric-value">Augmentation</div></div>
            <div class="metric"><div class="metric-label">Recovery</div><div class="metric-value">Clarify / Re-rank</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(health: dict | None) -> None:
    """Render sidebar controls."""
    st.sidebar.title("Demo controls")
    api_url = st.sidebar.text_input("Backend URL", value=st.session_state.api_url)
    if api_url:
        st.session_state.api_url = api_url

    if health:
        st.sidebar.success(f"Connected: {health.get('restaurant_count')} venues")
    else:
        st.sidebar.warning("Backend offline")

    selected_zone_label = st.sidebar.selectbox("Current zone", list(ZONE_OPTIONS.keys()))
    st.session_state["user_zone"] = ZONE_OPTIONS[selected_zone_label]

    st.sidebar.markdown("### Example prompts")
    for idx, prompt in enumerate(EXAMPLE_PROMPTS, start=1):
        if st.sidebar.button(f"Use example {idx}", use_container_width=True):
            st.session_state["draft_prompt"] = prompt

    st.sidebar.markdown("### Human role")
    st.sidebar.info(
        "Decider: choose final venue.\n\n"
        "Reviewer: verify voucher, menu, and distance.\n\n"
        "Rescuer: reject a bad suggestion.\n\n"
        "Trainer: feedback becomes correction signal."
    )

    if st.sidebar.button("Clear chat", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Chat cleared. Tell me your group's dining needs.",
            }
        ]
        st.session_state.original_query = ""
        st.session_state.active_clarification = None
        st.rerun()


def render_tags(title: str, values: list[str], css_class: str = "tag") -> None:
    """Render a compact tag list."""
    if not values:
        return
    tags = "".join(f'<span class="{css_class}">{value}</span>' for value in values[:8])
    st.markdown(f'<div class="section-kicker">{title}</div><div class="tag-list">{tags}</div>', unsafe_allow_html=True)


def render_card(card: dict, msg_idx: int, idx: int) -> None:
    """Render one recommendation card with actions."""
    confidence = card.get("confidence_label", "medium")
    voucher_label = "Voucher match" if card.get("voucher_match") else "Voucher check"
    st.markdown(
        f"""
        <div class="recommend-card">
            <span class="card-rank">Rank {card.get('rank', idx + 1)}</span>
            <div class="card-title">{card.get('name', 'Unknown venue')}</div>
            <div class="card-location">{card.get('location_hint', '')}</div>
            <div class="score-row">
                <span class="badge badge-score">{card.get('fit_score', 0)} fit</span>
                <span class="badge badge-mid">{confidence}</span>
                <span class="badge badge-warn">{voucher_label}</span>
            </div>
            <div class="detail-line"><b>Zone:</b> {card.get('zone')} / {card.get('brand_area')}</div>
            <div class="detail-line"><b>Walk:</b> {card.get('distance_text')}</div>
            <div class="detail-line"><b>Average price:</b> {format_price(card.get('avg_price_vnd'))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_tags("Matched constraints", card.get("matched_constraints", []))
    render_tags("Missed preferences", card.get("missed_preferences", []), "tag")

    for reason in card.get("reasons", [])[:3]:
        st.markdown(f'<div class="note-box">{reason}</div>', unsafe_allow_html=True)
    for tradeoff in card.get("trade_offs", [])[:3]:
        st.markdown(f'<div class="trade-box">{tradeoff}</div>', unsafe_allow_html=True)

    if card.get("explanation"):
        with st.expander("Why this was ranked here"):
            st.write(card["explanation"])

    if card.get("least_satisfied_person"):
        st.caption(f"Least satisfied: {card['least_satisfied_person']}")

    action_cols = st.columns([1, 1])
    with action_cols[0]:
        if card.get("google_maps_url"):
            st.link_button("Maps search", card["google_maps_url"], use_container_width=True)
    with action_cols[1]:
        if st.button("Choose", key=f"choose_{msg_idx}_{idx}_{card.get('restaurant_id')}", use_container_width=True):
            st.success(f"Selected {card.get('name')}")

    reason_label = st.selectbox(
        "Reject reason",
        list(REJECT_REASONS.keys()),
        key=f"reject_reason_{msg_idx}_{idx}_{card.get('restaurant_id')}",
    )
    if st.button("Reject and re-rank", key=f"reject_{msg_idx}_{idx}_{card.get('restaurant_id')}", use_container_width=True):
        reranked = call_feedback_api(
            st.session_state.original_query,
            card.get("restaurant_id"),
            REJECT_REASONS[reason_label],
        )
        if reranked:
            add_assistant_message(reranked, "Feedback saved and list reranked.")
            st.rerun()
        st.warning("Could not call /feedback. Check backend status.")


def render_message(msg: dict, msg_idx: int) -> None:
    """Render one chat message and any attached structured response."""
    with st.chat_message(msg.get("role", "assistant")):
        st.write(msg.get("content", ""))

        if msg.get("questions"):
            st.info("Clarification needed")
            for question in msg["questions"]:
                st.write(f"- {question.get('question')}")

        if msg.get("uncertainty"):
            issues = msg["uncertainty"].get("issues", [])
            if issues:
                with st.expander("Uncertainty signals"):
                    render_tags("Issues", issues)

        recommendations = msg.get("recommendations", [])
        if recommendations:
            st.markdown("#### Top 3 recommendations")
            cols = st.columns(min(3, len(recommendations)))
            for idx, card in enumerate(recommendations[:3]):
                with cols[idx]:
                    render_card(card, msg_idx, idx)

        if msg.get("fallbacks"):
            st.markdown("#### Recovery options")
            for fallback in msg["fallbacks"]:
                st.info(fallback)

        if msg.get("parsed_constraints"):
            with st.expander("Parsed constraints"):
                st.json(msg["parsed_constraints"])


def render_clarification_form() -> None:
    """Render follow-up questions when the API asks for clarification."""
    questions = st.session_state.active_clarification
    if not questions:
        return

    st.markdown("#### Clarify before ranking")
    with st.form("clarify_form"):
        answers: dict[str, str] = {}
        for question in questions:
            options = question.get("options") or ["Not sure"]
            answers[question["id"]] = st.selectbox(question.get("question", question["id"]), options=options)
        submitted = st.form_submit_button("Continue")

    if submitted:
        zone = answers.get("current_zone") or st.session_state.get("user_zone")
        voucher_type = answers.get("voucher_type")
        response = call_recommend_api(
            st.session_state.original_query,
            current_zone=zone,
            voucher_type=voucher_type,
        )
        add_assistant_message(response)
        st.session_state.active_clarification = None
        st.rerun()


init_state()
health_payload = backend_health(st.session_state.api_url)
render_sidebar(health_payload)
render_header(health_payload)

for message_index, message in enumerate(st.session_state.messages):
    render_message(message, message_index)

render_clarification_form()

draft = st.session_state.pop("draft_prompt", "")
prompt = st.chat_input("Describe your group, location, budget, voucher, cuisine, and constraints...")
if draft:
    st.info("Example loaded. Submit it from the chat input or paste/edit it below.")
    st.code(draft)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    is_correction = bool(st.session_state.original_query and len(st.session_state.messages) > 2)

    if is_correction:
        response_payload = call_recommend_api(
            st.session_state.original_query,
            current_zone=st.session_state.get("user_zone"),
            correction=prompt,
        )
    else:
        st.session_state.original_query = prompt
        response_payload = call_recommend_api(
            prompt,
            current_zone=st.session_state.get("user_zone"),
        )

    add_assistant_message(response_payload)
    st.rerun()
