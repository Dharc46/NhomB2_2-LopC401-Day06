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
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
 
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #1e293b;
        background-color: #fafbfc;
    }
 
    .block-container {
        max-width: 1220px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }
 
    .hero {
        background: linear-gradient(135deg, #ff4b2b 0%, #ff416c 50%, #ff8e53 100%);
        padding: 2.2rem 2rem;
        border-radius: 20px;
        color: white;
        box-shadow: 0 10px 30px rgba(255, 75, 43, 0.15);
        margin-bottom: 2rem;
    }
 
    .brand-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
    }
 
    .brand-title {
        font-size: 2.5rem;
        line-height: 1.1;
        font-weight: 800;
        color: white;
        letter-spacing: -0.5px;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
 
    .brand-subtitle {
        margin-top: 0.8rem;
        max-width: 800px;
        color: rgba(255, 255, 255, 0.9);
        font-size: 1.05rem;
        line-height: 1.6;
        font-weight: 500;
    }
 
    .system-pill {
        display: inline-flex;
        align-items: center;
        border: 1px solid rgba(255, 255, 255, 0.4);
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(10px);
        color: white;
        border-radius: 999px;
        padding: 0.4rem 0.9rem;
        font-size: 0.85rem;
        font-weight: 700;
        white-space: nowrap;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
    }
 
    .metric-strip {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.8rem;
        margin: 1.2rem 0 2rem 0;
    }
 
    .metric {
        border: 1px solid #f1f5f9;
        border-radius: 16px;
        background: #ffffff;
        padding: 1rem 1.2rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.02);
        transition: transform 0.2s ease;
    }
    
    .metric:hover {
        transform: translateY(-2px);
    }
 
    .metric-label {
        color: #64748b;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
 
    .metric-value {
        color: #0f172a;
        font-weight: 800;
        font-size: 1.25rem;
        margin-top: 0.35rem;
    }
 
    .recommend-card {
        border: 1px solid rgba(255, 142, 83, 0.15);
        border-radius: 20px;
        background: #ffffff;
        padding: 1.4rem;
        min-height: 300px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.03);
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
 
    .recommend-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 15px 35px rgba(255, 75, 43, 0.12);
        border-color: rgba(255, 75, 43, 0.3);
    }
 
    .card-rank {
        color: #ea580c;
        background: #fff7ed;
        border: 1px solid #ffedd5;
        border-radius: 999px;
        padding: 0.25rem 0.65rem;
        font-size: 0.75rem;
        font-weight: 800;
        display: inline-block;
    }
 
    .card-title {
        color: #0f172a;
        font-size: 1.2rem;
        font-weight: 800;
        margin: 0.8rem 0 0.35rem 0;
        line-height: 1.3;
    }
 
    .card-location {
        color: #475569;
        font-size: 0.88rem;
        line-height: 1.5;
        min-height: 2.5rem;
    }
 
    .score-row {
        display: flex;
        gap: 0.4rem;
        flex-wrap: wrap;
        margin: 0.85rem 0;
    }
 
    .badge {
        border-radius: 999px;
        padding: 0.3rem 0.7rem;
        font-size: 0.78rem;
        font-weight: 700;
        display: inline-block;
    }
 
    .badge-score { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }
    .badge-mid { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .badge-warn { background: #fff7ed; color: #c2410c; border: 1px solid #ffedd5; }
    .badge-risk { background: #fef2f2; color: #b91c1c; border: 1px solid #fee2e2; }
 
    .detail-line {
        color: #334155;
        font-size: 0.88rem;
        margin: 0.45rem 0;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }
 
    .section-kicker {
        font-size: 0.75rem;
        text-transform: uppercase;
        font-weight: 800;
        color: #475569;
        margin-top: 0.9rem;
        margin-bottom: 0.35rem;
        letter-spacing: 0.5px;
    }
 
    .tag-list {
        display: flex;
        gap: 0.35rem;
        flex-wrap: wrap;
        margin: 0.3rem 0 0.6rem 0;
    }
 
    .tag {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        color: #475569;
        border-radius: 999px;
        padding: 0.2rem 0.55rem;
        font-size: 0.75rem;
        font-weight: 600;
    }
 
    .note-box {
        border-left: 4px solid #10b981;
        background: #f0fdf4;
        color: #065f46;
        padding: 0.7rem 0.8rem;
        border-radius: 0 12px 12px 0;
        font-size: 0.85rem;
        line-height: 1.5;
        margin-top: 0.6rem;
        font-weight: 500;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.04);
    }
 
    .trade-box {
        border-left: 4px solid #f97316;
        background: #fff7ed;
        color: #9a3412;
        padding: 0.7rem 0.8rem;
        border-radius: 0 12px 12px 0;
        font-size: 0.85rem;
        line-height: 1.5;
        margin-top: 0.6rem;
        font-weight: 500;
        box-shadow: 0 2px 8px rgba(249, 115, 22, 0.04);
    }
 
    div[data-testid="stChatMessage"] {
        border: 1px solid #f1f5f9;
        border-radius: 16px;
        background: #ffffff;
        padding: 1rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.015);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


ZONE_OPTIONS = {
    "Cổng chính - VinWonders Nha Trang": "sanh chinh",
    "Sảnh Resort - Hòn Tre": "sanh resort",
    "Bến cảng - Nha Trang": "harbour",
    "Khu ẩm thực - VinWonders Nha Trang": "food court",
    "Công viên nước - Phú Quốc": "water park",
    "Grand World - Phú Quốc": "grand world",
    "Đảo dân gian - Nam Hội An": "folk island",
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
                "content": "Hãy cho tôi biết nhu cầu ăn uống của nhóm bạn. Tôi sẽ đặt câu hỏi làm rõ khi cần, sau đó xếp hạng các lựa chọn tốt nhất.",
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
            "user_message": "Không thể kết nối đến Backend. Hãy khởi động FastAPI rồi thử lại.",
            "recover_options": ["Chạy lệnh: py -m uvicorn src.api:app --reload"],
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
        return "Không rõ"
    return f"{value:,.0f} VND".replace(",", ".")


def add_assistant_message(response: dict, fallback_content: str = "") -> None:
    """Append API response as an assistant chat message."""
    status = response.get("status")
    recs = response.get("recommendations") or response.get("top_results") or []
    questions = response.get("clarification_questions") or response.get("questions") or []

    if status == "success" or response.get("type") == "recommendation":
        content = f"Tôi đã tìm thấy {len(recs)} lựa chọn được xếp hạng phù hợp nhất cho nhóm của bạn."
    elif status == "needs_clarification" or response.get("type") == "clarification":
        content = "Tôi cần thêm một số thông tin trước khi đưa ra xếp hạng chính xác nhất."
    elif status == "no_match":
        content = "Chưa tìm thấy quán ăn nào đáp ứng trọn vẹn yêu cầu. Dưới đây là các phương án gợi ý thay thế."
    else:
        route = response.get("error_route") or {}
        content = route.get("user_message") or fallback_content or "Đã xảy ra lỗi, vui lòng thử lại."

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
    status_text = "🟢 Hệ thống sẵn sàng" if health else "🔴 Hệ thống ngoại tuyến"
    dataset_text = f"🍽️ {health.get('restaurant_count')} nhà hàng resort" if health else "❌ Chưa tải dữ liệu"
    st.markdown(
        f"""
        <div class="hero">
            <div class="brand-row">
                <div>
                    <h1 class="brand-title">VinDine Concierge 💬</h1>
                    <div class="brand-subtitle">
                        Trợ lý AI hỗ trợ chọn quán ăn thông minh tại resort Vinpearl. Phân tích nhu cầu, gợi ý Top 3 quán ăn tối ưu, 
                        đánh giá điểm mạnh/điểm yếu và giúp bạn lựa chọn điểm đến lý tưởng nhất cho nhóm của mình.
                    </div>
                </div>
                <span class="system-pill">{status_text}</span>
            </div>
        </div>
        <div class="metric-strip">
            <div class="metric"><div class="metric-label">Cơ sở dữ liệu</div><div class="metric-value">{dataset_text}</div></div>
            <div class="metric"><div class="metric-label">Phương thức hỗ trợ</div><div class="metric-value">🎯 Tối ưu hóa lựa chọn</div></div>
            <div class="metric"><div class="metric-label">Xử lý linh hoạt</div><div class="metric-value">🔄 Hỏi lại & Tự động xếp hạng</div></div>
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

    selected_zone_label = st.sidebar.selectbox("Vị trí hiện tại", list(ZONE_OPTIONS.keys()))
    st.session_state["user_zone"] = ZONE_OPTIONS[selected_zone_label]

    st.sidebar.markdown("### Câu lệnh mẫu")
    for idx, prompt in enumerate(EXAMPLE_PROMPTS, start=1):
        if st.sidebar.button(f"Dùng mẫu {idx}", use_container_width=True):
            st.session_state["draft_prompt"] = prompt

    st.sidebar.markdown("### Vai trò người dùng (Human-in-the-loop)")
    st.sidebar.info(
        "👉 **Decider (Người quyết định)**: Chọn quán ăn cuối cùng.\n\n"
        "👉 **Reviewer (Người kiểm duyệt)**: Xác nhận voucher, thực đơn và khoảng cách đi bộ thực tế.\n\n"
        "👉 **Rescuer (Người giải cứu)**: Báo sai để yêu cầu xếp hạng lại.\n\n"
        "👉 **Trainer (Người hướng dẫn)**: Ghi nhận phản hồi để huấn luyện lại AI."
    )

    if st.sidebar.button("Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Lịch sử đã được xoá. Hãy cho tôi biết nhu cầu ăn uống của nhóm bạn.",
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
    if confidence == "medium":
        confidence_vi = "Trung bình"
    elif confidence == "low":
        confidence_vi = "Thấp"
    else:
        confidence_vi = "Cao"

    voucher_label = "Khớp Voucher" if card.get("voucher_match") else "Kiểm tra Voucher"
    st.markdown(
        f"""
        <div class="recommend-card">
            <span class="card-rank">Hạng {card.get('rank', idx + 1)}</span>
            <div class="card-title">{card.get('name', 'Quán ăn chưa rõ tên')}</div>
            <div class="card-location">{card.get('location_hint', '')}</div>
            <div class="score-row">
                <span class="badge badge-score">{card.get('fit_score', 0)} khớp</span>
                <span class="badge badge-mid">{confidence_vi}</span>
                <span class="badge badge-warn">{voucher_label}</span>
            </div>
            <div class="detail-line"><b>Khu vực:</b> {card.get('zone')} / {card.get('brand_area')}</div>
            <div class="detail-line"><b>Đi bộ:</b> {card.get('distance_text')}</div>
            <div class="detail-line"><b>Giá trung bình:</b> {format_price(card.get('avg_price_vnd'))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Xóa hiển thị Matched constraints theo yêu cầu
    render_tags("Tiêu chí chưa đáp ứng", card.get("missed_preferences", []), "tag")

    # Lọc bỏ các thông tin liên quan đến 'Khoảng cách đi bộ' hoặc 'location_context' trong reasons
    filtered_reasons = [
        r for r in card.get("reasons", [])
        if "Khoảng cách đi bộ" not in r and "location_context" not in r
    ]
    for reason in filtered_reasons[:3]:
        st.markdown(f'<div class="note-box">{reason}</div>', unsafe_allow_html=True)
        
    for tradeoff in card.get("trade_offs", [])[:3]:
        st.markdown(f'<div class="trade-box">{tradeoff}</div>', unsafe_allow_html=True)

    # Xóa phần giải thích "Why this was ranked here" theo yêu cầu

    if card.get("least_satisfied_person"):
        st.caption(f"Ít hài lòng nhất: {card['least_satisfied_person']}")

    action_cols = st.columns([1, 1])
    with action_cols[0]:
        if card.get("google_maps_url"):
            st.link_button("Tìm trên Bản đồ", card["google_maps_url"], use_container_width=True)
    with action_cols[1]:
        if st.button("Chọn 👍", key=f"choose_{msg_idx}_{idx}_{card.get('restaurant_id')}", use_container_width=True, type="primary"):
            st.session_state.messages.append({"role": "user", "content": f"Tôi muốn chọn {card.get('name')} 👍"})
            st.session_state.messages.append({"role": "assistant", "content": f"Tuyệt vời! Bạn đã chọn **{card.get('name')}**. Chúc bạn và nhóm có một bữa ăn ngon miệng tại đây!"})
            st.rerun()

    reason_label = st.selectbox(
        "Lý do không chọn",
        list(REJECT_REASONS.keys()),
        key=f"reject_reason_{msg_idx}_{idx}_{card.get('restaurant_id')}",
    )
    if st.button("Từ chối và xếp hạng lại 🔄", key=f"reject_{msg_idx}_{idx}_{card.get('restaurant_id')}", use_container_width=True):
        with st.spinner("Đang cập nhật xếp hạng mới..."):
            reranked = call_feedback_api(
                st.session_state.original_query,
                card.get("restaurant_id"),
                REJECT_REASONS[reason_label],
            )
        if reranked:
            add_assistant_message(reranked, "Đã ghi nhận phản hồi và cập nhật xếp hạng mới.")
            st.rerun()
        st.warning("Không thể kết nối đến API phản hồi. Hãy kiểm tra trạng thái backend.")


def render_message(msg: dict, msg_idx: int) -> None:
    """Render one chat message and any attached structured response."""
    with st.chat_message(msg.get("role", "assistant")):
        st.write(msg.get("content", ""))

        if msg.get("questions"):
            st.info("Cần làm rõ thông tin")
            for question in msg["questions"]:
                st.write(f"- {question.get('question')}")

        if msg.get("uncertainty"):
            issues = msg["uncertainty"].get("issues", [])
            if issues:
                with st.expander("Tín hiệu chưa chắc chắn"):
                    render_tags("Vấn đề", issues)

        recommendations = msg.get("recommendations", [])
        if recommendations:
            st.markdown("#### Top 3 gợi ý phù hợp nhất")
            cols = st.columns(min(3, len(recommendations)))
            for idx, card in enumerate(recommendations[:3]):
                with cols[idx]:
                    render_card(card, msg_idx, idx)

        if msg.get("fallbacks"):
            st.markdown("#### Phương án gợi ý thay thế")
            for f_idx, fallback in enumerate(msg["fallbacks"]):
                if st.button(fallback, key=f"fallback_{msg_idx}_{f_idx}", use_container_width=True):
                    st.session_state.pending_prompt = fallback
                    st.rerun()

        if msg.get("parsed_constraints"):
            with st.expander("Tiêu chí đã trích xuất"):
                st.json(msg["parsed_constraints"])


def render_clarification_form() -> None:
    """Render follow-up questions when the API asks for clarification."""
    questions = st.session_state.active_clarification
    if not questions:
        return

    st.markdown("#### Làm rõ thông tin trước khi xếp hạng")
    with st.form("clarify_form"):
        answers: dict[str, str] = {}
        for question in questions:
            options = question.get("options") or ["Không chắc chắn"]
            answers[question["id"]] = st.selectbox(question.get("question", question["id"]), options=options)
        submitted = st.form_submit_button("Tiếp tục")

    if submitted:
        zone = answers.get("current_zone") or st.session_state.get("user_zone")
        voucher_type = answers.get("voucher_type")
        with st.spinner("Đang tìm lựa chọn tốt nhất..."):
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
prompt = st.chat_input("Nhập nhu cầu ăn uống của bạn (số lượng người, vị trí, ngân sách, voucher, món ăn...)...")
pending = st.session_state.pop("pending_prompt", None)

if pending:
    prompt = pending

if draft:
    st.info("Đã tải câu mẫu. Bạn hãy gửi hoặc chỉnh sửa lại ở ô chat bên dưới.")
    st.code(draft)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Đang phân tích nhu cầu và tìm quán..."):
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
