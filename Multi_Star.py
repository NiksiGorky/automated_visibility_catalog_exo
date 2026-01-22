import streamlit as st
import datetime

from utils import vspace
from utils import is_numeric
from utils import read_data
from utils import Observability
from utils import Coordinates
from utils import pd
from utils import u

st.markdown(
    "<h2 style='text-align: center; margin-top: -50px;'>"
    "Multi Star Calculator"
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

# Container for the file uploader

    Data=None

    with cols[0]:  # Second column for file uploader
        
        uploaded_file = st.file_uploader("Upload your star catalog file", type=["csv", "txt", "dat"])

        if uploaded_file is not None:
            try:

                Data = read_data(uploaded_file)
                st.session_state["Data"] = Data
                st.success("File Loaded Successfully", width=315)

            except Exception as e:

                st.error(f"{e}")

    with cols[1]:

        if uploaded_file is not None and lat and long and is_numeric(lat) and is_numeric(long):

            vspace(17) 
            with st.expander("Data preview", expanded=False, width=360):

                st.dataframe(Data, height=210)

        elif uploaded_file is not None and lat and long:

            vspace(12) 
            with st.expander("Data preview", expanded=False, width=360):

                st.dataframe(Data, height=210)

        elif uploaded_file is not None:

            vspace(4) 
            with st.expander("Data preview", expanded=False, width=360):

                st.dataframe(Data, height=210)

preview_container=st.container()

with preview_container:

    pcols = st.columns([0.333,0.333,0.333]) 

    if Data is not None and lat and long and is_numeric(lat) and is_numeric(long):

        with pcols[0]:

            dur=None
            magn=None
            
            vspace(2)
            
            checkbox=st.checkbox('Filters', key="filter_checkbox")

            if checkbox: #Filter buttons
                left,right=st.columns(2)

                with left:
                    dur=st.number_input('Duration >', value=None, key="dur")
                
                with right:
                    magn=st.number_input('magnitude >', value=None, key="mag")
                
                # Add consistent spacing after filters
                vspace()
            else:
                # When filters are not checked, add the same amount of space
                vspace()

        with pcols[0]:
                
                if st.button('Calculate the time of observability'):
                    
                    try:
                        
                        Star_Observability = Observability(
                            st.session_state["Data"],
                            utc_shift,
                            date,
                            st.session_state["Loc"],
                            st.session_state["timezone_local"]
                        )

                        # store result for later preview
                        st.session_state["Star_Observability"] = Star_Observability

                        # Apply filters
                        filtered_data = Star_Observability.copy()
                        if 'Visibility (min)' in Star_Observability.columns and dur is not None:
                            filtered_data = filtered_data[filtered_data['Visibility (min)'] > dur]

                        if magn is not None and 'mag' in Star_Observability.columns:
                            
                            mag_numeric = pd.to_numeric(filtered_data['mag'], errors='coerce')
                            filtered_data = filtered_data[mag_numeric.isna() | (mag_numeric < magn)]

                        st.session_state["Filtered_Observability"] = filtered_data
                        st.session_state["calculation_done"] = True

                        with pcols[1]:

                            if checkbox:
                                vspace(17) 
                                with st.expander("Observability preview", expanded=False, width=360):
                                    st.dataframe(filtered_data, height=212)

                                with pcols[2]:
                                    vspace(18) 
                                    total=len(filtered_data['star name'])
                                    st.write("Total Number of Output Data : "+ str(total))
                            else:
                                vspace(8) 
                                with st.expander("Observability preview", expanded=False, width=360):
                                    st.dataframe(Star_Observability, height=212)

                                with pcols[2]:
                                    vspace(9) 
                                    total=len(Star_Observability['star name'])
                                    st.write("Total Number of Output Data : "+ str(total))

                    except Exception as e:
                        st.error(f'{e}')