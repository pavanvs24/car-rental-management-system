import ui_helpers as uh
import streamlit as st

#===========================================================

st.set_page_config(

    layout = 'centered'

)

#===========================================================

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

cus_email = st.text_input(

    "Enter Your Email: ", 
    type = 'email',

)

password = st.text_input(

    "Enter Password: ",
    max_chars = 36,
    type = 'password',
    key = "password_wk"

)

c1, c2 = st.columns(2)

login, register = st.columns([1,1])

with login:

    if st.button(

        "Login",
        icon = ":material/login:",
        type = 'primary',
        width = 'stretch',
        key = "login"

    ):
        
        if not cus_email or not password:

            st.toast("Missing Details, Please enter and try again")

        elif uh.CheckPassword("customer", cus_email, password):

            st.toast("Login Successful!", duration = 'short')

            st.session_state["Cus_Email"] = cus_email
            st.session_state["Cus_Name"] = uh.GetCustomerName(cus_email)
            st.session_state["Cus_ID"] = uh.GetCustomerId(cus_email)

            if st.session_state["auth"] == "Guest":

                st.session_state["auth"] = "User"
                st.switch_page("views/7_UserBooking.py")

            else:

                st.session_state["auth"] = "User"
                st.rerun()
            
        else:

            st.session_state["password_wk"] = ""
            st.error("Login Failed! Try again")
            
with register:

    if st.button(
    
        "Register",
        icon = ":material/person_add:",
        type = 'secondary',
        width = 'stretch',
        key = "register"

    ):

        st.session_state["auth"] = "RegisteringUser"
        st.rerun()

if st.button(

    "Use As Guest",
    icon = ":material/account_circle:",
    type = 'secondary',
    width = 'stretch',
    key = 'guest'

):

    st.session_state["auth"] = "Guest"
    st.rerun()