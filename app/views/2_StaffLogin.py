import streamlit as st
import ui_helpers as uh

#==================================================

col_title, col_back = st.columns([10,1])

with col_title:

    st.title(":red[Log] In")

with col_back:

    if st.button(

        "",
        icon = ":material/arrow_back:",
        width = 'content'

    ):
            st.session_state["auth"] = "No_Auth"
            st.rerun()

#=====================================================

Staff_ID = st.text_input(
   
   "Enter Staff ID (Numbers only):",
    placeholder="e.g. 12345"
    
)

if Staff_ID and not Staff_ID.isdigit():

    st.error("Staff ID can only contain numbers.")

password = st.text_input(

    "Enter Password: ",
    type = 'password',
    key = "password_wk",
    max_chars = 36

)

login, register = st.columns(2)

with login:

    if st.button(

        "Login",
        icon = ":material/login:",
        width = 'stretch',
        type = 'primary',
        key = 'login'

    ):

        if not Staff_ID or not password:

            st.toast("Missing Details, Please enter and try again")

        elif uh.CheckPassword("staff", Staff_ID, password):

            st.toast("Login Successful!", duration = 'short')

            st.session_state["Staff_ID"] = int(Staff_ID)
            st.session_state["Staff_Name"] = uh.GetStaffName(int(Staff_ID))

            st.session_state["auth"] = "Admin"
            st.rerun()

        else:

            st.session_state["password_wk"] = ""
            st.error("Login Failed! Try again")

        
    

#Not needed
#if c2.button(

#    "Register",
#    type = 'secondary',
#    width = 'stretch'

#):
#    st.switch_page("views/4_StaffRegistration.py")"""