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
# 블록/페이지 유틸
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
    idx = get_block_index(blocks, block_id)
    if idx == -1:
        return

    block = blocks[idx]
    if block["type"] == "folder":
        # 폴더 + children 묶어서 이동
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
# 샘플 페이지 생성
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
    st.session_state.setdefault("show_delete_page_modal", False)
    st.session_state.setdefault("show_rename_page_modal", False)
    st.session_state.setdefault("pending_delete_block_id", None)
    st.session_state.setdefault("show_delete_block_modal", False)


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
# 기본 스타일 (배경 + 메인 컨테이너 + 사이드바 색)
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
    border-radius: 18px;
    padding: 10px 12px;
    margin-bottom: 10px;
    border: 1px solid rgba(0,0,0,0.05);
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

# ===== 왼쪽: Streamlit 사이드바 =====
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

    col_new, col_del, col_edit = st.columns(1), st.columns(1), st.columns(1)

    # 새 페이지
    if st.button("＋ 새 페이지", use_container_width=True):
        max_idx = max((p["order_index"] for p in pages), default=-1)
        page = new_page(f"새 페이지 {max_idx + 2}")
        page["order_index"] = max_idx + 1
        insert_page(page)
        load_pages_to_state()
        st.session_state["selected_page_id"] = page["id"]
        load_current_page()
        st.rerun()

    # 삭제 버튼
    if st.button("🗑 삭제", use_container_width=True):
        st.session_state["show_delete_page_modal"] = True

    # 편집 버튼
    if st.button("✏️ 편집", use_container_width=True):
        st.session_state["show_rename_page_modal"] = True

# 사이드바 선택 반영 후 현재 페이지 로드
load_current_page()
page = st.session_state.get("current_page")

# ===== 오른쪽: 메인 영역 =====
st.markdown('<div class="memoking-main">', unsafe_allow_html=True)

if not page:
    st.info("왼쪽 사이드바에서 페이지를 선택하거나 새 페이지를 만들어주세요.")
else:
    st.markdown("#### 현재 페이지")
    page["title"] = st.text_input("제목", value=page["title"], key="page_title_input")
    page["subtitle"] = st.text_input(
        "부제(선택 사항)",
        value=page.get("subtitle", ""),
        key="page_subtitle_input",
    )

    if st.button("페이지 저장", key="save_page_button"):
        save_current_page()
        st.success("페이지가 저장되었습니다.")

    st.markdown("---")
    st.markdown("#### 메모")

    blocks: List[Dict[str, Any]] = page["blocks"]

    def render_block(block: Dict[str, Any]):
        btype = block["type"]
        level = block.get("bg_level", 1)
        color = bg_color(level)

        c2, c3, c4, c5 = st.columns(4)
        with c2:
            if st.button("↑", key=f"up_{block['id']}"):
                move_block(blocks, block["id"], "up")
                save_current_page()
                st.rerun()
        with c3:
            if st.button("↓", key=f"down_{block['id']}"):
                move_block(blocks, block["id"], "down")
                save_current_page()
                st.rerun()
        with c4:
            if st.button("🎨", key=f"bg_{block['id']}"):
                toggle_bg(block)
                save_current_page()
                st.rerun()
        with c5:
            if st.button("🗑", key=f"del_{block['id']}"):
                st.session_state["pending_delete_block_id"] = block["id"]
                st.session_state["show_delete_block_modal"] = True

        st.markdown(
            f'<div class="memo-card" style="background-color:{color}">',
            unsafe_allow_html=True,
        )
        if btype == "folder":
            block["title"] = st.text_input(
                "폴더 제목",
                value=block.get("title", ""),
                key=f"folder_title_{block['id']}",
            )
        elif btype == "text":
            block["title"] = st.text_input(
                "텍스트 카드 제목",
                value=block.get("title", ""),
                key=f"text_title_{block['id']}",
            )
            block["content"] = st.text_area(
                "내용",
                value=block.get("content", ""),
                key=f"text_content_{block['id']}",
                height=120,
            )
        elif btype == "point":
            block["content"] = st.text_input(
                "포인트 카드",
                value=block.get("content", ""),
                key=f"point_content_{block['id']}",
            )
        st.markdown("</div>", unsafe_allow_html=True)

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

# ===== 모달들 =====
# 페이지 삭제
if st.session_state.get("show_delete_page_modal", False):
    with st.modal("페이지 삭제"):
        st.write("정말 이 페이지를 삭제하시겠습니까?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("삭제", type="primary"):
                pid = st.session_state.get("selected_page_id")
                if pid:
                    delete_page_db(pid)
                    load_pages_to_state()
                    if st.session_state["pages"]:
                        st.session_state["selected_page_id"] = st.session_state["pages"][0]["id"]
                    else:
                        st.session_state["selected_page_id"] = None
                st.session_state["show_delete_page_modal"] = False
                st.rerun()
        with c2:
            if st.button("취소"):
                st.session_state["show_delete_page_modal"] = False
                st.rerun()

# 페이지 제목 편집
if st.session_state.get("show_rename_page_modal", False):
    current_id = st.session_state.get("selected_page_id")
    current_title = ""
    for p in st.session_state["pages"]:
        if p["id"] == current_id:
            current_title = p["title"]
            break

    with st.modal("페이지 제목 편집"):
        new_title = st.text_input("새 제목", value=current_title, key="rename_page_input")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("저장", type="primary"):
                page_db = fetch_page(current_id)
                if page_db:
                    page_db["title"] = new_title
                    update_page(page_db)
                load_pages_to_state()
                st.session_state["show_rename_page_modal"] = False
                st.rerun()
        with c2:
            if st.button("취소"):
                st.session_state["show_rename_page_modal"] = False
                st.rerun()

# 블록 삭제
if st.session_state.get("show_delete_block_modal", False):
    with st.modal("블록 삭제"):
        st.write("이 카드(또는 폴더)를 삭제하시겠습니까?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("삭제", type="primary", key="confirm_block_delete"):
                page_cur = st.session_state.get("current_page")
                block_id = st.session_state.get("pending_delete_block_id")
                if page_cur and block_id:
                    remove_block(page_cur["blocks"], block_id)
                    save_current_page()
                st.session_state["pending_delete_block_id"] = None
                st.session_state["show_delete_block_modal"] = False
                st.rerun()
        with c2:
            if st.button("취소", key="cancel_block_delete"):
                st.session_state["pending_delete_block_id"] = None
                st.session_state["show_delete_block_modal"] = False
                st.rerun()
