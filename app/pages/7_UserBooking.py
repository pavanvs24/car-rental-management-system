import streamlit as st
import datetime as dt
import services as ss

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
    </style>
    """
)

st.html(
    """
    <style>
        /* Hide default header bar strip entirely */
        header[data-testid="stHeader"] {
            display: none !important;
        }

        div[data-testid="stMainBlockContainer"] {
            padding-left: 0.2rem;
            padding-right: 0.2rem;
            padding-top: 1rem; 
        }
    </style>
    """
)

if "auth" not in st.session_state or st.session_state.auth == False:

    st.session_state.clear()
    st.switch_page("streamlit_app.py")

def ConfirmBooking():
    pass
    

#================Page==================

st.write("")
st.write("")
st.write("")
st.write("")
st.write("")

col1, col2, col3 = st.columns([1,10,1])

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
        st.subheader(":red[Car] Details", text_alignment ='center')
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
            Total = int(Days) * 2000

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


















