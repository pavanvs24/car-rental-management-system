import streamlit as st

st.title(":red[Car Rental] Services", text_alignment="center",)

st.html("<br> <br>")

if st.button(
    "Login as User",
    type='primary',
    width=990
):
    st.switch_page("pages/1_UserLogin.py")
    
if st.button(
    "Login as Staff",
    type = 'primary',
    width=990
):
    on_click=st.switch_page("pages/2_StaffLogin.py")

