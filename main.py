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
    cur.execute(
        "SELECT id, title, content FROM cards WHERE page_id=? ORDER BY id ASC",
        (page_id,),
    )
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
    cur.execute(
        "UPDATE cards SET title=?, content=? WHERE id=?",
        (title, content, card_id),
    )
    db.commit()


def delete_card(card_id):
    cur = db.cursor()
    cur.execute("DELETE FROM cards WHERE id=?", (card_id,))
    db.commit()


# ---------------------------
# 공통 스타일
# ---------------------------
st.markdown(
    """
<style>
/* 전체 배경 톤 */
[data-testid="stAppViewContainer"] {
    background-color: #f4f5f7;
}

/* 세로 블럭 간격 전체적으로 줄이기 (v-spacing) */
.stVerticalBlock {
    gap: 0.45rem !important;
}

/* 라벨 숨기기 – 위에 쓸모없는 빈 공간 제거 */
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

/* 카드 제목은 볼드체 */
.stTextInput input {
    font-weight: 700 !important;
}

/* textarea 높이 줄이기 */
.stTextArea textarea {
    min-height: 110px !important;
    font-size: 0.95rem !important;
}

/* 기본 버튼 조금 작게 */
.stButton button {
    padding: 0.32rem 0.75rem;
    font-size: 0.85rem;
}

/* ▼ 버튼 row: Streamlit이 모바일에서 column으로 바꾸는 걸 덮어씌우기 */

/* 이 wrapper 안에 있는 stHorizontalBlock 은 항상 가로 flex */
.btn-row-wrapper .stHorizontalBlock {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 0.3rem !important;
}

/* 각 column 은 auto-width, 여백 최소화 */
.btn-row-wrapper .stHorizontalBlock > div {
    flex: 0 0 auto !important;
    width: auto !important;
    padding: 0 !important;
    margin: 0 !important;
}

/* 버튼 자체는 왼쪽 정렬 */
.btn-row-wrapper .stButton {
    display: flex !important;
    justify-content: flex-start !important;
}

/* 카드와 카드 사이 구분선도 간격 줄이기 */
hr {
    margin-top: 0.6rem !important;
    margin-bottom: 0.6rem !important;
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
# 사이드바
# ---------------------------
with st.sidebar:

    st.markdown("### ✨ MemoKing")
    st.markdown("---")

    pages = get_pages()

    if not pages:
        add_page("아이디어")
        pages = get_pages()

    page_titles = [p[1] for p in pages]
    page_ids = [p[0] for p in pages]

    current_index = 0
    if (
        "current_page_id" in st.session_state
        and st.session_state["current_page_id"] in page_ids
    ):
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
                "color": "black",
            },
        },
    )

    current_page_id = page_ids[page_titles.index(choice)]
    st.session_state["current_page_id"] = current_page_id

    st.markdown("---")

    # ▼ 사이드바 하단 버튼 3개: wrapper + columns
    st.markdown('<div class="btn-row-wrapper">', unsafe_allow_html=True)
    colA, colB, colC = st.columns(3)
    with colA:
        add_page_clicked = st.button("➕", help="페이지 추가", key="btn_add_page")
    with colB:
        delete_page_clicked = st.button("🗑", help="페이지 삭제", key="btn_del_page")
    with colC:
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

if not cards:
    add_card(current_page_id)
    cards = get_cards(current_page_id)

# ---------------------------
# 카드 렌더링
# ---------------------------
for idx, card in enumerate(cards):
    card_id, title, content = card

    new_title = st.text_input(
        "",
        value=title,
        key=f"title_{card_id}",
        label_visibility="collapsed",
        placeholder="제목 입력",
    )

    new_content = st.text_area(
        "",
        value=content,
        height=110,
        key=f"content_{card_id}",
        label_visibility="collapsed",
        placeholder="내용을 입력하세요",
    )

    # ▼ 카드 아래 버튼 row
    st.markdown('<div class="btn-row-wrapper">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        save_clicked = st.button("💾 저장", key=f"save_{card_id}")
    with col2:
        add_clicked = st.button("＋ 추가", key=f"add_{card_id}")
    with col3:
        delete_clicked = st.button("🗑 삭제", key=f"delete_{card_id}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    if save_clicked:
        update_card(card_id, new_title, new_content)
        st.rerun()
    if add_clicked:
        add_card(current_page_id)
        st.rerun()
    if delete_clicked:
        delete_card(card_id)
        st.rerun()
