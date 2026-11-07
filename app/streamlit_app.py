import streamlit as st

#===============================================================

if "auth" not in st.session_state:

    st.session_state["auth"] = "No_Auth"

PAGES = {

    "No_Auth" :  [st.Page('views/0_Landing.py', default = True, title = 'Welcome!')],

    "Guest" : [st.Page('views/5_UserLanding.py', default = True, title = 'Cars View')],

    "LoggingInUser" : [st.Page('views/1_UserLogin.py', default = True, title = 'Login')],

    "RegisteringUser" : [st.Page('views/3_UserRegistration.py', default = True, title = 'Register')],

    "LoggingInAdmin" : [st.Page('views/2_StaffLogin.py', default = True, title = 'Login')],

    "RegisteringAdmin" : [st.Page('views/4_StaffRegistration.py', default = True, title = 'Register')],

    "User" : [st.Page('views/5_UserLanding.py', default = True, title = 'Cars View'), st.Page('views/7_UserBooking.py', title = 'Booking'), st.Page('views/8_UserProfile.py', title = 'Account')],

    "Admin" : [st.Page('views/6_StaffLanding.py', default = True, title = "Dashboard")]

}

pages_to_show = PAGES[st.session_state["auth"]]

pg = st.navigation(pages_to_show)
pg.run()