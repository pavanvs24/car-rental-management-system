import streamlit as st
import datetime as dt
import admin_services as admin
import services as ss
import ui_helpers as uh
import math
from decimal import Decimal

#==========================================

st.set_page_config(
    
    layout="wide"
    
)

st.html(
    """
    <style>
        [data-testid="stVerticalBlock"] { gap: 0.5rem; }
        header[data-testid="stHeader"] { display: none !important; }
        div[data-testid="stMainBlockContainer"] {
            padding-left: 2rem;
            padding-right: 2rem;
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
    </style>
    """
)

#==========================================

st.title(":red[Admin] Dashboard")

staff_id = st.session_state["Staff_ID"]
staff_name = st.session_state["Staff_Name"]

st.caption(f"**Current User:** {staff_name} | **Staff ID:** {staff_id}")

#==========================================

@st.dialog("Add New Vehicle Model")
def AddModelDialog():

    brand = st.text_input("Brand")
    model_name = st.text_input("Model Name")
    fuel = st.selectbox("Fuel Type", admin.FUEL_TYPES)
    trans = st.selectbox("Transmission", admin.TRANSMISSIONS)
    seats = st.number_input("Seats", min_value=1, step=1)
    rate = st.number_input("Daily Rate (₹)", min_value=0.0, step=100.0)
    
    if st.button("Save Model", type="primary", use_container_width=True):

        try:

            admin.add_vehicle_model(brand, model_name, fuel, trans, int(seats), rate)
            st.success("Model added successfully!")
            st.rerun()

        except ValueError as e:

            st.error(str(e))

@st.dialog("Add New Vehicle")
def AddVehicleDialog():

    models = admin.list_vehicle_models()
    model_opts = {m['model_id']: f"{m['brand']} {m['model_name']} (ID: {m['model_id']})" for m in models}
    
    selected_model = st.selectbox("Select Model", options=list(model_opts.keys()), format_func=lambda x: model_opts[x])
    reg_no = st.text_input("Registration No.")
    odo = st.number_input("Initial Odometer", min_value=0, step=1)
    status = st.selectbox("Initial Status", ["AVAILABLE", "UNAVAILABLE"])
    
    if st.button(
        
        "Save Vehicle", 
        type="primary", 
        use_container_width=True
        
    ):
        try:

            admin.add_vehicle(selected_model, reg_no, int(odo), status)
            st.success(f"Vehicle {reg_no} added successfully!")
            st.rerun()

        except ValueError as e:

            st.error(str(e))

@st.dialog("Change Vehicle Status")
def ChangeStatusDialog():

    vid = st.number_input("Vehicle ID", min_value=1, step=1)
    new_status = st.selectbox("New Status", ["AVAILABLE", "UNAVAILABLE"])
    
    if st.button(
        
        "Update Status", 
        type="primary", 
        use_container_width=True
        
    ):

        try:

            res = admin.set_vehicle_status(vid, new_status)
            st.success(f"Status changed to {res['new_status']}")

            if res.get("affected_bookings"):

                st.warning(f"Warning: This affected {len(res['affected_bookings'])} confirmed bookings.")
            
            st.rerun()

        except ValueError as e:

            st.error(str(e))

@st.dialog("Vehicle History")
def VehicleHistoryDialog():

    vid = st.number_input("Vehicle ID to lookup", min_value=1, step=1)

    if st.button(
        
        "Fetch History", 
        type="primary"
        
    ):

        try:

            data = admin.get_vehicle_history(vid)
            st.json(data)

        except ValueError as e:

            st.error(str(e))

@st.dialog("Reassign Booking")
def ReassignDialog():

    bid = st.number_input("Booking ID", min_value = 1, step = 1)
    new_vid = st.number_input("New Vehicle ID (Leave 0 for Auto-Assign)", min_value = 0, step = 1)
    
    if st.button(
        
        "Reassign", 
        type = "primary", 
        use_container_width = True
        
    ):

        try:

            assign_id = new_vid if new_vid > 0 else None
            res = admin.reassign_booking_vehicle(bid, assign_id)
            st.success(f"Booking {bid} reassigned from Vehicle {res['old_vehicle_id']} to {res['new_vehicle_id']}")
            st.rerun()

        except ValueError as e:

            st.error(str(e))

# ==========================================

nav_options = {

    "Dash": ":material/dashboard: Active Rentals",
    "Vehicles": ":material/directions_car: Vehicles",
    "Models": ":material/category: Models",
    "Bookings": ":material/book_online: Bookings",
    "Ops": ":material/build: Operations"

}

col_nav, col_logout = st.columns([10, 1], vertical_alignment = "center")

with col_nav:

    current_tab = st.segmented_control(

        "Admin Navigation", 
        options = list(nav_options.keys()), 
        format_func = lambda x: nav_options[x], 
        default = "Dash",
        label_visibility = "collapsed"

    )

with col_logout:

    if st.button(
        
        ":material/logout: Exit",
        type = "secondary", 
        use_container_width = True
        
    ):

        uh.ClearAndLogOut()

st.divider()

# ==========================================

if current_tab == "Dash":

    st.subheader(":material/dashboard: Active Rentals")

    rentals = admin.list_active_rentals()

    if rentals:

        st.dataframe(rentals, use_container_width=True, hide_index=True)

    else:

        st.info("No active rentals at the moment.")

elif current_tab == "Vehicles":

    st.subheader(":material/directions_car: Vehicle Management")
    
    filter_opts = uh.GetFilterOptions()
    
    with st.expander(":material/filter_list: Search & Filters"):

        c1, c2, c3, c4 = st.columns(4)
        status_f = c1.segmented_control("Status", options = ["All"] + list(admin.VEHICLE_STATUSES), default = "All")
        fuel_f = c2.segmented_control("Fuel Type", options = ["All"] + filter_opts.get("fuel_type", []), default = "All")
        trans_f = c3.segmented_control("Transmission", options = ["All"] + filter_opts.get("transmission", []), default = "All")
        seats_f = c4.segmented_control("Seats", options = ["All"] + filter_opts.get("seats", []), default = "All")
        
        reg_f = st.text_input("Registration Number (Partial)")
        
        filters = {}

        if status_f and status_f != "All": filters["status"] = status_f

        if fuel_f and fuel_f != "All": filters["fuel_type"] = fuel_f

        if trans_f and trans_f != "All": filters["transmission"] = trans_f

        if seats_f and seats_f != "All": filters["min_seats"] = seats_f

        if reg_f: filters["registration_no"] = reg_f
        
        vehicles = admin.list_vehicles(filters = filters)
    
    st.dataframe(vehicles, use_container_width = True, hide_index = True)
    
    st.write("")

    bc1, bc2, bc3, bc4 = st.columns(4)

    if bc1.button(
        
        ":material/add: Add Vehicle", 
        use_container_width = True
        
    ): 
        AddVehicleDialog()

    if bc2.button(
        
        ":material/edit: Change Status", 
        use_container_width = True
        
    ): 
        ChangeStatusDialog()

    if bc3.button(

        ":material/history: View History", 
        use_container_width = True
        
    ):
        VehicleHistoryDialog()

    if bc4.button(
        
        ":material/delete: Delete Vehicle", 
        use_container_width = True
        
    ):

        @st.dialog("Delete Vehicle")

        def del_dialog():

            vid = st.number_input("Vehicle ID to Delete", min_value = 1, step = 1)

            if st.button("Confirm Delete", type = "primary"):

                try:

                    admin.delete_vehicle(vid)
                    st.success("Vehicle deleted.")
                    st.rerun()

                except ValueError as e:

                    st.error(str(e))

        del_dialog()

elif current_tab == "Models":

    st.subheader(":material/category: Vehicle Models")

    models = admin.list_vehicle_models()

    st.dataframe(models, use_container_width = True, hide_index = True)
    
    if st.button(
        
        ":material/add: Add New Model", 
        type="primary"
        
    ):

        AddModelDialog()

elif current_tab == "Bookings":

    st.subheader(":material/book_online: Bookings")
    
    with st.expander(":material/filter_list: Booking Filters"):

        c1, c2, c3 = st.columns(3)
        b_status = c1.segmented_control("Booking Status", options=["All"] + list(admin.BOOKING_STATUSES), default = "All")
        b_cid = c2.number_input("Customer ID (0 for all)", min_value = 0, step = 1)
        b_vid = c3.number_input("Vehicle ID (0 for all)", min_value = 0, step = 1)
        
        b_filters = {}

        if b_status and b_status != "All": b_filters["status"] = b_status

        if b_cid > 0: b_filters["customer_id"] = int(b_cid)

        if b_vid > 0: b_filters["vehicle_id"] = int(b_vid)
        
        bookings = admin.list_bookings(filters = b_filters)

    st.dataframe(bookings, use_container_width = True, hide_index = True)
    
    st.write("")

    bc1, bc2, bc3 = st.columns(3)

    if bc1.button(
        
        ":material/swap_horiz: Reassign Vehicle", 
        use_container_width=True
    
    ): 

        ReassignDialog()
    
    if bc2.button(
        
        ":material/info: Booking Details", 
        use_container_width=True
        
    ):

        @st.dialog("Booking Details")
        def details_dialog():

            bid = st.number_input("Booking ID", min_value = 1, step = 1)

            if st.button(
                
                "Fetch Details"
                
            ):

                try:

                    st.json(admin.get_booking_details(bid))

                except ValueError as e:

                    st.error(str(e))

        details_dialog()
        
    if bc3.button(
        
        ":material/cancel: Cancel Booking", 
        use_container_width = True
        
    ):

        @st.dialog("Cancel Booking")
        def cancel_dialog():

            bid = st.number_input("Booking ID to Cancel", min_value = 1, step = 1)

            if st.button(
                
                "Confirm Cancel", 
                type = "primary"
            
            ):

                try:

                    res = ss.cancel_booking(bid)
                    st.success(f"Cancelled. Advance paid was ₹{res['advance_paid']}")
                    st.rerun()

                except ValueError as e:

                    st.error(str(e))

        cancel_dialog()

elif current_tab == "Ops":

    st.subheader(":material/build: Operations (Pickup & Return)")
    
    col_pickup, col_return = st.columns(2)
    
    with col_pickup.container(border = True):

        st.markdown("#### :material/key: Confirm Pickup")
        p_bid = st.number_input("Booking ID", min_value = 1, step = 1, key = "p_bid")
        p_odo = st.number_input("Pickup Odometer (Optional, 0 = Use Recorded)", min_value = 0, step = 1, key = "p_odo")
        p_date = st.date_input("Pickup Date", key = "p_date")
        
        if st.button(
            
            "Confirm Pickup", 
            type = "primary", 
            use_container_width = True
        
        ):

            try:

                odo_val = int(p_odo) if p_odo > 0 else None
                res = ss.confirm_pickup(int(p_bid), st.session_state["Staff_ID"], odo_val, p_date)
                st.success(f"Pickup confirmed! Rental ID: {res['rental_id']}")

            except ValueError as e:

                st.error(str(e))

    with col_return.container(border=True):

        st.markdown("#### :material/check_circle: Process Return")

        r_reg = st.text_input("Registration No.", key = "r_reg")
        r_odo = st.number_input("Return Odometer", min_value = 0, step = 1, key = "r_odo")
        r_charge = st.number_input("Other Charges (₹)", min_value = 0.0, step = 1.0, format = "%.2f", key = "r_charge")
        r_date = st.date_input("Return Date", key = "r_date")
        
        if st.button(

            "Process Return",
            type = "primary", 
            use_container_width = True
        
        ):
            try:

                charge_val = Decimal(str(r_charge)).quantize(Decimal("0.01"))

                res = ss.process_return(r_reg, st.session_state["Staff_ID"], int(r_odo), r_date, charge_val)
                
                st.success(f"Return processed! Final amount: ₹{res['final_amount']}")

                if res['refund_due'] > 0:

                    st.info(f"Refund due to customer: ₹{res['refund_due']}")

            except ValueError as e:

                st.error(str(e))