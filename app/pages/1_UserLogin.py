from services import GetPassHash
import streamlit as st
import bcrypt as bt
import time as te

if "p_in" not in st.session_state:
    st.session_state.p_in = ""
if "customer_email" not in st.session_state:
    st.session_state.customer_email = ""
if "auth" not in st.session_state:
    st.session_state.auth = False


st.set_page_config(
    "Login",
    layout = 'centered'
)

def checkpass():
    PH = GetPassHash("customer", st.session_state.customer_email)
    if PH == None:
        st.info("No account with the email id was found, please register or try again")

    elif bt.checkpw(st.session_state.p_in.encode("utf-8"), PH.encode("utf-8")):
        st.success("Log-In sucsess")
        te.sleep(0.5)
        st.session_state.p_in = ""
        st.session_state.auth = True
        st.switch_page("pages/5_UserLanding.py")

    else:
        st.session_state.p_in = ""
        st.session_state.auth = False
        st.error("Log-In failed, try again")

st.title(":red[Log] In")

st.text_input(
    "Enter Customer Email: ",
    key = "customer_email"
)

st.text_input(
    "Enter Password: ",
    max_chars = 36,
    type = 'password',
    key = "p_in"
)

c1, c2 = st.columns(2)
c1.button(
    "Login",
    width = 'stretch',
    type = 'primary',
    on_click=checkpass  
)
#Not needed
#if c2.button(
#    "Register",
#    type = 'secondary',
#    width = 'stretch'
#):
#    st.switch_page("pages/3_UserRegistration.py")"""