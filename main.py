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
# 4. 데이터 모델 (심플 버전)
# ------------------------------------------------
def new_page(title: str, order_index: int) -> Dict[str, Any]:
    """blocks 필드는 memo 텍스트만 저장"""
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "subtitle": "",
        "order_index": order_index,
        "blocks": {"memo": ""},  # 심플 구조
    }


def get_memo_from_page(page: Dict[str, Any]) -> str:
    blocks = page.get("blocks")
    if isinstance(blocks, dict) and "memo" in blocks:
        return blocks["memo"] or ""
    # 예전 구조일 수도 있으니 방어적으로
    return ""


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
        # memo 값만 꺼내서 캐시
        page["memo"] = get_memo_from_page(page)
        st.session_state["current_page"] = page


def save_current_page():
    page = st.session_state.get("current_page")
    if not page:
        return
    # memo를 blocks에 다시 넣어서 저장
    page_to_save = {
        "id": page["id"],
        "title": page.get("title", ""),
        "subtitle": page.get("subtitle", ""),
        "order_index": page.get("order_index", 0),
        "blocks": {"memo": page.get("memo", "")},
    }
    update_page(page_to_save)
    reload_pages()


# ------------------------------------------------
# 6. 스타일 (톤 통일 + 깔끔한 사이드바/에디터)
# ------------------------------------------------
st.markdown(
    """
<style>
body {
    background-color: #d8dae2;
}

/* 메인 레이아웃 */
.memoking-main {
    max-width: 900px;
    margin: 0 auto;
    padding: 1rem;
}

/* 사이드바 배경을 본문과 살짝 다르게 */
[data-testid="stSidebar"] {
    background-color: #ececf3;
    min-width: 180px;
    max-width: 230px;
    border-right: 1px solid #d0d2dd;
}

/* 사이드바 제목 */
.sidebar-title {
    font-size: 1.4rem;
    font-weight: 800;
    letter-spacing: 0.04em;
}

/* 사이드바 라디오 리스트를 카드형으로 */
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
    display: block;
    padding: 5px 9px;
    border-radius: 10px;
    margin-bottom: 4px;
    background-color: rgba(255,255,255,0.6);
    border: 1px solid transparent;
    font-size: 0.86rem;
}

/* 라디오 동그라미 숨기기 */
[data-testid="stSidebar"] input[type="radio"] {
    display: none;
}

/* 사이드바 아이콘 버튼 더 작게 */
.sidebar-icon-btn button {
    padding: 0.05rem 0.25rem;
    font-size: 0.75rem;
}

/* 제목 카드 */
.title-card {
    background-color: #f6f6fb;
    border-radius: 16px;
    padding: 10px 14px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.04);
    margin-bottom: 12px;
}

/* 메모 카드 */
.memo-card {
    background-color: #f6f6fb;
    border-radius: 20px;
    padding: 12px 16px;
    box-shadow: 0 6px 14px rgba(0,0,0,0.05);
}

/* Text input / textarea 배경을 카드와 동일하게 */
.stTextInput input, .stTextArea textarea {
    background-color: #f6f6fb !important;
    border-radius: 10px !important;
    border: 1px solid #d4d6e2 !important;
}

/* 입력 폰트 조금 부드럽게 */
.stTextInput input, .stTextArea textarea {
    font-size: 0.9rem !important;
    line-height: 1.4 !important;
}

/* text_area 높이 조정 */
textarea {
    min-height: 320px;
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

    # 하단 아이콘 3개 (새 페이지 / 삭제 / 이름변경)
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
    # 상단: 제목 / 부제 (타이틀 카드)
    with st.container():
        st.markdown('<div class="title-card">', unsafe_allow_html=True)
        page["title"] = st.text_input(
            "",
            value=page["title"],
            key="title_input",
            label_visibility="collapsed",
            placeholder="제목",
        )
        page["subtitle"] = st.text_input(
            "",
            value=page.get("subtitle", ""),
            key="subtitle_input",
            label_visibility="collapsed",
            placeholder="부제 (선택)",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # 메모 카드
    with st.container():
        st.markdown('<div class="memo-card">', unsafe_allow_html=True)
        page["memo"] = st.text_area(
            "",
            value=page.get("memo", ""),
            key="memo_textarea",
            label_visibility="collapsed",
            placeholder="여기에 메모를 작성하세요",
        )
        if st.button("저장", type="primary", key="save_memo_btn"):
            st.session_state["current_page"] = page
            save_current_page()
            st.success("저장되었습니다.")
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
