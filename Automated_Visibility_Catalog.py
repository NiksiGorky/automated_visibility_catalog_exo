import streamlit as st
from utils import add_bg_from_local

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

for key in ["Data", "Loc", "timezone_local", "Star_Observability"]:
    st.session_state.setdefault(key, None)

# Adding bg image
add_bg_from_local("milkyway.jpg")

pg = st.navigation([
    st.Page("Single_Star.py", title="Single Star Calculator"),
    st.Page("Multi_Star.py", title="Multi Star Calculator"),
])

pg.run()