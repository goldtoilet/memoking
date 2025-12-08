import streamlit as st
import sqlite3
from streamlit_option_menu import option_menu

st.set_page_config(page_title="MemoKing", layout="wide")

# ---------------------------
# DATABASE 초기화
# ---------------------------
def init_db():
    conn = sqlite3.connect("memo.db")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cards(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER,
            title TEXT,
            content TEXT,
            FOREIGN KEY(page_id) REFERENCES pages(id)
        )
    """)

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


def delete_page(page_id):
    cur = db.cursor()
    cur.execute("DELETE FROM cards WHERE page_id=?", (page_id,))
    cur.execute("DELETE FROM pages WHERE id=?", (page_id,))
    db.commit()


def rename_page(page_id, new_title):
    cur = db.cursor()
    cur.execute("UPDATE pages SET title=? WHERE id=?", (new_title, page_id))
    db.commit()


def get_cards(page_id):
    cur = db.cursor()
    cur.execute("SELECT id, title, content FROM cards WHERE page_id=? ORDER BY id ASC", (page_id,))
    return cur.fetchall()


def add_card(page_id):
    cur = db.cursor()
    cur.execute(
        "INSERT INTO cards(page_id, title, content) VALUES (?, ?, ?)",
        (page_id, "제목 없음", ""),
    )
    db.commit()


def update_card(card_id, title, content):
    cur = db.cursor()
    cur.execute("UPDATE cards SET title=?, content=? WHERE id=?", (title, content, card_id))
    db.commit()


def delete_card(card_id):
    cur = db.cursor()
    cur.execute("DELETE FROM cards WHERE id=?", (card_id,))
    db.commit()


# ---------------------------
# 공통 스타일 (배경/입력필드/버튼)
# ---------------------------
st.markdown(
    """
<style>
/* 전체 배경 톤 */
[data-testid="stAppViewContainer"] {
    background-color: #f4f5f7;
}

/* 라벨 영역 숨기기 - 위쪽 쓸모없는 공간 제거 */
.stTextInput label, .stTextArea label {
    display: none !important;
}

/* 입력/에디터 배경을 전체 배경과 같게 */
.stTextInput input, .stTextArea textarea {
    background-color: #f4f5f7 !important;
    border-radius: 10px !important;
    border: 1px solid #cfd3de !important;
    color: #222 !important;
}

/* 카드 제목은 볼드체 */
.stTextInput input {
    font-weight: 700 !important;
}

/* textarea 높이 조금 줄이기 */
.stTextArea textarea {
    min-height: 110px !important;
    font-size: 0.95rem !important;
}

/* 기본 버튼 조금 작게 */
.stButton button {
    padding: 0.35rem 0.8rem;
    font-size: 0.85rem;
}

/* 버튼들을 항상 가로 한 줄에 배치하기 위한 공통 클래스 */
.btn-row {
    display: block;
    margin-top: 0.4rem;
}

/* btn-row 안에 있는 모든 st.button 컨테이너를 inline-block 으로 */
.btn-row [data-testid="stButton"] {
    display: inline-block !important;
    margin-right: 0.4rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# 페이지 제목 수정 상태
if "renaming_page" not in st.session_state:
    st.session_state["renaming_page"] = False
if "rename_temp" not in st.session_state:
    st.session_state["rename_temp"] = ""


# ---------------------------
# 사이드바 (Notion Navigation Style)
# ---------------------------
with st.sidebar:

    st.markdown("### ✨ MemoKing")
    st.markdown("---")

    pages = get_pages()

    # 페이지가 없다면 하나 생성
    if not pages:
        add_page("아이디어")
        pages = get_pages()

    page_titles = [p[1] for p in pages]
    page_ids = [p[0] for p in pages]

    # 현재 선택 페이지 인덱스
    current_index = 0
    if "current_page_id" in st.session_state and st.session_state["current_page_id"] in page_ids:
        current_index = page_ids.index(st.session_state["current_page_id"])

    choice = option_menu(
        None,
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
                "color": "black"
            },
        },
    )

    current_page_id = page_ids[page_titles.index(choice)]
    st.session_state["current_page_id"] = current_page_id

    st.markdown("---")

    # 사이드바 하단 버튼 3개 (CSS로 가로 배치)
    btn_sidebar = st.container()
    with btn_sidebar:
        st.markdown('<div class="btn-row">', unsafe_allow_html=True)
        add_page_clicked = st.button("➕", help="페이지 추가", key="btn_add_page")
        delete_page_clicked = st.button("🗑", help="페이지 삭제", key="btn_del_page")
        rename_page_clicked = st.button("✏️", help="페이지 이름 변경", key="btn_rename_page")
        st.markdown("</div>", unsafe_allow_html=True)

    if add_page_clicked:
        add_page("새 페이지")
        st.rerun()

    if delete_page_clicked:
        delete_page(current_page_id)
        st.rerun()

    if rename_page_clicked:
        st.session_state["renaming_page"] = True
        st.session_state["rename_temp"] = choice

    # 페이지 이름 수정 UI
    if st.session_state["renaming_page"]:
        st.markdown("------")
        new_title = st.text_input(
            "",
            value=st.session_state["rename_temp"],
            key="rename_input",
            label_visibility="collapsed",
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("저장", key="rename_save"):
                rename_page(current_page_id, new_title.strip() or "제목 없음")
                st.session_state["renaming_page"] = False
                st.rerun()
        with c2:
            if st.button("취소", key="rename_cancel"):
                st.session_state["renaming_page"] = False
                st.rerun()


# ---------------------------
# 본문 UI
# ---------------------------
st.markdown(f"## {choice}")
st.markdown("---")

cards = get_cards(current_page_id)

# 카드가 없으면 자동 생성
if not cards:
    add_card(current_page_id)
    cards = get_cards(current_page_id)

# ---------------------------
# 카드 렌더링
# ---------------------------
for idx, card in enumerate(cards):
    card_id, title, content = card

    # 카드 제목
    new_title = st.text_input(
        "",
        value=title,
        key=f"title_{card_id}",
        label_visibility="collapsed",
        placeholder="제목 입력",
    )

    # 카드 내용
    new_content = st.text_area(
        "",
        value=content,
        height=110,
        key=f"content_{card_id}",
        label_visibility="collapsed",
        placeholder="내용을 입력하세요",
    )

    # 카드 아래 버튼 3개를 CSS로 가로 한 줄에 배치
    btn_row = st.container()
    with btn_row:
        st.markdown('<div class="btn-row">', unsafe_allow_html=True)
        save_clicked = st.button("💾 저장", key=f"save_{card_id}")
        add_clicked = st.button("＋ 추가", key=f"add_{card_id}")
        delete_clicked = st.button("🗑 삭제", key=f"delete_{card_id}")
        st.markdown("</div>", unsafe_allow_html=True)

    # 카드와 다음 카드 사이 구분선
    st.markdown("---")

    # 버튼 동작
    if save_clicked:
        update_card(card_id, new_title, new_content)
        st.rerun()
    if add_clicked:
        add_card(current_page_id)
        st.rerun()
    if delete_clicked:
        delete_card(card_id)
        st.rerun()
