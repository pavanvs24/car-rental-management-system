import streamlit as st

#===========================================================

st.set_page_config(

    layout = 'centered',

)

#===========================================================

st.title(":red[Log] In As", text_alignment = 'center')

st.write("")

st.divider()

st.write("")
st.write("")
st.write("")

col1, col2 = st.columns([1,1])

with col1:

    if st.button(

        '**Log In As User**',
        icon = ':material/person:',
        width = 'stretch',
        type = 'primary',
        key = 1

    ):

        st.session_state["auth"] = "LoggingInUser"
        st.rerun()

with col2:

    if st.button(

        '**Log In As Guest**',
        width = 'stretch',
        type = 'secondary',
        key = 2

    ):

        st.session_state["auth"] = "Guest"
        st.rerun()

if st.button(

    '**Log In As Admin**',
    icon = ':material/shield_person:',
    width = 'stretch',
    type = 'primary',
    key = 3

):

    st.session_state["auth"] = "LoggingInAdmin"
    st.rerun()
    