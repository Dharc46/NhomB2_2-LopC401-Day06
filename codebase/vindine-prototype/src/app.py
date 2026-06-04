import streamlit as st
import requests
import json

# Cấu hình trang với thiết kế hiện đại
st.set_page_config(
    page_title="VinDine Concierge - AI Resort Dining Assistant",
    page_icon="💬",
    layout="wide",
)

# Thêm CSS custom để giao diện chatbot trông bóng bẩy và cao cấp
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .main-title {
        background: linear-gradient(90deg, #FF6B6B 0%, #FF8E53 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        color: #666;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    /* Thẻ gợi ý quán ăn kiểu bong bóng chat */
    .chat-card {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-top: 10px;
        margin-bottom: 10px;
    }
    .fit-score {
        background: linear-gradient(135deg, #4299E1 0%, #3182CE 100%);
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-block;
    }
    .confidence-badge {
        background-color: #EDF2F7;
        color: #4A5568;
        padding: 3px 8px;
        border-radius: 12px;
        font-weight: 500;
        font-size: 0.8rem;
        display: inline-block;
        margin-left: 5px;
    }
    .reason-tag {
        color: #2F855A;
        background-color: #F0FFF4;
        border-left: 3px solid #38A169;
        padding: 4px 8px;
        margin: 4px 0;
        font-size: 0.85rem;
        border-radius: 0 4px 4px 0;
    }
    .tradeoff-tag {
        color: #C53030;
        background-color: #FFF5F5;
        border-left: 3px solid #E53E3E;
        padding: 4px 8px;
        margin: 4px 0;
        font-size: 0.85rem;
        border-radius: 0 4px 4px 0;
    }
    .info-tag {
        color: #3182CE;
        background-color: #EBF8FF;
        border-left: 3px solid #4299E1;
        padding: 4px 8px;
        margin: 4px 0;
        font-size: 0.85rem;
        border-radius: 0 4px 4px 0;
    }
    .constraint-badge {
        background-color: #E2E8F0;
        color: #4A5568;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        display: inline-block;
        margin: 2px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">VinDine Concierge 💬</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Hỏi đáp trực tiếp với trợ lý AI hỗ trợ chọn quán ăn thông minh</div>', unsafe_allow_html=True)

# ==========================================
# KHỞI TẠO STATE CHO CHATBOT
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Xin chào! Mình là VinDine Concierge. Bạn muốn ăn gì ở resort hôm nay? Hãy nhập số lượng người, loại voucher, hay vị trí hiện tại nhé!"}
    ]
if "api_url" not in st.session_state:
    st.session_state.api_url = "http://127.0.0.1:8000"
if "original_query" not in st.session_state:
    st.session_state.original_query = ""
if "active_clarification" not in st.session_state:
    st.session_state.active_clarification = None

# ==========================================
# SIDEBAR - DEMO CONTROL & ROLES
# ==========================================
st.sidebar.title("🔌 API Settings & Demo")
api_url_input = st.sidebar.text_input("FastAPI Backend URL:", value=st.session_state.api_url)
if api_url_input:
    st.session_state.api_url = api_url_input

# Kiểm tra Backend
is_online = False
try:
    health_resp = requests.get(f"{st.session_state.api_url}/health", timeout=2)
    if health_resp.status_code == 200:
        is_online = True
        st.sidebar.success(f"🟢 Connected to Backend ({health_resp.json().get('restaurant_count')} restaurants)")
except Exception:
    st.sidebar.warning("🟡 Offline (Dùng mock giả lập)")

st.sidebar.markdown("---")
st.sidebar.markdown("### 👥 Vai trò người dùng (Human-in-the-loop)")
st.sidebar.info(
    "👉 **Decider**: Quyết định chọn quán cuối cùng\n\n"
    "👉 **Reviewer**: Kiểm tra điều kiện/khoảng cách thực tế trước khi đi\n\n"
    "👉 **Rescuer**: Báo sai để yêu cầu re-rank\n\n"
    "👉 **Trainer**: Dữ liệu sửa đổi được ghi nhận để huấn luyện lại AI"
)

if st.sidebar.button("🧹 Clear Chat History", use_container_width=True):
    st.session_state.messages = [
        {"role": "assistant", "content": "Lịch sử đã được xoá. Hãy cho mình biết nhu cầu ăn uống của bạn hôm nay!"}
    ]
    st.session_state.original_query = ""
    st.session_state.active_clarification = None
    st.rerun()

# ==========================================
# CÁC HÀM XỬ LÝ TRUY VẤN
# ==========================================
def call_recommend_api(user_text: str, current_zone: str = None, voucher_type: str = None, correction: str = None):
    payload = {
        "user_text": user_text,
        "current_zone": current_zone,
        "voucher_type": voucher_type,
        "party_size": None,
        "correction": correction
    }
    try:
        resp = requests.post(f"{st.session_state.api_url}/recommend", json=payload, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    
    # Mock Offline Fallbacks
    if "không" in user_text.lower() or "no" in user_text.lower():
        return {
            "status": "no_match",
            "recommendations": [],
            "fallback_suggestions": [
                "Nới budget thêm 50.000-100.000 VND/người",
                "Mở rộng khoảng cách đi bộ thêm 5-10 phút",
                "Bỏ điều kiện voucher nếu không bắt buộc",
            ],
            "error_route": {
                "type": "no_match",
                "user_message": "Chưa tìm thấy lựa chọn thỏa các điều kiện cứng hiện tại.",
                "next_action": "relax_constraint",
                "recover_options": ["Nới rộng budget", "Tăng khoảng cách đi bộ"]
            }
        }
    elif "voucher" in user_text.lower() and not voucher_type:
        return {
            "status": "needs_clarification",
            "clarification_questions": [
                {
                    "id": "voucher_type",
                    "question": "Voucher của bạn là buffet, meal credit hay discount?",
                    "options": ["buffet", "meal_credit", "discount"]
                }
            ],
            "error_route": {
                "type": "low_confidence",
                "user_message": "Mình cần thêm thông tin trước khi chốt gợi ý đáng tin cậy.",
                "next_action": "ask_clarification",
                "recover_options": ["Cho biết loại voucher cụ thể"]
            }
        }
    else:
        # Giả lập thành công có cảnh báo nguy cơ (risky_recommendation)
        return {
            "status": "success",
            "parsed_constraints": {
                "party_size": 6,
                "has_kids": True,
                "has_elderly": True,
                "needs_stroller": True,
                "voucher_type": "buffet"
            },
            "recommendations": [
                {
                    "restaurant_id": "viet-delight",
                    "name": "Nhà Hàng Viet Delight (Mock)",
                    "fit_score": 92.5,
                    "zone": "Sảnh chính",
                    "brand_area": "Khu Resort",
                    "distance_text": "3 phút đi bộ",
                    "avg_price_vnd": 250000,
                    "reasons": ["Không gian yên tĩnh cho ông bà", "Hỗ trợ xe đẩy em bé"],
                    "trade_offs": ["Đi bộ khá xa", "Cần đặt bàn trước"],
                    "confidence_label": "medium",
                    "missing_info": ["Voucher validation"],
                    "assumptions": ["Giả định voucher buffet khả dụng tại điểm này"]
                }
            ],
            "error_route": {
                "type": "risky_recommendation",
                "user_message": "Có gợi ý dùng được nhưng còn trade-off cần người dùng kiểm tra.",
                "next_action": "human_review",
                "recover_options": [
                    "Kiểm tra lại voucher tại quầy trước khi đi",
                    "Xác nhận nhóm đồng ý khoảng cách đi bộ xa",
                    "Kiểm tra thực đơn chay trước khi đặt bàn"
                ]
            }
        }

# ==========================================
# RENDER HỘI THOẠI CHATBOT
# ==========================================
for msg_idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        
        # 0. Hiển thị AI group summary (nếu có)
        ai_expl = msg.get("ai_explanations")
        if ai_expl and ai_expl.get("group_summary"):
            st.info(f"💬 **AI Concierge:** {ai_expl['group_summary']}")

        # 1. Nếu có đính kèm thẻ gợi ý quán ăn
        if "recommendations" in msg and msg["recommendations"]:
            st.write("---")
            cols = st.columns(min(len(msg["recommendations"]), 3))
            for idx, card in enumerate(msg["recommendations"]):
                with cols[idx]:
                    st.markdown(
                        f"""
                        <div class="chat-card">
                            <h4 style="margin:0;">{card.get('name')}</h4>
                            <span class="fit-score">Khớp: {card.get('fit_score')}%</span>
                            <span class="confidence-badge">{card.get('confidence_label', 'medium')}</span>
                            <p style="margin:5px 0; font-size:0.85rem; color:#4A5568;">📍 {card.get('zone')} ({card.get('brand_area')})</p>
                            <p style="margin:0 0 8px 0; font-size:0.85rem; color:#4A5568;">🚶 {card.get('distance_text')} | 💰 {card.get('avg_price_vnd', 0):,}đ</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    
                    # Lý do chọn & trade-off ngay trong card
                    for r in card.get("reasons", []):
                        st.markdown(f"<div class='reason-tag'>✓ {r}</div>", unsafe_allow_html=True)
                    for t in card.get("trade_offs", []):
                        st.markdown(f"<div class='tradeoff-tag'>✗ {t}</div>", unsafe_allow_html=True)
                    for a in card.get("assumptions", []):
                        st.markdown(f"<div class='info-tag'>i {a}</div>", unsafe_allow_html=True)

                    # AI explanation cho quán này (nếu có)
                    ai_expl = msg.get("ai_explanations")
                    if ai_expl and ai_expl.get("explanations"):
                        for expl in ai_expl["explanations"]:
                            if expl.get("restaurant_id") == card.get("restaurant_id"):
                                st.markdown(f"<div class='info-tag'>💬 {expl.get('why_good', '')}</div>", unsafe_allow_html=True)
                                if expl.get("trade_off"):
                                    st.markdown(f"<div class='tradeoff-tag'>⚖️ {expl['trade_off']}</div>", unsafe_allow_html=True)
                                if expl.get("least_happy"):
                                    st.markdown(f"<div class='info-tag'>🤔 {expl['least_happy']}</div>", unsafe_allow_html=True)

                    st.write("")

                    # Các nút hành động tương tác ngay trong khung chat
                    btn_sel = st.button("Chọn 👍", key=f"sel_{msg_idx}_{idx}_{card.get('restaurant_id')}")
                    if btn_sel:
                        st.success(f"Bạn đã chọn quán **{card.get('name')}**!")
                        print(f"[CHAT-LOG] Chọn quán: {card.get('name')}")
        
        # 2. Hiển thị Error Route (low_confidence, no_match, risky_recommendation)
        if "error_route" in msg and msg["error_route"]:
            err = msg["error_route"]
            st.warning(f"⚠️ **{err.get('user_message')}**")
            
            # Nếu có danh sách checklists cần kiểm tra (recover_options)
            st.write("**📋 Danh sách việc cần lưu ý/xác nhận:**")
            for option in err.get("recover_options", []):
                st.checkbox(option, key=f"chk_{msg_idx}_{option[:15]}")
        
        # 3. Hiển thị gợi ý phương án thay thế (Fallback)
        if "fallbacks" in msg and msg["fallbacks"]:
            st.write("**💡 Các phương án gợi ý thay thế:**")
            for fb in msg["fallbacks"]:
                st.info(f"👉 {fb}")
                
        # 4. Hiển thị các tiêu chí đã trích xuất từ câu query (Parsed Constraints)
        if "parsed_constraints" in msg and msg["parsed_constraints"]:
            with st.expander("🔍 Xem thông tin phân tích câu lệnh (Parsed Constraints)"):
                constraints = msg["parsed_constraints"]
                for key, val in constraints.items():
                    if val:
                        st.markdown(f"<span class='constraint-badge'>{key}: {val}</span>", unsafe_allow_html=True)

# ==========================================
# NHẬN PHẢN HỒI TỪ KHUNG CHAT INPUT
# ==========================================
if chat_input := st.chat_input("Nhập nhu cầu ăn uống của bạn..."):
    # Hiển thị tin nhắn người dùng nhập lên khung chat
    st.session_state.messages.append({"role": "user", "content": chat_input})
    
    # Xác định đây là lượt hỏi đầu tiên hay là câu chỉnh sửa (Correction)
    is_correction = len(st.session_state.messages) > 2
    
    with st.chat_message("user"):
        st.write(chat_input)
        
    with st.chat_message("assistant"):
        with st.spinner("VinDine Concierge đang phân tích nhu cầu..."):
            if is_correction and st.session_state.original_query:
                res = call_recommend_api(st.session_state.original_query, correction=chat_input)
            else:
                st.session_state.original_query = chat_input
                res = call_recommend_api(chat_input)

            status = res.get("status")
            assistant_reply = ""
            msg_data = {"role": "assistant", "error_route": res.get("error_route")}

            if res.get("parsed_constraints"):
                msg_data["parsed_constraints"] = res.get("parsed_constraints")

            # Ghi nhận recommendations và AI explanations (nếu có)
            recs = res.get("recommendations", [])
            if recs:
                msg_data["recommendations"] = recs
            if res.get("ai_explanations"):
                msg_data["ai_explanations"] = res["ai_explanations"]

            if status == "error":
                err = res.get("error_route", {})
                assistant_reply = err.get("user_message", "Có lỗi xảy ra, vui lòng thử lại.")
                msg_data["content"] = assistant_reply
                msg_data.pop("error_route", None)
                st.session_state.original_query = ""
                st.session_state.active_clarification = None

            elif status == "success":
                assistant_reply = f"Mình đã tìm thấy {len(recs)} quán ăn phù hợp nhất với nhu cầu của bạn:"
                msg_data["content"] = assistant_reply
                
            elif status == "needs_clarification":
                questions = res.get("clarification_questions", [])
                assistant_reply = "Mình cần bạn làm rõ thêm một số thông tin để tìm kiếm chính xác nhất:"
                msg_data["content"] = assistant_reply
                st.session_state.active_clarification = questions
                
            elif status == "no_match":
                assistant_reply = "Rất tiếc, mình chưa tìm thấy quán ăn nào đáp ứng trọn vẹn yêu cầu hiện tại."
                msg_data["content"] = assistant_reply
                msg_data["fallbacks"] = res.get("fallback_suggestions", [])
                
            st.session_state.messages.append(msg_data)
            st.rerun()

# ==========================================
# RENDER BIỂU MẪU ĐỘNG ĐỂ LÀM RÕ THÔNG TIN
# ==========================================
if st.session_state.active_clarification:
    st.write("---")
    st.info("💬 Vui lòng trả lời câu hỏi làm rõ của AI dưới đây:")
    with st.form("clarify_form"):
        form_data = {}
        for q in st.session_state.active_clarification:
            form_data[q["id"]] = st.selectbox(q["question"], options=q["options"])
        
        submitted = st.form_submit_button("Gửi thông tin làm rõ 📨")
        if submitted:
            zone = form_data.get("current_zone")
            v_type = form_data.get("voucher_type")
            
            st.session_state.messages.append({
                "role": "user",
                "content": f"Bổ sung thông tin làm rõ: " + ", ".join([f"{k}: {v}" for k, v in form_data.items() if v])
            })
            
            with st.spinner("Đang cập nhật danh sách quán ăn..."):
                res = call_recommend_api(st.session_state.original_query, current_zone=zone, voucher_type=v_type)
                recs = res.get("recommendations", [])
                
                msg_data = {
                    "role": "assistant",
                    "content": f"Dựa trên thông tin làm rõ, đây là các đề xuất tối ưu:",
                    "recommendations": recs,
                    "error_route": res.get("error_route"),
                }
                if res.get("ai_explanations"):
                    msg_data["ai_explanations"] = res["ai_explanations"]
                if res.get("parsed_constraints"):
                    msg_data["parsed_constraints"] = res.get("parsed_constraints")
                    
                st.session_state.messages.append(msg_data)
            
            st.session_state.active_clarification = None
            st.rerun()
