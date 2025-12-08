# main.py
import os
import uuid
from typing import List, Dict, Any, Optional

import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

# -----------------------------
# 페이지 설정 (가장 먼저!)
# -----------------------------
st.set_page_config(
    page_title="memoking",
    page_icon="📝",
    layout="wide",
)

# -----------------------------
# 환경 변수 로딩
# -----------------------------
load_dotenv()
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY", ""))


# -----------------------------
# Supabase 클라이언트
# -----------------------------
@st.cache_resource
def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("⚠️ SUPABASE_URL / SUPABASE_ANON_KEY 환경변수를 설정해주세요.")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = get_supabase_client()
TABLE_NAME = "memoking_pages"

# -----------------------------
# 유틸 / 데이터 모델
# -----------------------------
def new_page(title: str = "새 페이지") -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "subtitle": "",
        "order_index": 0,
        "blocks": [],
    }


def new_folder(title: str = "새 폴더") -> Dict[str, Any]:
    return {
        "id": f"folder-{uuid.uuid4()}",
        "type": "folder",
        "title": title,
        "collapsed": False,
        "bg_level": 1,
        "children": [],
    }


def new_text_block(title: str = "제목", content: str = "") -> Dict[str, Any]:
    return {
        "id": f"text-{uuid.uuid4()}",
        "type": "text",
        "title": title,
        "content": content,
        "bg_level": 1,
        "folder_id": None,
    }


def new_point_block(content: str = "포인트 카드") -> Dict[str, Any]:
    return {
        "id": f"point-{uuid.uuid4()}",
        "type": "point",
        "content": content,
        "bg_level": 1,
        "folder_id": None,
    }


def get_block_index(blocks: List[Dict[str, Any]], block_id: str) -> int:
    for i, b in enumerate(blocks):
        if b["id"] == block_id:
            return i
    return -1


def toggle_bg(block: Dict[str, Any]):
    level = block.get("bg_level", 1)
    level = 1 if level >= 3 else level + 1
    block["bg_level"] = level


def bg_color(level: int) -> str:
    if level == 1:
        return "#FEFBE1"
    elif level == 2:
        return "#F7E38F"
    else:
        return "#F0C93D"


def move_block(blocks: List[Dict[str, Any]], block_id: str, direction: str):
    """폴더는 자식까지 묶어서 이동, 일반 블록은 한 칸 이동"""
    idx = get_block_index(blocks, block_id)
    if idx == -1:
        return

    block = blocks[idx]
    if block["type"] == "folder":
        start = idx
        end = idx + 1
        folder_id = block["id"]
        while end < len(blocks) and blocks[end].get("folder_id") == folder_id:
            end += 1

        if direction == "up" and start > 0:
            chunk = blocks[start:end]
            del blocks[start:end]
            new_pos = max(0, start - 1)
            blocks[new_pos:new_pos] = chunk
        elif direction == "down" and end < len(blocks):
            chunk = blocks[start:end]
            del blocks[start:end]
            new_pos = min(len(blocks), start + 1)
            blocks[new_pos:new_pos] = chunk
    else:
        if direction == "up" and idx > 0:
            blocks[idx - 1], blocks[idx] = blocks[idx], blocks[idx - 1]
        elif direction == "down" and idx < len(blocks) - 1:
            blocks[idx + 1], blocks[idx] = blocks[idx], blocks[idx + 1]


def delete_folder_with_children(blocks: List[Dict[str, Any]], folder_id: str):
    i = 0
    result = []
    while i < len(blocks):
        b = blocks[i]
        if b["id"] == folder_id:
            i += 1
            while i < len(blocks) and blocks[i].get("folder_id") == folder_id:
                i += 1
        else:
            result.append(b)
            i += 1
    blocks.clear()
    blocks.extend(result)


def remove_block(blocks: List[Dict[str, Any]], block_id: str):
    idx = get_block_index(blocks, block_id)
    if idx == -1:
        return
    block = blocks[idx]
    if block["type"] == "folder":
        delete_folder_with_children(blocks, block_id)
    else:
        del blocks[idx]


# -----------------------------
# Supabase CRUD
# -----------------------------
def fetch_pages() -> List[Dict[str, Any]]:
    resp = (
        supabase.table(TABLE_NAME)
        .select("id,title,subtitle,order_index")
        .order("order_index")
        .execute()
    )
    return resp.data or []


def fetch_page(page_id: str) -> Optional[Dict[str, Any]]:
    resp = supabase.table(TABLE_NAME).select("*").eq("id", page_id).single().execute()
    return resp.data


def insert_page(page: Dict[str, Any]) -> Dict[str, Any]:
    resp = supabase.table(TABLE_NAME).insert(
        {
            "id": page["id"],
            "title": page["title"],
            "subtitle": page["subtitle"],
            "order_index": page["order_index"],
            "blocks": page["blocks"],
        }
    ).execute()
    return resp.data[0]


def update_page(page: Dict[str, Any]):
    supabase.table(TABLE_NAME).update(
        {
            "title": page["title"],
            "subtitle": page["subtitle"],
            "order_index": page["order_index"],
            "blocks": page["blocks"],
        }
    ).eq("id", page["id"]).execute()


def delete_page_db(page_id: str):
    supabase.table(TABLE_NAME).delete().eq("id", page_id).execute()


# -----------------------------
# 샘플 페이지
# -----------------------------
def create_sample_page() -> Dict[str, Any]:
    page = new_page("첫 페이지")
    page["subtitle"] = "memoking 기본 샘플"

    folder = new_folder("샘플 폴더 1")
    text = new_text_block("제목 1", "여기에 메모를 써보세요.")
    text["folder_id"] = folder["id"]
    point = new_point_block("중요 포인트를 적어보세요.")
    point["folder_id"] = folder["id"]

    page["blocks"] = [folder, text, point]
    return page


# -----------------------------
# 세션 상태 & 로딩
# -----------------------------
def init_state():
    st.session_state.setdefault("pages", [])
    st.session_state.setdefault("selected_page_id", None)
    st.session_state.setdefault("current_page", None)
    st.session_state.setdefault("show_delete_page_prompt", False)
    st.session_state.setdefault("show_rename_page_prompt", False)
    st.session_state.setdefault("rename_title_temp", "")
    st.session_state.setdefault("pending_delete_block_id", None)
    st.session_state.setdefault("show_delete_block_prompt", False)


def load_pages_to_state():
    st.session_state["pages"] = fetch_pages()
    if not st.session_state["pages"]:
        page = create_sample_page()
        insert_page(page)
        st.session_state["pages"] = fetch_pages()

    if st.session_state["selected_page_id"] is None:
        st.session_state["selected_page_id"] = st.session_state["pages"][0]["id"]


def load_current_page():
    pid = st.session_state.get("selected_page_id")
    if not pid:
        return
    page = fetch_page(pid)
    if page is None:
        return
    page["blocks"] = page.get("blocks") or []
    st.session_state["current_page"] = page


def save_current_page():
    page = st.session_state.get("current_page")
    if page:
        update_page(page)
        load_pages_to_state()


# -----------------------------
# 스타일 (카드 라인 / 사이드바 배경 등)
# -----------------------------
st.markdown(
    """
<style>
body {
    background-color: #d3d7dd;
}
.memoking-main {
    max-width: 900px;
    margin: 0 auto;
    padding: 1rem;
}
[data-testid="stSidebar"] {
    background-color: #e4e5ea;
}
.memo-card {
    border-radius: 16px;
    padding: 10px 12px;
    margin-bottom: 10px;
    border: 1px solid #d0d0d0;
}
.memo-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    margin-bottom: 4px;
    font-size: 12px;
}
.memo-header-left {
    font-weight: 600;
}
.memo-header-right button {
    margin-left: 2px;
}
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------
# 앱 로직 시작
# -----------------------------
init_state()
load_pages_to_state()

pages = st.session_state["pages"]
current_id = st.session_state.get("selected_page_id")

# ===== 사이드바 =====
with st.sidebar:
    st.markdown("### memo<br>king", unsafe_allow_html=True)
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

    if st.button("＋ 새 페이지", use_container_width=True):
        max_idx = max((p["order_index"] for p in pages), default=-1)
        page = new_page(f"새 페이지 {max_idx + 2}")
        page["order_index"] = max_idx + 1
        insert_page(page)
        load_pages_to_state()
        st.session_state["selected_page_id"] = page["id"]
        load_current_page()
        st.rerun()

    if st.button("🗑 삭제", use_container_width=True):
        st.session_state["show_delete_page_prompt"] = True

    if st.button("✏️ 편집", use_container_width=True):
        st.session_state["show_rename_page_prompt"] = True
        # 현재 제목을 임시 변수에 세팅
        cur = next((p for p in pages if p["id"] == st.session_state["selected_page_id"]), None)
        st.session_state["rename_title_temp"] = cur["title"] if cur else ""

    # 페이지 삭제 확인 박스 (사이드바 안)
    if st.session_state.get("show_delete_page_prompt", False):
        st.warning("페이지를 삭제하시겠습니까?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("삭제 확인"):
                pid = st.session_state.get("selected_page_id")
                if pid:
                    delete_page_db(pid)
                    load_pages_to_state()
                    if st.session_state["pages"]:
                        st.session_state["selected_page_id"] = st.session_state["pages"][0]["id"]
                    else:
                        st.session_state["selected_page_id"] = None
                st.session_state["show_delete_page_prompt"] = False
                st.rerun()
        with c2:
            if st.button("취소"):
                st.session_state["show_delete_page_prompt"] = False
                st.rerun()

    # 페이지 제목 편집 박스 (사이드바 안)
    if st.session_state.get("show_rename_page_prompt", False):
        st.info("페이지 제목을 수정하세요.")
        new_title = st.text_input(
            "새 제목",
            value=st.session_state.get("rename_title_temp", ""),
            label_visibility="collapsed",
            key="rename_page_input_sidebar",
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("저장", key="rename_save_btn"):
                pid = st.session_state.get("selected_page_id")
                page_db = fetch_page(pid)
                if page_db:
                    page_db["title"] = new_title
                    update_page(page_db)
                load_pages_to_state()
                st.session_state["show_rename_page_prompt"] = False
                st.rerun()
        with c2:
            if st.button("취소", key="rename_cancel_btn"):
                st.session_state["show_rename_page_prompt"] = False
                st.rerun()

# 현재 페이지 로딩
load_current_page()
page = st.session_state.get("current_page")

# ===== 메인 영역 =====
st.markdown('<div class="memoking-main">', unsafe_allow_html=True)

if not page:
    st.info("왼쪽 사이드바에서 페이지를 선택하거나 새 페이지를 만들어주세요.")
else:
    # --- 상단 헤더: 제목/부제 라벨만 (컴팩트) ---
    st.markdown(
        f"<div style='font-weight:700;font-size:1.1rem;margin-bottom:2px;'>{page['title']}</div>",
        unsafe_allow_html=True,
    )
    subtitle = page.get("subtitle") or ""
    if subtitle.strip():
        st.markdown(
            f"<div style='color:#666;font-size:0.9rem;margin-bottom:8px;'>{subtitle}</div>",
            unsafe_allow_html=True,
    )
    st.markdown("---")

    blocks: List[Dict[str, Any]] = page["blocks"]

    # --- 블록 렌더링 ---
    def render_block(block: Dict[str, Any]):
        btype = block["type"]
        level = block.get("bg_level", 1)
        color = bg_color(level)

        st.markdown(
            f'<div class="memo-card" style="background-color:{color}">',
            unsafe_allow_html=True,
        )

        # 상단 컨트롤 가로 정렬
        c_title, c_up, c_down, c_bg, c_del = st.columns([8, 1, 1, 1, 1])

        # 왼쪽: 폴더/카드 제목 레이블
        with c_title:
            if btype == "folder":
                label = block.get("title", "폴더")
            elif btype == "text":
                label = block.get("title", "텍스트 카드")
            else:
                label = "포인트 카드"
            st.markdown(
                f"<div style='font-size:12px;font-weight:600;'>{label}</div>",
                unsafe_allow_html=True,
            )

        # 오른쪽: 버튼들 (위/아래/색/삭제)
        with c_up:
            if st.button("↑", key=f"up_{block['id']}"):
                move_block(blocks, block["id"], "up")
                save_current_page()
                st.rerun()
        with c_down:
            if st.button("↓", key=f"down_{block['id']}"):
                move_block(blocks, block["id"], "down")
                save_current_page()
                st.rerun()
        with c_bg:
            if st.button("🎨", key=f"bg_{block['id']}"):
                toggle_bg(block)
                save_current_page()
                st.rerun()
        with c_del:
            if st.button("🗑", key=f"del_{block['id']}"):
                st.session_state["pending_delete_block_id"] = block["id"]
                st.session_state["show_delete_block_prompt"] = True

        # 본문 입력 영역 (제목/내용)
        if btype == "folder":
            block["title"] = st.text_input(
                "",
                value=block.get("title", ""),
                key=f"folder_title_{block['id']}",
                label_visibility="collapsed",
            )
        elif btype == "text":
            block["title"] = st.text_input(
                "",
                value=block.get("title", ""),
                key=f"text_title_{block['id']}",
                label_visibility="collapsed",
            )
            block["content"] = st.text_area(
                "",
                value=block.get("content", ""),
                key=f"text_content_{block['id']}",
                height=120,
                label_visibility="collapsed",
            )
        elif btype == "point":
            block["content"] = st.text_input(
                "",
                value=block.get("content", ""),
                key=f"point_content_{block['id']}",
                label_visibility="collapsed",
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # 폴더 + 자식 구조에 맞게 순서대로 렌더링
    i = 0
    while i < len(blocks):
        b = blocks[i]
        if b["type"] == "folder":
            render_block(b)
            folder_id = b["id"]
            i += 1
            while i < len(blocks) and blocks[i].get("folder_id") == folder_id:
                render_block(blocks[i])
                i += 1
        else:
            render_block(b)
            i += 1

    st.markdown("---")

    # 카드 추가 버튼들
    st.markdown("#### 카드 추가")
    add_col1, add_col2, add_col3 = st.columns(3)
    with add_col1:
        if st.button("＋ 폴더", use_container_width=True):
            folder = new_folder()
            blocks.append(folder)
            save_current_page()
            st.rerun()
    with add_col2:
        if st.button("＋ 텍스트 카드", use_container_width=True):
            text_b = new_text_block()
            blocks.append(text_b)
            save_current_page()
            st.rerun()
    with add_col3:
        if st.button("＋ 포인트 카드", use_container_width=True):
            point_b = new_point_block()
            blocks.append(point_b)
            save_current_page()
            st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ===== 블록 삭제 확인 박스 (본문 아래) =====
if st.session_state.get("show_delete_block_prompt", False):
    st.warning("이 카드(또는 폴더)를 삭제하시겠습니까?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("카드 삭제 확인", key="confirm_block_delete"):
            page_cur = st.session_state.get("current_page")
            block_id = st.session_state.get("pending_delete_block_id")
            if page_cur and block_id:
                remove_block(page_cur["blocks"], block_id)
                save_current_page()
            st.session_state["pending_delete_block_id"] = None
            st.session_state["show_delete_block_prompt"] = False
            st.rerun()
    with c2:
        if st.button("취소", key="cancel_block_delete"):
            st.session_state["pending_delete_block_id"] = None
            st.session_state["show_delete_block_prompt"] = False
            st.rerun()
