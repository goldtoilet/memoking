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
# PAGE LOAD
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


def get_cards(page_id):
    cur = db.cursor()
    cur.execute("SELECT id, title, content FROM cards WHERE page_id=? ORDER BY id ASC", (page_id,))
    return cur.fetchall()


def add_card(page_id):
    cur = db.cursor()
    cur.execute("INSERT INTO cards(page_id, title, content) VALUES (?, ?, ?)",
                (page_id, "제목 없음", ""))
    db.commit()


def update_card(card_id, title, content):
    cur = db.cursor()
    cur.execute("UPDATE cards SET title=?, content=? WHERE id=?",
                (title, content, card_id))
    db.commit()


def delete_card(card_id):
    cur = db.cursor()
    cur.execute("DELETE FROM cards WHERE id=?", (card_id,))
    db.commit()


# ---------------------------
# 사이드바 (Notion Navigation Style)
# ---------------------------
with st.sidebar:

    st.markdown("### ✨ MemoKing")
    st.markdown("---")

    pages = get_pages()

    # 페이지가 없다면 하나 생성
    if not pages:
        new_page_id = add_page("아이디어")
        pages = get_pages()

    page_titles = [p[1] for p in pages]
    page_ids = [p[0] for p in pages]

    selected = option_menu(
        None,
        page_titles,
        icons=["journal-text"] * len(page_titles),
        menu_icon="menu-app",
        default_index=0,
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
            }
        }
    )

    # 현재 페이지 id
    current_page_id = page_ids[page_titles.index(selected)]

    st.markdown("---")

    # 페이지 추가/삭제 버튼
    colA, colB = st.columns(2)
    with colA:
        if st.button("➕ 페이지 추가"):
            add_page("새 페이지")
            st.rerun()

    with colB:
        if st.button("🗑 페이지 삭제"):
            delete_page(current_page_id)
            st.rerun()


# ---------------------------
# 본문 UI 시작
# ---------------------------
st.markdown(f"## {selected}")
st.markdown("---")

cards = get_cards(current_page_id)

# 카드가 없으면 자동 생성
if not cards:
    add_card(current_page_id)
    cards = get_cards(current_page_id)


# ---------------------------
# 카드 렌더링
# ---------------------------
for card in cards:
    card_id, title, content = card

    with st.container():
        st.markdown(
            """
            <div style='background-color:#f0f2f6; padding:15px; border-radius:10px;'>
            """,
            unsafe_allow_html=True
        )

        new_title = st.text_input(" ", value=title, label_visibility="collapsed", key=f"title_{card_id}")
        new_content = st.text_area(" ", value=content, height=120,
                                   label_visibility="collapsed", key=f"content_{card_id}")

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("💾 저장", key=f"save_{card_id}"):
                update_card(card_id, new_title, new_content)
                st.rerun()
        with col2:
            if st.button("➕ 추가", key=f"add_{card_id}"):
                add_card(current_page_id)
                st.rerun()
        with col3:
            if st.button("🗑 삭제", key=f"delete_{card_id}"):
                delete_card(card_id)
                st.rerun()

        st.markdown("</div><br>", unsafe_allow_html=True)
