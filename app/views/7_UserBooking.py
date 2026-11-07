import streamlit as st
import datetime as dt
import services as ss
import bcrypt as bt
import time as te
import ui_helpers as uh

#===============PAGE==================

st.set_page_config(

    "Selection",
    layout = 'wide',
    initial_sidebar_state = 'collapsed'

)

st.html(
    """
    <style>

        [data-testid="stVerticalBlock"] {
            gap: 0.5rem;
        }

        header[data-testid="stHeader"] {
            display: none !important;
        }

        div[data-testid="stMainBlockContainer"] {
            padding-left: 0.2rem;
            padding-right: 0.2rem;
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
    </style>
    """
)

#===============================================================

@st.dialog("Enter details to confirm booking")
def ConfirmBooking():

    st.warning(f"Confirm Booking?")
    st.caption("Please enter your account password to confirm cancellation.")


    if "cancel_tries" not in st.session_state:

        st.session_state["cancel_tries"] = 3

    password = st.text_input(
        
        'password', 
        type = "password",
        max_chars = 36,
        key = "password_wk"
        
    )

    st.write("")

    if st.button(
        
        "Confirm", 
        type = 'primary',
        
    ):

        if uh.CheckPassword("customer", st.session_state["Cus_Email"], password):

            st.success("BOOKING CONFIRMED!")

            ss.create_booking(

                st.session_state["Cus_ID"],
                st.session_state["selected_vehicle"]["vehicle_id"],
                st.session_state["f_dates"][0], 
                st.session_state["f_dates"][1],

            )

            for key in st.session_state.keys():

                if not str(key).startswith("__") and key not in ("auth", "Cus_Name", "Cus_Email", "Cus_ID"):

                    del st.session_state[key]
    

            st.switch_page("views/8_UserProfile.py")

        else:

            if st.session_state["tries"] == 0:

                st.error("Too many wrong attempts! Logging Out...")
                uh.ClearAndLogOut()
            
            st.session_state["tries"] -= 1
            st.error(f"Wrong Details! Attempts remaining: {st.session_state["tries"] + 1}")


#================Page==================

st.write("")
st.write("")
st.write("")
st.write("")
st.write("")

col1, col2, col3 = st.columns([1,10,1])

with col1:

    if st.button(

        "",
        icon = ":material/arrow_back:",
        type="secondary"

    ):

        del st.session_state["selected_vehicle"]
        del st.session_state["f_dates"]
        st.switch_page("views/5_UserLanding.py")

#with col3:

#    with st.popover("", icon=":material/settings:", key="settings", width = 'content'):
                
#                if st.button(":green[Pro]file", width="stretch"):

#                    st.switch_page("pages/8_UserProfile.py")
                    
#                elif st.button(":red[Log] Out", width="stretch"):

#                    st.session_state.clear()
#                    st.switch_page("streamlit_app.py")

with col2:

    with st.container(border = True, width = 'stretch'):

        st.header(":red[Booking] Information", text_alignment = 'center')

        st.divider()
        st.subheader(":red[Car] Details", text_alignment = 'center')
        st.divider()

        col_keys, col_values = st.columns([1,1])

        with col_keys:

            st.markdown("#### :red[Reg No]")
            st.markdown("#### :red[Odometer]")
            st.markdown("#### :red[Fuel Type]")
            st.markdown("#### :red[Transmission]")

        with col_values:

            st.markdown(f"#### :&nbsp;&nbsp;&nbsp;&nbsp;{st.session_state["selected_vehicle"]["registration_no"]}")
            st.markdown(f"#### :&nbsp;&nbsp;&nbsp;&nbsp;{st.session_state["selected_vehicle"]["odometer"]} km")
            st.markdown(f"#### :&nbsp;&nbsp;&nbsp;&nbsp;{st.session_state["selected_vehicle"]["fuel_type"]}")
            st.markdown(f"#### :&nbsp;&nbsp;&nbsp;&nbsp;{st.session_state["selected_vehicle"]["transmission"]}")

        st.divider()
        st.subheader(":red[Billing] Details", text_alignment = 'center')
        st.divider()

        col_keys, col_values = st.columns([1,1])

        with col_keys:

            st.markdown("#### :red[Rate]")
            st.markdown("#### :red[Start Date]")
            st.markdown("#### :red[End Date]")
            st.markdown("#### :red[No Of Days]")
            st.markdown("#### :red[Payable Total]")
            st.markdown("#### :red[Payble Advance]")

        with col_values:

            Days = (st.session_state["f_dates"][1] - st.session_state["f_dates"][0]).days + 1
            Total = int(Days) * st.session_state["selected_vehicle"]["daily_rate"]

            st.markdown(f"#### :&nbsp;&nbsp;&nbsp;&nbsp;₹{st.session_state["selected_vehicle"]["daily_rate"]} per day")
            st.markdown(f"#### :&nbsp;&nbsp;&nbsp;&nbsp;{st.session_state["f_dates"][0].strftime("%d-%m-%Y")}")
            st.markdown(f"#### :&nbsp;&nbsp;&nbsp;&nbsp;{st.session_state["f_dates"][1].strftime("%d-%m-%Y")}")
            st.markdown(f"#### :&nbsp;&nbsp;&nbsp;&nbsp;{Days}")
            st.markdown(f"#### :&nbsp;&nbsp;&nbsp;&nbsp;₹{Total}")
            st.markdown(f"#### :&nbsp;&nbsp;&nbsp;&nbsp;₹{0.2*Total}")

        st.divider()
        st.write("")
        
        st.button(

            "Confirm Booking",
            type = 'primary',
            width = 'stretch',
            on_click = ConfirmBooking
            
        )
