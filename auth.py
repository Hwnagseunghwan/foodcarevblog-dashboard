"""
Cle Dashboard 인증 모듈 (Supabase Auth)
"""
import streamlit as st
from supabase import create_client


def _get_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)


def require_login():
    """로그인 확인. 미로그인 시 로그인 폼 표시 후 실행 중단."""
    if st.session_state.get("user"):
        return
    _show_login()
    st.stop()


def show_user_sidebar():
    """사이드바 하단에 로그인 사용자 이메일 + 로그아웃 버튼 표시"""
    if not st.session_state.get("user"):
        return
    st.sidebar.divider()
    email = st.session_state["user"].get("email", "")
    st.sidebar.caption(f"👤 {email}")
    if st.sidebar.button("로그아웃", key="logout_btn"):
        _logout()


def _show_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            '<p style="font-size:28px; font-weight:900; font-family:\'Apple SD Gothic Neo\', \'Noto Sans KR\', \'Malgun Gothic\', sans-serif;">Cle Dashboard</p>',
            unsafe_allow_html=True
        )
        st.markdown("접근 권한이 필요합니다. 계정이 없으면 관리자에게 초대를 요청하세요.")
        st.divider()
        email = st.text_input("이메일", key="login_email")
        password = st.text_input("비밀번호", type="password", key="login_password")
        if st.button("로그인", use_container_width=True, type="primary", key="login_btn"):
            if email and password:
                _do_login(email, password)
            else:
                st.warning("이메일과 비밀번호를 입력해주세요.")


def _do_login(email, password):
    try:
        client = _get_client()
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state["user"] = {
            "email": res.user.email,
            "id": str(res.user.id),
        }
        st.session_state["access_token"] = res.session.access_token
        st.rerun()
    except Exception:
        st.error("이메일 또는 비밀번호가 올바르지 않습니다.")


def _logout():
    try:
        _get_client().auth.sign_out()
    except Exception:
        pass
    st.session_state.pop("user", None)
    st.session_state.pop("access_token", None)
    st.rerun()
