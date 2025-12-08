import streamlit as st
import sqlite3
from streamlit_option_menu import option_menu

st.set_page_config(page_title="MemoKing", layout="wide")

# -------------------------------------------------------------------------
# DB 초기화 (SQLite)  + color_level 컬럼 보정
# -------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect("memo.db")
    cur = conn.cursor()

    # 페이지 테이블
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL
        )
        """
    )

    # 카드 테이블
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

    # color_level 컬럼이 없으면 추가
    cur.execute("PRAGMA table_info(cards)")
    cols = [row[1] for row in cur.fetchall()]
    if "color_level" not in cols:
        cur.execute("ALTER TABLE cards ADD COLUMN color_level INTEGER DEFAULT 0")

    conn.commit()
    return conn


db = init_db()

# -------------------------------------------------------------------------
# 페이지 / 카드 관련 함수
# -------------------------------------------------------------------------
def get_pages():
    cur = db.cursor()
    cur.execute("SELECT id, title FROM pages ORDER BY id ASC")
    return cur.fetchall()


def add_page(title: str = "새 페이지"):
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
        """
        SELECT id, title, content, COALESCE(color_level,0)
        FROM cards
        WHERE page_id=?
        ORDER BY id ASC
        """,
        (page_id,),
    )
    return cur.fetchall()


def add_card(page_id: int):
    cur = db.cursor()
    cur.execute(
        """
        INSERT INTO cards(page_id, title, content, color_level)
        VALUES (?, ?, ?, 0)
        """,
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


def set_card_color(card_id: int, level: int):
    cur = db.cursor()
    cur.execute(
        "UPDATE cards SET color_level=? WHERE id=?",
        (level, card_id),
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


# -------------------------------------------------------------------------
# 공통 CSS
# -------------------------------------------------------------------------
st.markdown(
    """
<style>
/* 전체 배경 톤 */
[data-testid="stAppViewContainer"] {
    background-color: #f4f5f7;
}

/* 세로 블럭 간격 줄이기 */
.stVerticalBlock {
    gap: 0.25rem !important;
}

/* 입력 라벨 숨기기 */
.stTextInput label, .stTextArea label {
    display: none !important;
}

/* 입력/에디터 공통 스타일 */
.stTextInput input, .stTextArea textarea {
    background-color: #f4f5f7 !important;
    border-radius: 10px !important;
    border: 1px solid #cfd3de !important;
    color: #222 !important;
}

/* 제목 input 은 일반체 */
.stTextInput input {
    font-weight: 400 !important;
    font-size: 0.95rem !important;
}

/* textarea 높이 */
.stTextArea textarea {
    min-height: 110px !important;
    font-size: 0.95rem !important;
}

/* 버튼 작게 */
.stButton button {
    padding: 0.15rem 0.5rem !important;
    font-size: 0.80rem !important;
    border-radius: 8px !important;
}

/* Expander 헤더 텍스트 Bold */
details > summary {
    font-weight: 700 !important;
    color: #222 !important;
}

/* 구분선 여백 */
hr {
    margin-top: 0.45rem !important;
    margin-bottom: 0.45rem !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------------
# 세션 상태 기본값
# -------------------------------------------------------------------------
if "current_page_id" not in st.session_state:
    st.session_state["current_page_id"] = None
if "confirm_delete_page" not in st.session_state:
    st.session_state["confirm_delete_page"] = False
if "renaming_page" not in st.session_state:
    st.session_state["renaming_page"] = False
if "rename_temp" not in st.session_state:
    st.session_state["rename_temp"] = ""
if "card_delete_mode" not in st.session_state:
    st.session_state["card_delete_mode"] = False
if "color_mode" not in st.session_state:
    st.session_state["color_mode"] = False

# -------------------------------------------------------------------------
# 사이드바 : 페이지 리스트 + 가로 버튼 3개
# -------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 📝 memo king")

    pages = get_pages()
    if not pages:
        add_page("아이디어")
        pages = get_pages()

    page_ids = [p[0] for p in pages]
    page_titles = [p[1] for p in pages]

    # 현재 선택된 페이지 인덱스
    current_index = 0
    if (
        st.session_state["current_page_id"] in page_ids
    ):
        current_index = page_ids.index(st.session_state["current_page_id"])

    # 페이지 리스트 선택
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

    # 가로형 버튼 3개 (추가 / 삭제 / 이름 변경)
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("➕", help="새 페이지 추가"):
            add_page("새 페이지")
            st.experimental_rerun()
    with b2:
        if st.button("🗑", help="현재 페이지 삭제"):
            st.session_state["confirm_delete_page"] = True
    with b3:
        if st.button("✏️", help="페이지 이름 변경"):
            st.session_state["renaming_page"] = True
            st.session_state["rename_temp"] = choice

    # 페이지 삭제 확인
    if st.session_state["confirm_delete_page"]:
        st.warning("페이지를 삭제하시겠습니까?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("삭제", key="confirm_page_delete"):
                delete_page(current_page_id)
                st.session_state["confirm_delete_page"] = False
                st.experimental_rerun()
        with c2:
            if st.button("취소", key="cancel_page_delete"):
                st.session_state["confirm_delete_page"] = False
                st.experimental_rerun()

    # 페이지 이름 변경
    if st.session_state["renaming_page"]:
        new_title = st.text_input(
            "새 페이지 이름",
            value=st.session_state["rename_temp"],
            key="rename_input",
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("이름 변경", key="rename_save"):
                rename_page(current_page_id, new_title.strip() or "제목 없음")
                st.session_state["renaming_page"] = False
                st.experimental_rerun()
        with c2:
            if st.button("취소", key="rename_cancel"):
                st.session_state["renaming_page"] = False
                st.experimental_rerun()

# -------------------------------------------------------------------------
# 본문 상단 : 페이지 제목 + 카드 툴바
# -------------------------------------------------------------------------
st.markdown(f"## {choice}")
st.markdown("---")

cards = get_cards(current_page_id)
if not cards:
    add_card(current_page_id)
    cards = get_cards(current_page_id)

# 카드 툴바 : 저장 버튼 + 삭제 모드 체크 + 색상 모드 체크
tb1, tb2, tb3 = st.columns(3)
with tb1:
    if st.button("💾 저장", key="save_all_cards"):
        for card_id, title, content, color_level in cards:
            new_title = st.session_state.get(f"title_{card_id}", title)
            new_content = st.session_state.get(f"content_{card_id}", content)
            update_card(card_id, new_title, new_content)
        st.success("모든 카드가 저장되었습니다.")
        st.experimental_rerun()

with tb2:
    st.session_state["card_delete_mode"] = st.checkbox(
        "🗑 카드 삭제 모드",
        value=st.session_state["card_delete_mode"],
        key="chk_delete_mode",
    )

with tb3:
    st.session_state["color_mode"] = st.checkbox(
        "🎨 색상 모드",
        value=st.session_state["color_mode"],
        key="chk_color_mode",
    )

# 카드 삭제 모드 UI
if st.session_state["card_delete_mode"]:
    st.info("삭제할 카드의 제목을 입력한 뒤 '카드 삭제 실행'을 눌러주세요.")
    delete_title = st.text_input(
        "삭제할 카드 제목",
        key="delete_title_input",
        placeholder="예: 카드1",
    )
    if st.button("카드 삭제 실행"):
        if delete_title.strip():
            ok = delete_card_by_title(current_page_id, delete_title.strip())
            if ok:
                st.success(f"'{delete_title}' 카드가 삭제되었습니다.")
            else:
                st.warning(f"'{delete_title}' 제목의 카드를 찾을 수 없습니다.")
        else:
            st.warning("삭제할 카드 제목을 입력해주세요.")
        st.experimental_rerun()

# -------------------------------------------------------------------------
# 카드 렌더링 (Expander : 기본 닫힘, 헤더 Bold, 내부 제목은 일반체)
# -------------------------------------------------------------------------
COLOR_MAP = {
    0: None,
    1: "#FEFBE1",
    2: "#FDE88A",
}

cards = get_cards(current_page_id)  # 변경이 있을 수 있으니 다시 읽기

for card_id, title, content, color_level in cards:
    header = title if title else "제목 없음"

    with st.expander(header, expanded=False):  # 항상 닫힌 상태에서 시작
        # 색상 모드일 때만 색상 변경 버튼 노출
        if st.session_state["color_mode"]:
            col_bar, col_btn = st.columns([6, 2])
            with col_bar:
                color = COLOR_MAP.get(color_level)
                if color:
                    st.markdown(
                        f'<div style="height:6px;border-radius:4px;'
                        f'background:{color};margin-bottom:6px;"></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div style="height:6px;border-radius:4px;'
                        'background:transparent;margin-bottom:6px;"></div>',
                        unsafe_allow_html=True,
                    )
            with col_btn:
                if st.button("색상 변경", key=f"color_{card_id}"):
                    next_level = (color_level + 1) % 3  # 0→1→2→0
                    set_card_color(card_id, next_level)
                    st.experimental_rerun()
        else:
            # 색상 모드가 아니어도, 현재 색상은 표시해 주기
            color = COLOR_MAP.get(color_level)
            if color:
                st.markdown(
                    f'<div style="height:6px;border-radius:4px;'
                    f'background:{color};margin-bottom:6px;"></div>',
                    unsafe_allow_html=True,
                )

        # 제목 입력 (일반체)
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

# -------------------------------------------------------------------------
# 맨 위로 이동 버튼
# -------------------------------------------------------------------------
st.markdown("---")
if st.button("맨 위로 이동", key="btn_scroll_top"):
    st.experimental_rerun()
