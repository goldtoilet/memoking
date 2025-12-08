import streamlit as st
import sqlite3
from streamlit_option_menu import option_menu

st.set_page_config(page_title="MemoKing", layout="wide")

# 맨 위 스크롤용 앵커
st.markdown('<a name="top"></a>', unsafe_allow_html=True)

# ---------------------------
# DB 초기화 (SQLite)
# ---------------------------
def init_db():
    conn = sqlite3.connect("memo.db")
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cards(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER,
            title TEXT,
            content TEXT,
            FOREIGN KEY(page_id) REFERENCES pages(id)
        )
        """
    )

    conn.commit()
    return conn


db = init_db()

# ---------------------------
# PAGE / CARD 함수
# ---------------------------
def get_pages():
    cur = db.cursor()
    cur.execute("SELECT id, title FROM pages ORDER BY id ASC")
    return cur.fetchall()


def add_page(title="새 페이지"):
    cur = db.cursor()
    cur.execute("INSERT INTO pages(title) VALUES(?)", (title,))
    db.commit()
    return cur.lastrowid


def delete_page(page_id: int):
    cur = db.cursor()
    cur.execute("DELETE FROM cards WHERE page_id=?", (page_id,))
    cur.execute("DELETE FROM pages WHERE id=?", (page_id,))
    db.commit()


def rename_page(page_id: int, new_title: str):
    cur = db.cursor()
    cur.execute("UPDATE pages SET title=? WHERE id=?", (new_title, page_id))
    db.commit()


def get_cards(page_id: int):
    cur = db.cursor()
    cur.execute(
        "SELECT id, title, content FROM cards WHERE page_id=? ORDER BY id ASC",
        (page_id,),
    )
    return cur.fetchall()


def add_card(page_id: int):
    cur = db.cursor()
    cur.execute(
        "INSERT INTO cards(page_id, title, content) VALUES (?, ?, ?)",
        (page_id, "제목 없음", ""),
    )
    db.commit()


def update_card(card_id: int, title: str, content: str):
    cur = db.cursor()
    cur.execute(
        "UPDATE cards SET title=?, content=? WHERE id=?",
        (title, content, card_id),
    )
    db.commit()


def delete_card_by_title(page_id: int, title: str):
    """같은 제목이 여러 개면 첫 번째 카드만 삭제."""
    cur = db.cursor()
    cur.execute(
        "SELECT id FROM cards WHERE page_id=? AND title=? ORDER BY id ASC",
        (page_id, title),
    )
    row = cur.fetchone()
    if row:
        card_id = row[0]
        cur.execute("DELETE FROM cards WHERE id=?", (card_id,))
        db.commit()
        return True
    return False


# ---------------------------
# 공통 스타일 (CSS)
# ---------------------------
st.markdown(
    """
<style>
/* 전체 배경 톤 */
[data-testid="stAppViewContainer"] {
    background-color: #f4f5f7;
}

/* 세로 블럭 간격 전체적으로 줄이기 */
.stVerticalBlock {
    gap: 0.25rem !important;
}

/* 라벨 숨기기 */
.stTextInput label, .stTextArea label {
    display: none !important;
}

/* 입력/에디터 스타일 */
.stTextInput input, .stTextArea textarea {
    background-color: #f4f5f7 !important;
    border-radius: 10px !important;
    border: 1px solid #cfd3de !important;
    color: #222 !important;
}

/* 제목 인풋 : 일반 굵기 */
.stTextInput input {
    font-weight: 400 !important;
    font-size: 0.95rem !important;
}

/* 내용 textarea 높이 */
.stTextArea textarea {
    min-height: 110px !important;
    font-size: 0.95rem !important;
}

/* 버튼 – 작고 컴팩트하게 */
.stButton button {
    padding: 0.18rem 0.6rem !important;
    font-size: 0.80rem !important;
    border-radius: 8px !important;
}

/* Expander 헤더 텍스트 볼드 */
details > summary {
    font-weight: 700 !important;
    color: #222 !important;
}

/* 구분선 간격 (위아래 여백 최소화) */
hr {
    margin-top: 0.45rem !important;
    margin-bottom: 0.45rem !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------
# 세션 상태 기본값
# ---------------------------
if "renaming_page" not in st.session_state:
    st.session_state["renaming_page"] = False
if "rename_temp" not in st.session_state:
    st.session_state["rename_temp"] = ""
if "confirm_delete_page" not in st.session_state:
    st.session_state["confirm_delete_page"] = False
if "card_delete_mode" not in st.session_state:
    st.session_state["card_delete_mode"] = False

# ---------------------------
# 사이드바 : 페이지 리스트 + 가로형 버튼 3개
# ---------------------------
with st.sidebar:
    st.markdown("### memo king")

    pages = get_pages()
    if not pages:
        add_page("아이디어")
        pages = get_pages()

    page_ids = [p[0] for p in pages]
    page_titles = [p[1] for p in pages]

    # 현재 선택 페이지 인덱스
    current_index = 0
    if (
        "current_page_id" in st.session_state
        and st.session_state["current_page_id"] in page_ids
    ):
        current_index = page_ids.index(st.session_state["current_page_id"])

    # 페이지 리스트
    choice = option_menu(
        "",
        page_titles,
        icons=["journal-text"] * len(page_titles),
        menu_icon="menu-app",
        default_index=current_index,
        styles={
            "container": {"background-color": "#f5f6fa"},
            "icon": {"color": "#4c4c4c"},
            "nav-link": {
                "font-size": "15px",
                "padding": "6px 10px",
                "color": "#333",
                "--hover-color": "#e4e6eb",
            },
            "nav-link-selected": {
                "background-color": "#dcdfe5",
                "color": "black",
            },
        },
    )

    current_page_id = page_ids[page_titles.index(choice)]
    st.session_state["current_page_id"] = current_page_id

    st.markdown("---")

    # 페이지 추가 / 삭제 / 이름변경 버튼 (가로)
    c_add, c_del, c_ren = st.columns(3)
    with c_add:
        if st.button("➕", key="btn_add_page"):
            add_page("새 페이지")
            st.experimental_rerun()

    with c_del:
        if st.button("🗑", key="btn_del_page"):
            st.session_state["confirm_delete_page"] = True

    with c_ren:
        if st.button("✏️", key="btn_rename_page"):
            st.session_state["renaming_page"] = True
            st.session_state["rename_temp"] = choice

    # 페이지 삭제 확인 UI
    if st.session_state["confirm_delete_page"]:
        st.warning("페이지를 삭제하시겠습니까?")
        d1, d2 = st.columns(2)
        with d1:
            if st.button("삭제", key="confirm_page_delete"):
                delete_page(current_page_id)
                st.session_state["confirm_delete_page"] = False
                st.experimental_rerun()
        with d2:
            if st.button("취소", key="cancel_page_delete"):
                st.session_state["confirm_delete_page"] = False
                st.experimental_rerun()

    # 페이지 이름 변경 UI
    if st.session_state["renaming_page"]:
        new_title = st.text_input(
            "새 페이지 이름",
            value=st.session_state["rename_temp"],
            key="rename_input",
        )
        r1, r2 = st.columns(2)
        with r1:
            if st.button("이름 변경", key="rename_save"):
                rename_page(current_page_id, new_title.strip() or "제목 없음")
                st.session_state["renaming_page"] = False
                st.experimental_rerun()
        with r2:
            if st.button("취소", key="rename_cancel"):
                st.session_state["renaming_page"] = False
                st.experimental_rerun()

# ---------------------------
# 본문 상단 : 페이지 제목 + 카드 툴바 버튼 3개
# ---------------------------
st.markdown(f"## {choice}")
st.markdown("---")

# 카드 목록
cards = get_cards(current_page_id)
if not cards:
    add_card(current_page_id)
    cards = get_cards(current_page_id)

# 카드 툴바 (버튼 3개 가로)
bt1, bt2, bt3 = st.columns(3)
with bt1:
    if st.button("💾 저장", key="btn_save_cards"):
        for card_id, title, content in cards:
            new_title = st.session_state.get(f"title_{card_id}", title)
            new_content = st.session_state.get(f"content_{card_id}", content)
            update_card(card_id, new_title, new_content)
        st.success("모든 카드가 저장되었습니다.")
        st.experimental_rerun()

with bt2:
    if st.button("＋ 카드 추가", key="btn_add_card"):
        add_card(current_page_id)
        st.experimental_rerun()

with bt3:
    if st.button("🗑 카드 삭제", key="btn_toggle_delete_card"):
        st.session_state["card_delete_mode"] = not st.session_state["card_delete_mode"]

# 카드 삭제 모드일 때만 제목 입력 UI 표시
if st.session_state["card_delete_mode"]:
    st.info("삭제할 카드의 제목을 입력한 뒤 '카드 삭제 실행'을 눌러주세요.")
    delete_title = st.text_input(
        "삭제할 카드 제목",
        key="delete_title_input",
        placeholder="예: 카드1",
    )
    if st.button("카드 삭제 실행", key="btn_do_delete_card"):
        if delete_title.strip():
            ok = delete_card_by_title(current_page_id, delete_title.strip())
            if ok:
                st.success(f"'{delete_title}' 카드가 삭제되었습니다.")
            else:
                st.warning(f"'{delete_title}' 제목의 카드를 찾을 수 없습니다.")
        else:
            st.warning("삭제할 카드 제목을 입력해주세요.")
        st.experimental_rerun()

# ---------------------------
# 카드 렌더링 (Expander: 닫힌 상태에서 시작)
# ---------------------------
cards = get_cards(current_page_id)  # 삭제/추가 후 다시 읽기

for card_id, title, content in cards:
    header = title if title else "제목 없음"
    # 항상 닫힌 상태에서 시작
    with st.expander(header, expanded=False):
        # 제목 편집용 텍스트 필드 (일반 굵기)
        st.text_input(
            "",
            value=title,
            key=f"title_{card_id}",
            label_visibility="collapsed",
            placeholder="제목 입력",
        )

        # 내용
        st.text_area(
            "",
            value=content,
            height=110,
            key=f"content_{card_id}",
            label_visibility="collapsed",
            placeholder="내용을 입력하세요",
        )
    # separator 제거 – 카드 사이에 선 없음

# ---------------------------
# 맨 위로 이동 버튼
# ---------------------------
st.markdown("---")
if st.button("맨 위로 이동", key="btn_scroll_top"):
    # rerun 되면서 자연스럽게 최상단으로 이동
    st.experimental_rerun()
