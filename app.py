import streamlit as st
import requests
import folium
from streamlit_folium import st_folium

# --- UPDATED: Your Live Render Backend URL ---
BASE_URL = "https://rescue-odisha.onrender.com"

st.title("Spatial Triage & SOS Dispatch System")

# Example: Submitting SOS Data to your Cloud Backend
with st.form("sos_form"):
    st.subheader("Dispatch SOS")
    name = st.text_input("Name")
    latitude = st.number_input("Latitude", format="%.6f")
    longitude = st.number_input("Longitude", format="%.6f")
    severity = st.selectbox("Emergency Level", ["High", "Medium", "Low"])
    
    submitted = st.form_submit_button("Dispatch SOS & Run Triage")
    
    if submitted:
        payload = {
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "severity": severity
        }
        
        # Send data to Render instead of localhost
        try:
            response = requests.post(f"{BASE_URL}/api/v1/sos/triage", json=payload)
            if response.status_code == 200:
                st.success("SOS Dispatched Successfully to Cloud Server!")
            else:
                st.error(f"Error: {response.text}")
        except Exception as e:
            st.error(f"Failed to connect to backend: {e}")

# Example: Fetching and Mapping Data from your Cloud Backend
st.subheader("Live Rescue Map")
try:
    # Fetch triage data from Render
    map_data_response = requests.get(f"{BASE_URL}/api/v1/sos/locations")
    
    if map_data_response.status_code == 200:
        locations = map_data_response.json()
        
        # Draw Map
        m = folium.Map(location=[20.296, 85.824], zoom_start=7) # Centered on Odisha
        for loc in locations:
            folium.Marker(
                [loc['latitude'], loc['longitude']], 
                popup=f"{loc['name']} - {loc['severity']}"
            ).add_to(m)
            
        st_folium(m, width=700, height=500)
except Exception as e:
    st.warning("Waiting for data from cloud server...")