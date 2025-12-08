# main.py
import os
import uuid
from typing import Dict, Any, List, Optional

import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

# ------------------------------------------------
# 1. 페이지 설정 (항상 맨 위)
# ------------------------------------------------
st.set_page_config(
    page_title="memoking",
    page_icon="📝",
    layout="wide",
)

# ------------------------------------------------
# 2. 환경변수 & Supabase 클라이언트
# ------------------------------------------------
load_dotenv()
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY", ""))


@st.cache_resource
def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("⚠️ SUPABASE_URL / SUPABASE_ANON_KEY 환경변수를 설정해주세요.")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = get_supabase_client()
TABLE_NAME = "memoking_pages"

# ------------------------------------------------
# 3. DB 유틸
# ------------------------------------------------
def fetch_pages() -> List[Dict[str, Any]]:
    """사이드바에 쓸 페이지 리스트"""
    resp = (
        supabase.table(TABLE_NAME)
        .select("id, title, subtitle, order_index, blocks")
        .order("order_index")
        .execute()
    )
    return resp.data or []


def fetch_page(page_id: str) -> Optional[Dict[str, Any]]:
    resp = (
        supabase.table(TABLE_NAME)
        .select("*")
        .eq("id", page_id)
        .single()
        .execute()
    )
    return resp.data


def insert_page(page: Dict[str, Any]) -> Dict[str, Any]:
    resp = supabase.table(TABLE_NAME).insert(page).execute()
    return resp.data[0]


def update_page(page: Dict[str, Any]):
    supabase.table(TABLE_NAME).update(page).eq("id", page["id"]).execute()


def delete_page_db(page_id: str):
    supabase.table(TABLE_NAME).delete().eq("id", page_id).execute()


# ------------------------------------------------
# 4. 데이터 모델 (카드 리스트 구조)
# ------------------------------------------------
def new_page(title: str, order_index: int) -> Dict[str, Any]:
    """blocks -> cards: [ {id,title,content}, ... ]"""
    first_card = {
        "id": str(uuid.uuid4()),
        "title": "",
        "content": "",
    }
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "subtitle": "",
        "order_index": order_index,
        "blocks": {"cards": [first_card]},
    }


def extract_cards_from_blocks(page: Dict[str, Any]) -> List[Dict[str, Any]]:
    """기존 memo 구조도 카드 1개로 변환해주는 함수"""
    blocks = page.get("blocks") or {}
    cards: List[Dict[str, Any]] = []

    if isinstance(blocks, dict):
        if "cards" in blocks and isinstance(blocks["cards"], list):
            cards = blocks["cards"]
        elif "memo" in blocks:  # 예전 단일 메모 구조
            cards = [
                {
                    "id": str(uuid.uuid4()),
                    "title": page.get("title", ""),
                    "content": blocks.get("memo", "") or "",
                }
            ]

    # 내용이 전혀 없는 카드(제목, 내용 둘 다 빈 것)는 보여주지 않기
    cards = [
        c for c in cards
        if (c.get("title") or c.get("content"))
    ]

    # 그래도 없으면 한 개 생성
    if not cards:
        cards = [
            {
                "id": str(uuid.uuid4()),
                "title": "",
                "content": "",
            }
        ]
    return cards


# ------------------------------------------------
# 5. 세션 상태
# ------------------------------------------------
def init_state():
    st.session_state.setdefault("pages", [])
    st.session_state.setdefault("selected_page_id", None)
    st.session_state.setdefault("current_page", None)
    st.session_state.setdefault("show_delete_prompt", False)
    st.session_state.setdefault("show_rename_prompt", False)
    st.session_state.setdefault("rename_temp_title", "")


def reload_pages():
    st.session_state["pages"] = fetch_pages()
    if not st.session_state["pages"]:
        # 아무 페이지도 없으면 첫 페이지 하나 만들기
        first = new_page("첫 페이지", 0)
        insert_page(first)
        st.session_state["pages"] = fetch_pages()

    if st.session_state["selected_page_id"] is None:
        st.session_state["selected_page_id"] = st.session_state["pages"][0]["id"]


def load_current_page():
    pid = st.session_state.get("selected_page_id")
    if not pid:
        return
    page = fetch_page(pid)
    if page:
        page["cards"] = extract_cards_from_blocks(page)
        st.session_state["current_page"] = page


def save_current_page():
    page = st.session_state.get("current_page")
    if not page:
        return
    cards = page.get("cards", [])
    page_to_save = {
        "id": page["id"],
        "title": page.get("title", ""),
        "subtitle": page.get("subtitle", ""),
        "order_index": page.get("order_index", 0),
        "blocks": {"cards": cards},
    }
    update_page(page_to_save)
    reload_pages()


# ------------------------------------------------
# 6. 스타일 (배경/에디터 색, 카드, 버튼)
# ------------------------------------------------
st.markdown(
    """
<style>
:root {
    --memoking-bg: #dde1ea;
    --memoking-text: #333333;
}

/* 전체 배경 & 텍스트색 */
body {
    background-color: var(--memoking-bg);
    color: var(--memoking-text);
}

/* 메인 컨테이너 배경도 동일하게 */
[data-testid="stAppViewContainer"] .main .block-container {
    background-color: var(--memoking-bg);
}

/* 전체 텍스트 색상 진한 그레이 */
html, body, [class^="css"], .stMarkdown, .stTextInput, .stTextArea {
    color: var(--memoking-text) !important;
}

/* 메인 레이아웃 */
.memoking-main {
    max-width: 900px;
    margin: 0 auto;
    padding: 1rem;
}

/* 사이드바 배경 */
[data-testid="stSidebar"] {
    background-color: #e7e9f0;
    min-width: 170px;
    max-width: 220px;
    border-right: 1px solid #c1c4d0;
}

/* 사이드바 제목을 조금 더 크게, 굵게 */
.sidebar-title {
    font-size: 1.5rem;
    font-weight: 800;
    letter-spacing: 0.06em;
}

/* 사이드바 라디오: 한 줄 네비게이션 느낌 */
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
    display: block;
    padding: 2px 4px 4px 0;
    margin-bottom: 2px;
    font-size: 0.85rem;
    border-bottom: 1px solid #d0d3dd;
    background-color: transparent;
}

/* 라디오 동그라미 숨기기 */
[data-testid="stSidebar"] input[type="radio"] {
    display: none;
}

/* 아이콘 버튼 더 작게 */
.sidebar-icon-btn button {
    padding: 0.05rem 0.25rem;
    font-size: 0.75rem;
}

/* 입력·에디터 배경을 흰색으로 */
.stTextInput input,
.stTextArea textarea {
    background-color: #ffffff !important;
    border-radius: 10px !important;
    border: 1px solid #c1c4d0 !important;
    color: var(--memoking-text) !important;
}

/* 제목은 굵게 */
.stTextInput input {
    font-weight: 700 !important;
}

/* textarea 기본 높이 (카드당 약 1/3 화면) */
.stTextArea textarea {
    min-height: 120px;
    font-size: 0.9rem !important;
    line-height: 1.4 !important;
}

/* 카드 스타일: 살짝 다른 톤의 배경 + 테두리 + 그림자 */
.memo-card {
    background-color: #f4f5fb;
    border-radius: 18px;
    padding: 10px 12px;
    border: 1px solid #c1c4d0;
    box-shadow: 0 4px 10px rgba(0,0,0,0.05);
}
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------
# 7. 앱 실행
# ------------------------------------------------
init_state()
reload_pages()
load_current_page()

pages = st.session_state["pages"]
current_id = st.session_state.get("selected_page_id")

# ---------- 사이드바 ----------
with st.sidebar:
    st.markdown('<div class="sidebar-title">memo<br>king</div>', unsafe_allow_html=True)
    st.markdown("---")

    page_ids = [p["id"] for p in pages]
    page_titles = [p["title"] for p in pages]

    if current_id in page_ids:
        current_index = page_ids.index(current_id)
    else:
        current_index = 0

    selected_title = st.radio(
        "페이지 선택",
        page_titles,
        index=current_index,
        label_visibility="collapsed",
    )
    selected_id = page_ids[page_titles.index(selected_title)]

    if selected_id != current_id:
        st.session_state["selected_page_id"] = selected_id
        load_current_page()
        st.rerun()

    st.markdown("---")

    # 하단 아이콘 3개 (새 페이지 / 삭제 / 이름변경) - 작은 버튼
    col_new, col_del, col_edit = st.columns(3)

    with col_new:
        st.markdown('<div class="sidebar-icon-btn">', unsafe_allow_html=True)
        if st.button("➕", use_container_width=True, key="btn_new_page"):
            max_idx = max((p["order_index"] for p in pages), default=-1)
            new = new_page(f"새 페이지 {max_idx + 2}", max_idx + 1)
            insert_page(new)
            reload_pages()
            st.session_state["selected_page_id"] = new["id"]
            load_current_page()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_del:
        st.markdown('<div class="sidebar-icon-btn">', unsafe_allow_html=True)
        if st.button("🗑", use_container_width=True, key="btn_delete_page"):
            st.session_state["show_delete_prompt"] = True
        st.markdown("</div>", unsafe_allow_html=True)

    with col_edit:
        st.markdown('<div class="sidebar-icon-btn">', unsafe_allow_html=True)
        if st.button("✏️", use_container_width=True, key="btn_rename_page"):
            st.session_state["show_rename_prompt"] = True
            cur = next(
                (p for p in pages if p["id"] == st.session_state["selected_page_id"]),
                None,
            )
            st.session_state["rename_temp_title"] = cur["title"] if cur else ""
        st.markdown("</div>", unsafe_allow_html=True)

    # 삭제 확인 박스
    if st.session_state.get("show_delete_prompt", False):
        st.warning("현재 페이지를 삭제하시겠습니까?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("삭제", key="confirm_delete_page"):
                pid = st.session_state.get("selected_page_id")
                if pid:
                    delete_page_db(pid)
                    reload_pages()
                    if st.session_state["pages"]:
                        st.session_state["selected_page_id"] = st.session_state["pages"][0]["id"]
                    else:
                        st.session_state["selected_page_id"] = None
                        st.session_state["current_page"] = None
                st.session_state["show_delete_prompt"] = False
                st.rerun()
        with c2:
            if st.button("취소", key="cancel_delete_page"):
                st.session_state["show_delete_prompt"] = False
                st.rerun()

    # 이름 변경 박스
    if st.session_state.get("show_rename_prompt", False):
        st.info("페이지 제목을 수정하세요.")
        new_title = st.text_input(
            "",
            value=st.session_state.get("rename_temp_title", ""),
            key="rename_page_input",
            label_visibility="collapsed",
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("저장", key="rename_save"):
                pid = st.session_state.get("selected_page_id")
                p = fetch_page(pid)
                if p:
                    p["title"] = new_title
                    update_page(p)
                reload_pages()
                st.session_state["show_rename_prompt"] = False
                st.rerun()
        with c2:
            if st.button("취소", key="rename_cancel"):
                st.session_state["show_rename_prompt"] = False
                st.rerun()

# ---------- 메인 영역 ----------
st.markdown('<div class="memoking-main">', unsafe_allow_html=True)

page = st.session_state.get("current_page")

if not page:
    st.info("왼쪽에서 페이지를 선택하거나 새 페이지를 만들어주세요.")
else:
    # 1) 페이지 제목: 라벨(텍스트)만, 굵게
    st.markdown(
        f"<div style='font-size:1.0rem;font-weight:700;margin-bottom:6px;'>{page['title']}</div>",
        unsafe_allow_html=True,
    )

    cards: List[Dict[str, Any]] = page.get("cards", [])
    if not cards:
        cards.append({"id": str(uuid.uuid4()), "title": "", "content": ""})

    # 2) 카드들 렌더링
    for idx, card in enumerate(cards):
        with st.container():
            st.markdown('<div class="memo-card">', unsafe_allow_html=True)

            card["title"] = st.text_input(
                "",
                value=card.get("title", ""),
                key=f"card_title_{card['id']}",
                label_visibility="collapsed",
                placeholder=f"카드 {idx+1} 제목",
            )

            card["content"] = st.text_area(
                "",
                value=card.get("content", ""),
                key=f"card_content_{card['id']}",
                label_visibility="collapsed",
                placeholder="내용을 입력하세요",
            )

            st.markdown("</div>", unsafe_allow_html=True)

        st.write("")  # 카드 간 간격

    page["cards"] = cards
    st.session_state["current_page"] = page

    # 3) 카드 영역과 버튼 영역 사이에 항상 separator
    st.markdown("---")

    # 4) 버튼 줄: 저장 / 카드 추가 / 카드 삭제 (가로 3개)
    b1, b2, b3 = st.columns(3)

    with b1:
        if st.button("저장", type="primary", key="save_cards_btn"):
            save_current_page()
            st.success("저장되었습니다.")

    with b2:
        if st.button("＋ 카드", key="add_card_btn"):
            cards.append(
                {
                    "id": str(uuid.uuid4()),
                    "title": "",
                    "content": "",
                }
            )
            page["cards"] = cards
            st.session_state["current_page"] = page
            save_current_page()
            st.rerun()

    with b3:
        if st.button("🗑 카드", key="delete_card_btn"):
            if len(cards) > 1:
                cards.pop()  # 마지막 카드 삭제
            else:
                # 카드가 1개만 있으면 내용만 비우기
                cards[0]["title"] = ""
                cards[0]["content"] = ""
            page["cards"] = cards
            st.session_state["current_page"] = page
            save_current_page()
            st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
