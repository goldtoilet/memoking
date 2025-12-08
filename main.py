import streamlit as st
import sqlite3
from streamlit_option_menu import option_menu

st.set_page_config(page_title="MemoKing", layout="wide")

# ============================================================
# 로그인 정보: secrets.toml에서 불러오기 (안전하게)
# ============================================================
auth_conf = st.secrets.get("auth", {})

VALID_ID = auth_conf.get("id")
VALID_PW = auth_conf.get("pw")

if not VALID_ID or not VALID_PW:
    st.error(
        "⚠️ 로그인 설정(auth.id / auth.pw)이 없습니다.\n\n"
        "Streamlit secrets 또는 .streamlit/secrets.toml 파일에\n"
        "[auth]\n"
        'id = "아이디"\n'
        'pw = "비밀번호"\n'
        "형식으로 설정해 주세요."
    )
    st.stop()

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
