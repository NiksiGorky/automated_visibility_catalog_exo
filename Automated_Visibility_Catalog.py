import streamlit as st
import base64

from astropy.coordinates import SkyCoord, EarthLocation, AltAz, get_sun
import astropy.units as u
import numpy as np
import matplotlib.pyplot as plt
from astropy.time import Time

import pandas as pd

from timezonefinder import TimezoneFinder
import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Automated Visibility Catalog", layout="wide")

st.markdown(
    "<h1 style='text-align: center;'>🔭 Automated Visibility Catalog For Exoplanet Host Stars</h1>",
    unsafe_allow_html=True
)

st.markdown("<br>", unsafe_allow_html=True) 

st.markdown("""
<style>
    /* Style of the text input */
    div[data-testid="stTextInput"] label p {
        font-size: 16px !important;
    }
.stTextInput,
.stDateInput,
div[data-testid="stFileUploader"] {
    width: 100% !important;
    max-width: 420px;
}

    
    /* Change file uploader label text size */
    div[data-testid="stFileUploader"] label p {
        font-size: 16px !important;
    }
            
</style>

""", unsafe_allow_html=True)

for key in ["Data", "utc_shift", "Loc", "timezone_local", "Star_Observability"]:
    st.session_state.setdefault(key, None)

def is_numeric(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def vspace(units=1):
    units = max(0, units)
    st.markdown(
        f"<div style='height: {0.6 * units}em;'></div>",
        unsafe_allow_html=True
    )
#Function to read data from a file

@st.cache_data
def read_data(file_path):

    try:
        file=pd.read_csv(file_path, sep=None, engine='python')

    except Exception as e:
        raise ValueError('Error Loading File')
    
    file.columns = [c.strip().lower() for c in file.columns]

#    name_col = next((c for c in file.columns if 'name' in c), None)
#    mag_col = next((c for c in file.columns if 'mag' in c), None)
#    ra_col = next((c for c in file.columns if 'ra' in c), None)
#    dec_col = next((c for c in file.columns if 'dec' in c), None)
#    coord_col = next((c for c in file.columns if 'coord' in c), None)

    name_col = next((c for c in file.columns if c == 'star_name'), None)
    mag_col = next((c for c in file.columns if 'mag_v' in c), None)
    ra_col = next((c for c in file.columns if c == 'ra'), None)
    dec_col = next((c for c in file.columns if c == 'dec'), None)
    coord_col = next((c for c in file.columns if c == 'coord'), None)

    if ra_col and dec_col:
        ra = file[ra_col]
        dec = file[dec_col]
    elif coord_col:
        ra = file[coord_col].str.split(',').str[0]
        dec = file[coord_col].str.split(',').str[1]

    else:
        raise ValueError('No RA/DEC data found in the file. Use valid data/coloumn name')
    
    if not name_col is None:
        star_name=file[name_col]

    else:
        raise ValueError('Name of the stars not found')
    
    
    if not (pd.to_numeric(ra, errors="coerce").notna().all() and 
            pd.to_numeric(dec, errors="coerce").notna().all()
            ):
        raise ValueError("RA or DEC contains invalid values.")

    if file[[ra_col, dec_col, name_col]].isnull().any().any():
        raise ValueError("One or more required columns contain none values.")
    
    if mag_col:
        mag = file[mag_col]
        
        # Check if magnitude values are valid
        valid_mag = pd.to_numeric(mag, errors="coerce").notna().all()

        if not valid_mag:
            st.warning(
                "Warning: MAG column contains invalid or missing values.", width=290
             )
        
        # Always create DataFrame with mag column if it exists
        Data = pd.DataFrame({
            'star name': star_name,
            'ra': ra,
            'dec': dec,
            'mag': mag
        })
    else:
        Data = pd.DataFrame({
            'star name': star_name,
            'ra': ra,
            'dec': dec
        })
        
    del file
    return Data

@st.cache_data
def Observability(Data, _utc_shift,date, _Loc, timezone_local):

    date_str = date.strftime("%Y-%m-%d")

    #12 noon in local time zone
    time_in_local = Time( f"{date} 12:00:00")-_utc_shift 

    # time array covering next 24 hours in steps of 5 min
    elapsed = np.arange(0, (24*60)+5, 5)*u.min

    #time array of next 24 hours starting from noon cest
    time = time_in_local + elapsed 
    time_array=time[:,None]

    # Creating a series of coordinate frames in the AltAz system,
    # each one corresponding to a specific time from the time array
    # corresponding to a specific location given by obs

    frame_local_24h = AltAz(obstime=time[:,None], location=_Loc)
    Frame_Local_24h = AltAz(obstime=time, location=Loc)

    #Betelgeuse RA and DEC   

    Coordinates_of_the_stars=SkyCoord(ra=Data['ra'].values*u.deg, dec=Data['dec'].values*u.deg) 

    # transforms the declination and right ascension of the
    # star into altitudes and azimuths for the time sequence of frames defined

    Coordinates_local = Coordinates_of_the_stars[None, :].transform_to(frame_local_24h)

    # time-dependent coordinates of the Sun in equatorial system
    sun = get_sun(time)
    sun_local = sun.transform_to(Frame_Local_24h)

    # night time w.r.t to the location
    elapsed_night = elapsed[np.where(sun_local.alt < 0)]

    if len(elapsed_night)==0:

        raise ValueError('No night time detected for the given location at the given date')

    #Coordinates of the stars when sun is down
    Coord_local_sunset = Coordinates_local.alt[np.where(sun_local.alt < 0)]

    #Observabilty Duration
    Duration_of_Observabilty=[]

    for i in range(len(Coord_local_sunset[0])):

        if len(elapsed_night[Coord_local_sunset.transpose()[i]>0])>0:

            Duration_of_Observabilty.append((elapsed_night[Coord_local_sunset.transpose()[i]>0][-1]-
                                            elapsed_night[Coord_local_sunset.transpose()[i]>0][0]).to_value(u.min))
        else:
            Duration_of_Observabilty.append(0)

    Data['Visibility (min)']=Duration_of_Observabilty

    #Time of observability in Local timezone

    Observability_Time_Local=[]
    for i in range(len(Coord_local_sunset[0])):
        
        Observability_Time_Local.append(time_array[(Coordinates_local.alt.transpose()[i][:,None] > 0*u.deg)
                                            & (sun_local.alt[:, None] < 0*u.deg)].to_datetime(timezone=timezone_local))

    formatted_start=[]
    formatted_end=[]

    for dt in Observability_Time_Local:
        if len(dt) > 0:
            formatted_start.append(dt[0].strftime("%Y-%m-%d %H:%M"))
            formatted_end.append(dt[-1].strftime("%Y-%m-%d %H:%M"))
        else:
            formatted_start.append("Not visible")
            formatted_end.append("Not visible")

    Data['Visibility (start)'] = formatted_start
    Data['Visibility (end)'] = formatted_end

    return Data

def add_bg_from_local(image_file):
    with open(image_file, "rb") as f:
        encoded_string = base64.b64encode(f.read()).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{encoded_string}");
            background-size: contain;
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Adding bg image
add_bg_from_local("milkyway.jpg")

@st.cache_data
def Coordinates(lat, long):
    if is_numeric(lat) and is_numeric(long):

        try:

            tf = TimezoneFinder()
            Loc = EarthLocation(lat=float(lat), lon=float(long))
            tz_string = tf.timezone_at(lat=Loc.lat.deg, lng=Loc.lon.deg)
            timezone_local = ZoneInfo(tz_string)
            local_time = datetime.datetime.now(timezone_local)
            utc_shift_p = local_time.utcoffset().total_seconds() / 3600
            utc_shift = utc_shift_p * u.hour

            return utc_shift, Loc, timezone_local, tz_string, local_time, utc_shift_p

        except Exception as e:
            raise ValueError('Please enter valid latitude and longitude')
    else:
        raise ValueError('Please enter valid latitude and longitude')

# Create a container and center the inputs
container = st.container()

with container:
    cols = st.columns([0.2,0.266,0.266,0.266])  # Create 4 equal columns
    
    with cols[1]: 
        lat = st.text_input("Enter your latitude in signed DD format", key="lat")
    
    with cols[2]: 
        long = st.text_input("Enter your longitude in signed DD format", key="long")

    with cols[3]: 
        date=st.date_input("Select observation date")

    with cols[1]:

        if lat and long:
            try:
                utc_shift, Loc, timezone_local, tz_string, local_time, utc_shift_p = Coordinates(lat, long)
        
                st.write("Time zone:", tz_string)
                st.write("Local time:", local_time.strftime("%H:%M:%S"))
                st.write("UTC Shift:", utc_shift_p, "h")
        
                if tz_string.startswith("Etc/GMT"):
                    st.warning("Location may be a sea or desert", width=310)
        
            except Exception as e:
                st.error(str(e), width=309)

# Container for the file uploader

    Data=None

    with cols[1]:  # Second column for file uploader
        
        uploaded_file = st.file_uploader("Upload your star catalog file", type=["csv", "txt", "dat"])

        if uploaded_file is not None:
            try:

                Data = read_data(uploaded_file)
                st.session_state["Data"] = Data
                st.success("File Loaded Successfully", width=315)

            except Exception as e:

                st.error(f"{e}")

    with cols[2]:

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

    pcols = st.columns([0.2,0.266,0.266,0.266]) 

    if Data is not None and lat and long and is_numeric(lat) and is_numeric(long):

        with pcols[1]:

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

        with pcols[1]:
                
                if st.button('Calculate the time of observability'):
                    
                    try:
                        
                        Star_Observability = Observability(
                            st.session_state["Data"],
                            st.session_state["utc_shift"],
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

                        with pcols[2]:

                            if checkbox:
                                vspace(17) 
                                with st.expander("Observability preview", expanded=False, width=360):
                                    st.dataframe(filtered_data, height=212)
                            else:
                                vspace(8) 
                                with st.expander("Observability preview", expanded=False, width=360):
                                    st.dataframe(Star_Observability, height=212)

                    except Exception as e:
                        st.error(f'{e}')

