import streamlit as st
import sqlite3
from streamlit_option_menu import option_menu

st.set_page_config(page_title="MemoKing", layout="wide")

# ============================================================
# 로그인 정보: secrets.toml에서 불러오기
# ============================================================
VALID_ID = st.secrets["auth"]["id"]
VALID_PW = st.secrets["auth"]["pw"]

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False


def login_view():
    st.title("🔒 MemoKing 로그인")
    st.write("아이디와 비밀번호를 입력하세요.")

    user_id = st.text_input("아이디", key="login_id")
    user_pw = st.text_input("비밀번호", type="password", key="login_pw")

    if st.button("로그인"):
        if user_id == VALID_ID and user_pw == VALID_PW:
            st.session_state["logged_in"] = True
            st.success("로그인 성공!")
            st.rerun()
        else:
            st.error("아이디 또는 비밀번호가 올바르지 않습니다.")


# 로그인 안 되어 있으면 여기서 종료
if not st.session_state["logged_in"]:
    login_view()
    st.stop()


# ============================================================
# DB 초기화 (SQLite)
# ============================================================
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

# ============================================================
# PAGE / CARD 함수
# ============================================================
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


# ============================================================
# 공통 스타일 (CSS)
# ============================================================
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

/* 카드 제목 인풋은 일반체(헤더만 Bold) */
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

# ============================================================
# 세션 상태 기본값 + page_toolbar 리셋 플래그
# ============================================================
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

# 이전 러닝에서 리셋 플래그가 설정돼 있으면
# radio 생성 전에 page_toolbar 값을 "-"로 초기화
if st.session_state.get("reset_page_toolbar", False):
    st.session_state["page_toolbar"] = "-"
    st.session_state["reset_page_toolbar"] = False

# ============================================================
# 사이드바 : option_menu + 페이지 툴바 (radio) + 로그아웃
# ============================================================
with st.sidebar:
    st.markdown("### memo king")
    if st.button("로그아웃"):
        st.session_state["logged_in"] = False
        st.rerun()

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

    # 페이지 리스트 (이전 스타일)
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

    # 페이지용 툴바 (가로형 라디오, 아이콘 3개)
    st.radio(
        "",
        ["-", "➕", "🗑", "✏️"],
        key="page_toolbar",
        horizontal=True,
        label_visibility="collapsed",
    )
    page_action = st.session_state.get("page_toolbar", "-")

    # 페이지 추가
    if page_action == "➕" and st.session_state["page_toolbar_last"] != "➕":
        add_page("새 페이지")
        st.session_state["page_toolbar_last"] = "➕"
        st.session_state["confirm_delete_page"] = False
        st.rerun()

    # 페이지 삭제(확인 모드 진입만)
    elif page_action == "🗑" and st.session_state["page_toolbar_last"] != "🗑":
        st.session_state["page_toolbar_last"] = "🗑"
        st.session_state["confirm_delete_page"] = True

    else:
        # 다른 상태는 last 값만 갱신
        st.session_state["page_toolbar_last"] = page_action
        if page_action != "🗑":
            st.session_state["confirm_delete_page"] = False

    # 이름 변경 모드 진입
    if page_action == "✏️":
        st.session_state["renaming_page"] = True
        st.session_state["rename_temp"] = choice

    # 페이지 삭제 확인 UI
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

    # 페이지 이름 변경 UI
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

# ============================================================
# 본문 상단 : 페이지 제목 + 카드 툴바(radio)
# ============================================================
st.markdown(f"## {choice}")
st.markdown("---")

# 카드 목록
cards = get_cards(current_page_id)
if not cards:
    add_card(current_page_id)
    cards = get_cards(current_page_id)

# 카드 툴바 (저장 / 추가 / 삭제)
st.radio(
    "",
    ["-", "💾 저장", "＋ 카드 추가", "🗑 카드 삭제"],
    key="card_toolbar",
    horizontal=True,
    label_visibility="collapsed",
)
card_action = st.session_state.get("card_toolbar", "-")

# ============================================================
# 카드 렌더링 (Expander: 제목 = 헤더, 내부에 제목/내용)
#  - 항상 닫힌 상태(expanded=False)에서 시작
# ============================================================
for card_id, title, content in cards:
    header = title if title else "제목 없음"
    with st.expander(header, expanded=False):  # 기본 닫힌 상태
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

# ============================================================
# 카드 툴바 동작 처리
# ============================================================
# 1) 전체 저장 (한 번만 실행)
if card_action == "💾 저장" and st.session_state["card_toolbar_last"] != "💾 저장":
    for card_id, title, content in cards:
        new_title = st.session_state.get(f"title_{card_id}", title)
        new_content = st.session_state.get(f"content_{card_id}", content)
        update_card(card_id, new_title, new_content)

    st.session_state["card_toolbar_last"] = "💾 저장"
    st.success("모든 카드가 저장되었습니다.")
    st.rerun()

# 2) 카드 추가 (한 번만 실행)
elif (
    card_action == "＋ 카드 추가"
    and st.session_state["card_toolbar_last"] != "＋ 카드 추가"
):
    add_card(current_page_id)
    st.session_state["card_toolbar_last"] = "＋ 카드 추가"
    st.rerun()

else:
    # 다른 상태는 last 값만 갱신
    st.session_state["card_toolbar_last"] = card_action

# 3) 카드 삭제 모드
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
