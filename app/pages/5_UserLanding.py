from typing import Any
import services as ss
import streamlit as st
import datetime as dt

#==============Page Layout=================

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
            padding-left: 0.5rem;
            padding-right: 0.5rem;
            padding-top: 1rem; 
        }
    </style>
    """
)

#==============Data Init==================

FILTER_OPTIONS = ss.Get_Filter_Options()
min_price = FILTER_OPTIONS["min_rate"][0] if FILTER_OPTIONS.get("min_rate") else 0
max_price = FILTER_OPTIONS["max_rate"][0] if FILTER_OPTIONS.get("max_rate") else 10000

DEFAULT_FILTERS = {

    "dates" : [dt.date.today(), dt.date.today() + dt.timedelta(days = 1)],
    "seats" : ["All"],
    "fuel_type" : ["All"],
    "transmission" : ["All"],
    "daily_rate" : (min_price, max_price),
    "brand" : [],
    "model" : []

}

for key, value in DEFAULT_FILTERS.items():

    if key not in st.session_state:

        st.session_state[key] = value

if "first_time" not in st.session_state:

    st.session_state["first_time"] = True
    st.session_state["vehicle_list"] = []
    st.session_state["current_page"] = 1
    st.session_state["page_nav"] = [True, True]

#================Functions================

def ClearAndLogOut():

    st.session_state.clear()
    st.switch_page("pages/1_UserLogin.py")

def ChangeToAll(select):

    if "All" in st.session_state[select]:

        if st.session_state[select][-1] == "All":

            st.session_state[select] = ["All"]

        elif len(st.session_state[select]) > 1 and st.session_state[select][0] == "All":

            st.session_state[select] = [x for x in st.session_state[select] if x != "All"]

    elif len(st.session_state[select]) == len(FILTER_OPTIONS[select]):

        st.session_state[select] = ["All"]

    elif len(st.session_state[select]) == 0:

        st.session_state[select] = ["All"]

def ApplyRetriveDisplay():

    SELECTED_FILTERS = {}

    for key, value in DEFAULT_FILTERS.items():

        if key == "dates":

            pass
        
        elif key == "daily_rate":

            SELECTED_FILTERS["min_daily_rate"] = st.session_state["daily_rate"][0]
            SELECTED_FILTERS["max_daily_rate"] = st.session_state["daily_rate"][1]
        
        elif st.session_state[key] != value:

            SELECTED_FILTERS[key] = st.session_state[key]

    if len(st.session_state["dates"]) == 1:

        st.session_state["dates"] = [st.session_state["dates"][0], st.session_state["dates"][0]]

    st.session_state["vehicle_list"] = ss.search_available_vehicles(st.session_state["dates"][0], st.session_state["dates"][1], SELECTED_FILTERS)    

def ResetFilters(select):

    if select == "All":

        for key, value in DEFAULT_FILTERS.items():
            
            st.session_state[key] = value

        ApplyRetriveDisplay()

    else:

        st.session_state[select] = DEFAULT_FILTERS[select]


def UpdateCurrentPage(dir):

    if dir == 1:

        st.session_state["current_page"] += 1
        st.session_state["page_nav"][0] = False

    elif dir == -1:

        st.session_state["current_page"] -= 1
        st.session_state["page_nav"][1] = False

def BookCar(vehicle):


    st.switch_page("pages/7_UserBooking.py")

    pass

#initialise data for first time
if st.session_state["first_time"]:

    ApplyRetriveDisplay()
    st.session_state["first_time"] = False

#==============Login auth==================

if "auth" not in st.session_state or st.session_state.auth == False:

    ClearAndLogOut()

empty, logout, rerun = st.columns([11,1,1], gap = "small", vertical_alignment = 'top', width = 'stretch')

with logout:

    if st.button("Log :red[Out]", key="LogOut"):
        ClearAndLogOut()

with rerun:

    #dev only, disable when commit
    if st.button("Re :green[Run]", key = 'rerun'):
        st.rerun()

#==========================================

col_filters, col_main = st.columns([4,10])

#=============Col Filters==================
with col_filters:   

    st.title(

        ":red[Filters]",
        text_alignment = 'center'

    )

    st.write("")
    st.write("")
    st.write("")
    st.write("")

    with st.container(border = True):

        col1, col2 = st.columns([0.9, 0.1], vertical_alignment = 'bottom')

        col1.date_input(

            "Date Range:",
            key = "dates",  
            
        )

        col2.button(

            "",
            icon = ":material/refresh:",
            key = '1',
            on_click = ResetFilters,
            args = ("dates",)

        )

        col1, col2 = st.columns([0.9, 0.1], vertical_alignment = 'bottom')

        col1.segmented_control(

            "Seat Capacity:",
            options = ["All"] + FILTER_OPTIONS["seats"],
            key = "seats",
            selection_mode = 'multi',
            on_change = ChangeToAll,
            args = ("seats",)

        )

        col2.button(

            "",
            icon = ":material/refresh:",
            key = '2',
            on_click = ResetFilters,
            args = ("seats",)

        )

        col1, col2 = st.columns([0.9, 0.1], vertical_alignment = 'bottom')

        col1.slider(

            "Price Range (Per Day):",
            min_value = FILTER_OPTIONS["min_rate"][0] if FILTER_OPTIONS["min_rate"] else 0,
            max_value = FILTER_OPTIONS["max_rate"][0] if FILTER_OPTIONS["max_rate"] else 20000,
            key = "daily_rate",
            value = (st.session_state["daily_rate"][0], st.session_state["daily_rate"][1])

        )

        col2.button(

            "",
            icon = ":material/refresh:",
            key = '3',
            on_click = ResetFilters,
            args = ("daily_rate",)

        )

        st.write("")

        if st.toggle(
            "Advance Filters: "
        ):

            col1, col2 = st.columns([0.9, 0.1], vertical_alignment = 'bottom')

            col1.segmented_control(

                "Fuel Type:",
                options = ["All"] + FILTER_OPTIONS["fuel_type"],
                key = "fuel_type",
                selection_mode = 'multi',
                on_change = ChangeToAll,
                args = ("fuel_type",)

            )

            col2.button(

                "",
                icon = ":material/refresh:",
                key = '4',
                on_click = ResetFilters,
                args = ("fuel_type",)

            )

            col1, col2 = st.columns([0.9, 0.1], vertical_alignment = 'bottom')

            col1.segmented_control(

                "Transmission:",
                options = ["All"] + FILTER_OPTIONS["transmission"],
                key = "transmission",
                selection_mode = 'multi',
                on_change = ChangeToAll,
                args = ("transmission",)

            )

            col2.button(

                "",
                icon = ":material/refresh:",
                key = '5',
                on_click = ResetFilters,
                args = ("transmission",)

            )

            col1, col2 = st.columns([0.9, 0.1], vertical_alignment = 'bottom')

            col1.multiselect(

                "Brands:",
                options = FILTER_OPTIONS["brand"],
                key = "brand",

            )

            col2.button(

                "",
                icon = ":material/refresh:",
                key = '6',
                on_click = ResetFilters,
                args = ("brand",)

            )
            
            col1, col2 = st.columns([0.9, 0.1], vertical_alignment = 'bottom')

            col1.multiselect(

                "Models:",
                options = ss.get_models(st.session_state["brand"]),
                key = "model",

            )

            col2.button(

                "",
                icon = ":material/refresh:",
                key = '7',
                on_click = ResetFilters,
                args = ("model",)

            )

        st.divider()

        col1, col2 = st.columns(2)

        with col1:

            st.button(

                "Apply",
                key = "Apply",
                type = 'primary',
                width = 'stretch',
                on_click = ApplyRetriveDisplay

            )

        with col2:

            st.button(

                "Reset",
                key = "reset",
                type = "secondary",
                width = 'stretch',
                on_click = ResetFilters,
                args = ("All",)

            )

#================Col CAR VIEW=================

index = st.session_state["current_page"]

if index == len(st.session_state["vehicle_list"])//16 + 1:

    st.session_state["right_disabled"] = True

if index == 1:

    st.session_state["left_disabled"] = True


with col_main:

    st.title(

    ":red[Car] Selection",
    text_alignment = 'center'

    )

    st.divider()

    for idx, vehicle in enumerate(st.session_state["vehicle_list"][16*(index-1):(16*index)]):
    
        if idx % 4 == 0:

            cols = st.columns(3)

        col = cols[idx % 3]
                
        with col:
            
            with st.container(border=True):

                st.markdown(f"### {16*(index-1) + idx + 1}) {vehicle["brand"]} {vehicle["model_name"]}", text_alignment = 'center')
                st.markdown(f"<h5 style='text-align: center; color: #FF5555; margin: 0.5;'> {vehicle["registration_no"]} </h5>", unsafe_allow_html = True)

                st.divider()

                col_1, col_2 = st.columns([1.9,1])

                with col_1:

                    col_11, col_12 = st.columns(2)

                    with col_11:

                        st.caption("**Odometer**")
                        st.markdown(f"{vehicle["odometer"]}")

                        st.caption("**Seats**")
                        st.markdown(f"{vehicle["seats"]}")

                    with col_12:

                        st.caption("**Transmission**")
                        st.markdown(f"{vehicle["transmission"]}".lower())

                        st.caption("**Fuel Type**")
                        st.markdown(f"{vehicle["fuel_type"]}".lower())

                with col_2:

                    st.write("")
                    st.write("")
                    st.markdown(f"<h4 style='text-align: right; margin: 0.5; color: #2E7D32;'>₹{vehicle["daily_rate"]:,}/ day</h4>", unsafe_allow_html=True)
                    
                st.write("") 
                
                st.button(

                    f"Book **{vehicle["registration_no"]}**", 
                    type = 'primary',
                    key = 16*index + idx, 
                    use_container_width = True,
                    on_click = BookCar,
                    args = (vehicle,)

                )
                        
    st.divider()

    c1, c2, c3 = st.columns([2.22,2,1])

    with c2.container(border = True, width = 'content', horizontal_alignment = 'center'):

        c21, c22, c23 = st.columns(3)

        c21.button(

            ":material/chevron_left:",
            disabled = st.session_state["page_nav"][0],
            on_click = UpdateCurrentPage,
            args = (-1,)

        )

        c22.html(f"<p style='text-align: center;'> <b>{st.session_state["current_page"]}</b> / {len(st.session_state["vehicle_list"])//16 + 1}</p>")    

        c23.button(

            ":material/chevron_right:",
            disabled = st.session_state["page_nav"][1],
            on_click = UpdateCurrentPage,
            args = (1,)
                            
        )