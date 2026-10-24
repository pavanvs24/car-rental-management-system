from services import GetPassHash
import streamlit as st
import bcrypt as bt

if "p_in" not in st.session_state:
    st.session_state.p_in = ""
if "staff_id" not in st.session_state:
    st.session_state.staff_id = ""

def checkpass():
    PH = GetPassHash("staff", st.session_state.staff_id)
    if PH == None:
        st.info("No account with that staff id was found, please register or try again")

    elif bt.checkpw(st.session_state.p_in.encode("utf-8"), PH.encode("utf-8")):
        st.success("Log-In sucsess")

    else:
        st.error("Log-In failed, try again")
        st.session_state.p_in = ""

st.title(":red[Login]")

st.text_input(
    "Enter Staff ID: ",
    key = "staff_id"
)

st.text_input(
    "Enter Password: ",
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
#    st.switch_page("pages/4_StaffRegistration.py")"""