import streamlit as st
import pandas as pd
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="TestTrack Pro Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# API base URL
API_URL = os.getenv("API_URL", "http://localhost:8000/api")

# Title
st.title("📊 TestTrack Pro Dashboard")

# Sidebar
with st.sidebar:
    st.header("Navigation")
    page = st.radio("Select Page", ["Home", "Analytics", "Settings"])

# Main content
if page == "Home":
    st.header("Welcome to TestTrack Pro")
    
    # Check backend health
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            st.success("✅ Backend is healthy")
        else:
            st.error("❌ Backend is not responding")
    except Exception as e:
        st.error(f"❌ Cannot connect to backend: {str(e)}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Tests", 150)
    with col2:
        st.metric("Pass Rate", "92%")
    with col3:
        st.metric("Active Sessions", 23)

elif page == "Analytics":
    st.header("Analytics")
    st.info("Analytics page will be implemented here")
    
    # Sample chart
    data = {
        "Day": ["Mon", "Tue", "Wed", "Thu", "Fri"],
        "Tests": [45, 52, 48, 61, 55]
    }
    df = pd.DataFrame(data)
    st.line_chart(df.set_index("Day"))

elif page == "Settings":
    st.header("Settings")
    st.info("Settings page will be implemented here")
    
    api_url = st.text_input("API URL", value=API_URL)
    if st.button("Save Settings"):
        st.success("Settings saved!")
