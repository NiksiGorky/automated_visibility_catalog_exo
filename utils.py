import streamlit as st
import base64

from astropy.coordinates import SkyCoord, EarthLocation, AltAz, get_sun
import astropy.units as u
import numpy as np
import matplotlib.pyplot as plt
from astropy.time import Time

import pandas as pd

from timezonefinder import TimezoneFinder

from zoneinfo import ZoneInfo

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
    Frame_Local_24h = AltAz(obstime=time, location=_Loc)

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

def Observability_Single(ra, dec, _utc_shift,date, _Loc, timezone_local):

    date_str = date.strftime("%Y-%m-%d")

    #12 noon in local time zone
    time_in_local = Time( f"{date} 12:00:00")-_utc_shift 

    # time array covering next 24 hours in steps of 5 min
    elapsed = np.arange(0, (24*60)+5, 5)*u.min

    #time array of next 24 hours starting from noon cest
    time = time_in_local + elapsed 

    # Creating a series of coordinate frames in the AltAz system,
    # each one corresponding to a specific time from the time array
    # corresponding to a specific location given by obs

    frame_local_24h = AltAz(obstime=time, location=_Loc)

    #Betelgeuse RA and DEC   

    Coordinates_of_the_star=SkyCoord(ra=ra*u.deg, dec=dec*u.deg) 

    # transforms the declination and right ascension of the
    # star into altitudes and azimuths for the time sequence of frames defined

    Coordinates_local = Coordinates_of_the_star.transform_to(frame_local_24h)

    # time-dependent coordinates of the Sun in equatorial system
    sun = get_sun(time)
    sun_local = sun.transform_to(frame_local_24h)

    # night time w.r.t to the location
    elapsed_night = elapsed[np.where(sun_local.alt < 0)]

    if len(elapsed_night)==0:

        raise ValueError('No night time detected for the given location at the given date')

    #Coordinates of the stars when sun is down
    Coord_local_sunset = Coordinates_local.alt[np.where(sun_local.alt < 0)]

    #Observabilty Duration


    if len(elapsed_night[Coord_local_sunset>0])>0:

        Duration_of_Observabilty=((elapsed_night[Coord_local_sunset>0][-1]-
                                        elapsed_night[Coord_local_sunset>0][0]).to_value(u.min))
    else:
        Duration_of_Observabilty=0

    #Time of observability in Local timezone
    
    Observability_Time_Local=(time[(Coordinates_local.alt > 0*u.deg)
                                            & (sun_local.alt < 0*u.deg)].to_datetime(timezone=timezone_local))

    formatted=[]

    if len(Observability_Time_Local) > 0:
        formatted.append(Observability_Time_Local[0].strftime("%Y-%m-%d %H:%M"))
        formatted.append(Observability_Time_Local[-1].strftime("%Y-%m-%d %H:%M"))
    else:
        formatted.append("Not Visibile")

    plt.plot(elapsed.to(u.h), sun_local.alt, color='orange', label='Sun')
    plt.plot(elapsed.to(u.h), Coordinates_local.alt, color='red',
    linestyle=':', label='Star (daylight)')
    plt.plot(elapsed_night.to(u.h), Coord_local_sunset, color='red',
    label='Star (night)')

    plt.xlabel('Time from noon [h]')
    plt.xlim(0, 24)
    plt.xticks(np.arange(13)*2)
    plt.ylim(0,90)
    plt.ylabel('Altitude [deg]')
    plt.legend(loc='best')
    plt.title("Altitude vs Time")


    fig = plt.gcf()  
    plt.close()  

    return Duration_of_Observabilty, formatted, fig

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

@st.cache_data
def Coordinates(lat, long):
    if is_numeric(lat) and is_numeric(long):

        try:

            tf = TimezoneFinder()
            Loc = EarthLocation(lat=float(lat), lon=float(long))
            tz_string = tf.timezone_at(lat=Loc.lat.deg, lng=Loc.lon.deg)
            timezone_local = ZoneInfo(tz_string)

            return Loc, timezone_local, tz_string

        except Exception as e:
            raise ValueError('Please enter valid latitude and longitude')
    else:
        raise ValueError('Please enter valid latitude and longitude')