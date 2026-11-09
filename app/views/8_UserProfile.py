import math
import streamlit as st
import time
import services as ss
import ui_helpers as uh

st.set_page_config(

    layout = 'wide',

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
            padding-left: 0.5rem;
            padding-right: 0.5rem;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
    </style>
    """
)

#==================================================================

@st.dialog("Confirm Cancellation")
def CancelBookingDialog(booking_id: int):

    st.warning(f"Cancel **Booking #{booking_id}**?")
    st.caption("Please enter your account password to confirm cancellation.")

    if "cancel_tries" not in st.session_state:

        st.session_state["cancel_tries"] = 3

    password = st.text_input(

        "Password",
        type="password",
        max_chars=36,
        key=f"cancel_pw_{booking_id}",

    )

    st.write("")

    col_confirm, col_cancel = st.columns(2)

    with col_confirm:

        if st.button("Confirm Cancel", type="primary", use_container_width=True):

            if uh.CheckPassword("customer", st.session_state["Cus_Email"], password):

                try:

                    result = ss.cancel_booking(

                        booking_id = booking_id,
                        customer_id = st.session_state["Cus_ID"],

                    )
                    
                    st.success("Booking cancelled successfully!")
                    st.info(f"Advance refund due: **${result.get('advance_paid', 0):,.2f}**")
                    
                    st.session_state.pop("cancel_tries", None)
                    st.session_state.pop(f"cancel_pw_{booking_id}", None)

                    time.sleep(1.2)
                    st.rerun()

                except ValueError as err:

                    st.error(f"Cancellation failed: {err}")

            else:

                st.session_state["cancel_tries"] -= 1

                if st.session_state["cancel_tries"] <= 0:

                    st.error("Too many wrong attempts! Logging Out...")

                    del st.session_state["cancel_tries"]
                    
                    uh.ClearAndLogOut()
                    st.rerun()

                else:

                    st.error(

                        f"Wrong password. Attempts remaining: {st.session_state['cancel_tries']}"

                    )

    with col_cancel:

        if st.button(
            
            "Never Mind",
            use_container_width = True
            
        ):

            del st.session_state["cancel_tries"]
            del st.session_state[f"cancel_pw_{booking_id}"]
            st.rerun()

def GetStatusBadge(status: str) -> str:

    color_map = {

        "CONFIRMED": "green",
        "COMPLETED": "blue",
        "CANCELLED": "red",

    }

    color = color_map.get(status.upper(), "gray")
    return f":{color}[**{status.upper()}**]"


#==================================================================

col_title, col_home = st.columns([10,1])

with col_title:

    st.title("Your :red[Car] Bookings")
    st.caption("Review your rental reservations, trip durations, and booking status.")

with col_home:

    if st.button(

        "",
        icon = ":material/home:"

    ):

        st.switch_page("views/5_UserLanding.py")

#==================================================================

col_filter, _ = st.columns([1.5, 3])

with col_filter:

    status_choice = st.selectbox(

        "Filter by Status",
        options = ["All", "CONFIRMED", "COMPLETED", "CANCELLED"],
        index = 0,
        key = "booking_status_filter"

    )

selected_status = None if status_choice == "All" else status_choice

try:

    bookings = ss.get_customer_bookings(st.session_state["Cus_ID"], selected_status)

except ValueError as e:

    st.error(f"Error fetching bookings: {e}")
    st.stop()

if not bookings:

    st.info("No bookings found for the selected criteria.")
    st.stop()

#==================================================================

ITEMS_PER_PAGE = 3
total_items = len(bookings)
total_pages = math.ceil(total_items / ITEMS_PER_PAGE)

if "booking_page" not in st.session_state:

    st.session_state["booking_page"] = 1

if st.session_state["booking_page"] > total_pages:

    st.session_state["booking_page"] = 1

current_page = st.session_state["booking_page"]
start_idx = (current_page - 1) * ITEMS_PER_PAGE
end_idx = start_idx + ITEMS_PER_PAGE
page_bookings = bookings[start_idx:end_idx]

#======================================================================

for b in page_bookings:

    with st.container(border=True):

        col_main, col_stats, col_action = st.columns([2.5, 1.8, 1.2], gap="medium")

        with col_main:

            st.subheader(f"{b['brand']} {b['model_name']}")
            st.markdown(f"**Plate:** `{b['registration_no']}` &nbsp;|&nbsp; **Booking ID:** `#{b['booking_id']}`")
            st.caption(f"Booked on: {b['booking_date']}")

        with col_stats:

            st.markdown(f"**Status:** {GetStatusBadge(b['status'])}")
            st.write(f"**Dates:** {b['start_date']} to {b['end_date']}")
            st.write(f"**Duration:** {b['days']} {'day' if b['days'] == 1 else 'days'}")

        with col_action:

            st.caption("Total Cost")
            st.markdown(f"### ₹{b['total_amount']:,.2f}")
            st.caption(f"(₹{b['daily_rate']:,.2f}/day)")

            if b["status"] == "CONFIRMED":

                if st.button(
                    
                    "Cancel Booking",
                    key = f"cancel_btn_{b['booking_id']}",
                    use_container_width = True
                    
                ):
                    
                    CancelBookingDialog(b["booking_id"])

#======================================================================

st.divider()
p_col1, p_col2, p_col3 = st.columns([1, 2, 1], vertical_alignment="center")

with p_col1:

    if st.button("⬅ Previous", disabled=(current_page == 1), use_container_width=True):

        st.session_state["booking_page"] -= 1
        st.rerun()

with p_col2:

    st.html(

        f"<div style='text-align: center; color: gray;'>Page <b>{current_page}</b> of <b>{total_pages}</b> &bull; ({total_items} bookings)</div>"

    )

with p_col3:

    if st.button(

        "Next ➡", 
        disabled = (current_page == total_pages), 
        use_container_width = True
        
    ):

        st.session_state["booking_page"] += 1
        st.rerun()