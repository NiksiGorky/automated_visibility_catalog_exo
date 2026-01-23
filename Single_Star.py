import streamlit as st

from utils import vspace
from utils import Coordinates
from utils import Observability_Single

import datetime
from utils import u

st.markdown(
    "<h2 style='text-align: center; margin-top: -50px;'>"
    "Single Star Calculator"
    "</h2>",
    unsafe_allow_html=True
)

vspace(2)

# Create a container and center the inputs
container = st.container()

with container:
    cols = st.columns([0.333,0.333,0.333])  # Create 4 equal columns
    
    with cols[0]: 
        lat = st.text_input("Enter your latitude in signed DD format", key="lat")
    
    with cols[1]: 
        long = st.text_input("Enter your longitude in signed DD format", key="long")

    with cols[2]: 
        date=st.date_input("Select observation date")

    with cols[0]:

        if lat and long:

            try:

                if ("prev_lat" not in st.session_state
                    or st.session_state["prev_lat"] != lat
                    or st.session_state["prev_long"] != long):

                    Loc, timezone_local, tz_string = Coordinates(lat, long)
                    
                    st.session_state.update({
                        "Loc": Loc,
                        "timezone_local": timezone_local,
                        "prev_lat": lat,
                        "prev_long": long,
                        "tz_string": tz_string,
                        })

                else:

                    Loc = st.session_state["Loc"]
                    timezone_local = st.session_state["timezone_local"]
                    tz_string = st.session_state["tz_string"]

                local_time = datetime.datetime.now(timezone_local)
                utc_shift_p = local_time.utcoffset().total_seconds() / 3600
                utc_shift = utc_shift_p * u.hour

                # Streamlit outputs outside cached function
                st.write("Time zone:", tz_string)
                st.write("Local time:", local_time.strftime("%H:%M:%S"))
                st.write("UTC Shift:", utc_shift_p, "h")

                if tz_string.startswith("Etc/GMT"):
                    st.warning('Location maybe a sea or desert', width=310)

            except Exception as e:
                st.error(f"{e}", width=309)

    with cols[0]: 
        ra = st.text_input("Enter your stars RA in signed DD format", key="ra")
    
    with cols[1]: 

        if lat and long:
            
            vspace(13)

            dec = st.text_input("Enter your stars DEC in signed DD format", key="dec")

        else:
            dec = st.text_input("Enter your stars DEC in signed DD format", key="dec")

    if lat and long and ra and dec:

        Duration, formatted, fig= Observability_Single(float(ra), float(dec), utc_shift,date, Loc, timezone_local)

        with cols[0]:

            st.write("Duration of Observability:", Duration, "min")
            st.write("Star Rise Time:", formatted[0])
            st.write("Star Set Time:", formatted[-1])

        with cols[1]:

            st.pyplot(fig)


