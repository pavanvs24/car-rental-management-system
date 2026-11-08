import streamlit as st
import datetime as dt
import bcrypt as bt
import math
from decimal import Decimal
from db import get_connection
from typing import Any, cast
from typing_extensions import LiteralString

def ClearAndLogOut():

    custom_keys = [
        
        key for key in st.session_state.keys() 
        if not str(key).startswith("__") and key != "st.sidebar" and key != "auth"
    
    ]

    for key in custom_keys:

        del st.session_state[key]

    st.session_state["auth"] = "No_Auth"
    st.toast(":green[Logged Out]", duration = 'short')
    st.rerun()

def CheckPassword(select, identifier, password) -> bool:

    f_hash = ""

    with get_connection() as conn:

        with conn.cursor() as cur:

            if select == "staff":

                try:

                    int(identifier)

                except ValueError:

                    return False
                
                cur.execute("SELECT password_hash FROM staff WHERE staff_id = %s;", (int(identifier),))

                hash = cur.fetchone()

                f_hash = hash[0] if hash else ""

            elif select == "customer":

                cur.execute("SELECT password_hash FROM customer WHERE email = %s;", (identifier,))
                hash = cur.fetchone()

                f_hash = hash[0] if hash else ""

    if not f_hash:

        return False
    
    return bt.checkpw(password.encode('utf-8'), f_hash.encode('utf-8'))

@st.cache_data(ttl=dt.timedelta(minutes=5))
def GetFilterOptions() -> dict[str,Any]:

    query = f"""
                SELECT DISTINCT 'brand' AS col, brand::text AS val FROM vehicle_model WHERE brand IS NOT NULL
                UNION ALL
                SELECT DISTINCT 'fuel_type', fuel_type::text FROM vehicle_model WHERE fuel_type IS NOT NULL
                UNION ALL
                SELECT DISTINCT 'transmission', transmission::text FROM vehicle_model WHERE transmission IS NOT NULL
                UNION ALL
                SELECT DISTINCT 'seats', seats::text FROM vehicle_model WHERE seats IS NOT NULL
                UNION ALL
                SELECT 'min_rate', MIN(daily_rate)::text FROM vehicle_model
                UNION ALL
                SELECT 'max_rate', MAX(daily_rate)::text FROM vehicle_model;
            """

    filter_options = {}

    with get_connection() as conn:

        with conn.cursor() as cur:

            safe_query = cast(LiteralString, query)
            
            cur.execute(safe_query)
    
            for col, val in cur.fetchall():

                if col in ("seats", "min_rate", "max_rate"):

                    number = Decimal(val)

                    number = math.ceil(number) if col == "max_rate" else math.floor(number)

                    filter_options.setdefault(col, []).append(int(number))

                else:

                    filter_options.setdefault(col, []).append(val)

                filter_options[col].sort()

    return filter_options

def GetModels(brand_names: list[str]) -> list[str]:

    query = f"SELECT DISTINCT model_name FROM vehicle_model WHERE brand = ANY(%s)"

    with get_connection() as conn:

        with conn.cursor() as cur:
            safe_query = cast(LiteralString, query)

            cur.execute(safe_query, (brand_names,))

            rows = cur.fetchall() or []

    return [row[0] for row in rows]

def GetCustomerId(email: str) -> int:

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute("SELECT customer_id FROM customer WHERE email = %s", (email,))

            row = cur.fetchone()

    return row[0] if row else -1

def GetCustomerName(email: str) -> str:

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute("SELECT full_name FROM customer WHERE email = %s", (email,))

            row = cur.fetchone()

    return row[0] if row else ""

def GetStaffName(StaffID: int) -> str:

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute("SELECT full_name FROM staff WHERE staff_id = %s", (StaffID,))

            row = cur.fetchone()

    return row[0] if row else ""
