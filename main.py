import streamlit as st
import sqlite3
from streamlit_option_menu import option_menu

st.set_page_config(page_title="MemoKing", layout="wide")


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


st.markdown(
    """
<style>
[data-testid="stAppViewContainer"] {
    background-color: #f4f5f7;
}

.stVerticalBlock {
    gap: 0.25rem !important;
}

.stTextInput label, .stTextArea label {
    display: none !important;
}

.stTextInput input, .stTextArea textarea {
    border-radius: 10px !important;
    border: 1px solid #cfd3de !important;
    color: #222 !important;
}

.stTextInput input {
    background-color: #f4f5f7 !important;
    font-weight: 400 !important;
    font-size: 0.95rem !important;
}

.stTextArea textarea {
    min-height: 110px !important;
    font-size: 0.95rem !important;
    background-color: #ffffff !important;
    color: #222 !important;
    border-radius: 10px !important;
    border: 1px solid #cfd3de !important;
}

.stButton button {
    padding: 0.18rem 0.6rem !important;
    font-size: 0.80rem !important;
    border-radius: 8px !important;
}

details > summary {
    font-weight: 700 !important;
    color: #222 !important;
}

hr {
    margin-top: 0.45rem !important;
    margin-bottom: 0.45rem !important;
}
</style>
""",
    unsafe_allow_html=True,
)

if "card_toolbar_last" not in st.session_state:
    st.session_state["card_toolbar_last"] = "-"
if "page_toolbar_last" not in st.session_state:
    st.session_state["page_toolbar_last"] = "-"
if "renaming_page" not in st.session_state:
    st.session_state["renaming_page"] = False
if "rename_temp" not in st.session_state:
    st.session_state["rename_temp"] = ""
if "confirm_delete_page" not in st.session_state:
    st.session_state["confirm_delete_page"] = False
if "reset_page_toolbar" not in st.session_state:
    st.session_state["reset_page_toolbar"] = False

if st.session_state.get("reset_page_toolbar", False):
    st.session_state["page_toolbar"] = "-"
    st.session_state["reset_page_toolbar"] = False

with st.sidebar:
    pages = get_pages()
    if not pages:
        add_page("아이디어")
        pages = get_pages()

    page_ids = [p[0] for p in pages]
    page_titles = [p[1] for p in pages]

    current_index = 0
    if (
        "current_page_id" in st.session_state
        and st.session_state["current_page_id"] in page_ids
    ):
        current_index = page_ids.index(st.session_state["current_page_id"])

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

    st.markdown(
        "<div style='margin-top:0.6rem;'></div>",
        unsafe_allow_html=True,
    )

    st.radio(
        "",
        ["-", "➕", "🗑", "✏️"],
        key="page_toolbar",
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown(
        "<div style='margin-bottom:0.6rem;'></div>",
        unsafe_allow_html=True,
    )

    page_action = st.session_state.get("page_toolbar", "-")

    if page_action == "➕" and st.session_state["page_toolbar_last"] != "➕":
        add_page("새 페이지")
        st.session_state["page_toolbar_last"] = "➕"
        st.session_state["confirm_delete_page"] = False
        st.rerun()

    elif page_action == "🗑" and st.session_state["page_toolbar_last"] != "🗑":
        st.session_state["page_toolbar_last"] = "🗑"
        st.session_state["confirm_delete_page"] = True

    else:
        st.session_state["page_toolbar_last"] = page_action
        if page_action != "🗑":
            st.session_state["confirm_delete_page"] = False

    if page_action == "✏️":
        st.session_state["renaming_page"] = True
        st.session_state["rename_temp"] = choice

    if st.session_state["confirm_delete_page"]:
        st.warning("페이지를 삭제하시겠습니까?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("삭제", key="confirm_page_delete"):
                delete_page(current_page_id)
                st.session_state["confirm_delete_page"] = False
                st.session_state["reset_page_toolbar"] = True
                st.rerun()
        with c2:
            if st.button("취소", key="cancel_page_delete"):
                st.session_state["confirm_delete_page"] = False
                st.session_state["reset_page_toolbar"] = True
                st.rerun()

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
                st.session_state["reset_page_toolbar"] = True
                st.rerun()
        with c2:
            if st.button("취소", key="rename_cancel"):
                st.session_state["renaming_page"] = False
                st.session_state["reset_page_toolbar"] = True
                st.rerun()

top_left, top_right = st.columns([3, 1])

with top_left:
    st.markdown(
        f"<h4 style='margin-bottom:0.2rem;'>{choice}</h4>",
        unsafe_allow_html=True,
    )

with top_right:
    st.markdown(
        "<h2 style='text-align:right; margin-bottom:0.2rem;'>MemoKing</h2>",
        unsafe_allow_html=True,
    )

st.markdown(
    "<div style='margin:0.8rem 0;'></div>",
    unsafe_allow_html=True,
)

cards = get_cards(current_page_id)
if not cards:
    add_card(current_page_id)
    cards = get_cards(current_page_id)

st.radio(
    "",
    ["-", "💾 저장", "＋ 카드 추가", "🗑 카드 삭제"],
    key="card_toolbar",
    horizontal=True,
    label_visibility="collapsed",
)
card_action = st.session_state.get("card_toolbar", "-")

for card_id, title, content in cards:
    header = title if title else "제목 없음"
    with st.expander(header, expanded=False):
        st.text_input(
            "",
            value=title,
            key=f"title_{card_id}",
            label_visibility="collapsed",
            placeholder="제목 입력",
        )

        st.text_area(
            "",
            value=content,
            height=110,
            key=f"content_{card_id}",
            label_visibility="collapsed",
            placeholder="내용을 입력하세요",
        )

if card_action == "💾 저장" and st.session_state["card_toolbar_last"] != "💾 저장":
    for card_id, title, content in cards:
        new_title = st.session_state.get(f"title_{card_id}", title)
        new_content = st.session_state.get(f"content_{card_id}", content)
        update_card(card_id, new_title, new_content)

    st.session_state["card_toolbar_last"] = "💾 저장"
    st.success("모든 카드가 저장되었습니다.")
    st.rerun()

elif (
    card_action == "＋ 카드 추가"
    and st.session_state["card_toolbar_last"] != "＋ 카드 추가"
):
    add_card(current_page_id)
    st.session_state["card_toolbar_last"] = "＋ 카드 추가"
    st.rerun()

else:
    st.session_state["card_toolbar_last"] = card_action

if card_action == "🗑 카드 삭제":
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
        st.rerun()
