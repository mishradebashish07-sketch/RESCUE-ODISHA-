import streamlit as st
import folium
from streamlit_folium import st_folium
import requests

st.set_page_config(page_title="Odisha AI Disaster Response", layout="wide")

st.title("🌊 RESCUE ODISHA 🌊 ")
st.caption("Command Center for Zero-Casualty Rescue Dispatch | Innovate Odisha")

# --- SESSION STATE PERSISTENCE ---
if "dispatches" not in st.session_state:
    st.session_state.dispatches = []

# --- ODIA NLP HELPER ---
def analyze_distress_text(text: str):
    text_lower = text.lower()
    flood_keywords = ["ବନ୍ୟା", "ପାଣି", "banya", "pani", "flood", "water", "stranded", "drowning", "roof"]
    medical_keywords = ["ଡାକ୍ତରଖାନା", "ରକ୍ତ", "ଚିକିତ୍ସା", "doctor", "medical", "hospital", "injured", "aghata", "pregnant"]
    cyclone_keywords = ["ବାତ୍ୟା", "ଝଡ଼", "cyclone", "wind", "shelter", "ashraya"]

    if any(k in text_lower for k in flood_keywords):
        return "flood_evacuation", 5
    elif any(k in text_lower for k in medical_keywords):
        return "medical_emergency", 4
    elif any(k in text_lower for k in cyclone_keywords):
        return "cyclone_shelter", 3
    return "general_alert", 3

# --- SIDEBAR INTERFACE ---
st.sidebar.header("🚨 Report Citizen SOS")

demo_choice = st.sidebar.selectbox(
    "Load Demo Scenario:",
    [
        "Custom Input",
        "Baleswar Coastal Flood (Odia)",
        "Cuttack River Overflow (English)",
        "Ganjam Medical Evacuation"
    ]
)

if demo_choice == "Baleswar Coastal Flood (Odia)":
    default_msg = "ଘରେ ବନ୍ୟା ପାଣି ପଶିଯାଇଛି, ଛାତ ଉପରେ ୪ ଜଣ ଫସିଛନ୍ତି (Water entered house, 4 trapped on roof)"
    default_lat, default_lon = 21.4700, 86.9300
elif demo_choice == "Cuttack River Overflow (English)":
    default_msg = "Mahanadi water level breached embankment, need urgent boat rescue."
    default_lat, default_lon = 20.4850, 85.8800
elif demo_choice == "Ganjam Medical Evacuation":
    default_msg = "Elderly patient injured during storm, urgently requires medical support."
    default_lat, default_lon = 19.3600, 84.9900
else:
    default_msg = "Severe waterlogging, roof rescue needed."
    default_lat, default_lon = 21.4700, 86.9300

contact = st.sidebar.text_input("Reporter Phone", value="+919876543210")
msg = st.sidebar.text_area("Distress Details (English / Odia)", value=default_msg)

auto_cat, auto_sev = analyze_distress_text(msg)

category = st.sidebar.selectbox(
    "Category (Auto-Detected)",
    ["flood_evacuation", "medical_emergency", "cyclone_shelter", "general_alert"],
    index=["flood_evacuation", "medical_emergency", "cyclone_shelter", "general_alert"].index(auto_cat)
)
severity = st.sidebar.slider("Severity Level (1-5)", 1, 5, auto_sev)
lat = st.sidebar.number_input("Latitude", value=default_lat, format="%.4f")
lon = st.sidebar.number_input("Longitude", value=default_lon, format="%.4f")

# --- LIVE RENDER BACKEND URL ---
API_BASE = "https://rescue-odisha.onrender.com"

# Known units and coordinates
odraf_units = [
    {"name": "ODRAF Unit 3 (Inflatable Boat Team)", "loc": [21.4800, 86.9100]},
    {"name": "ODRAF Unit 1 (Bhubaneswar Rapid Action)", "loc": [20.2961, 85.8200]}
]

shelters = [
    {"name": "Chandipur Cyclone Shelter (Baleswar)", "loc": [21.4680, 87.0130]},
    {"name": "Barabati Multipurpose Shelter (Cuttack)", "loc": [20.4812, 85.8732]},
    {"name": "Chhatrapur Relief Camp (Ganjam)", "loc": [19.3550, 84.9920]}
]

# --- ACTION BUTTONS ---
if st.sidebar.button("Dispatch SOS & Run Triage"):
    payload = {
        "reporter_contact": contact,
        "message": msg,
        "latitude": lat,
        "longitude": lon,
        "category": category,
        "severity_score": severity
    }
    try:
        res = requests.post(f"{API_BASE}/sos/triage", json=payload)
        if res.status_code == 201:
            data = res.json()
            st.sidebar.success(f"Status: {data['status']}")
            
            st.session_state.dispatches.append({
                "lat": lat,
                "lon": lon,
                "msg": msg,
                "team": data.get("assigned_team"),
                "shelter": data.get("nearest_shelter")
            })
        else:
            st.sidebar.error(f"Error {res.status_code}: {res.text}")
    except Exception as e:
        st.sidebar.error(f"Backend connection failed: {e}")

st.sidebar.markdown("---")

# Reset Responder Units Button (Calls the FastAPI endpoint)
if st.sidebar.button("🔄 Reset Responder Availability"):
    try:
        r = requests.post(f"{API_BASE}/responders/reset")
        if r.status_code == 200:
            st.sidebar.success("All ODRAF teams are now available!")
        else:
            st.sidebar.error("Could not reset responders.")
    except Exception as e:
        st.sidebar.error(f"Failed to reset: {e}")

if st.sidebar.button("🧹 Clear Map Alerts"):
    st.session_state.dispatches = []
    st.rerun()

# --- BUILD MAP ---
m = folium.Map(location=[20.65, 86.0], zoom_start=8)

# 1. Base Shelters (Green)
for s in shelters:
    folium.Marker(
        s["loc"],
        popup=s["name"],
        tooltip=s["name"],
        icon=folium.Icon(color="green", icon="home")
    ).add_to(m)

# 2. Base ODRAF Units (Blue)
for r in odraf_units:
    folium.Marker(
        r["loc"],
        popup=r["name"],
        tooltip=r["name"],
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)

# 3. Dispatches & Route Lines
for item in st.session_state.dispatches:
    # Red Distress Flag
    folium.Marker(
        [item["lat"], item["lon"]],
        popup=f"🚨 SOS: {item['msg']}",
        tooltip="Active Emergency Call",
        icon=folium.Icon(color="red", icon="flag")
    ).add_to(m)

    # Route from ODRAF unit to SOS site
    if item["team"]:
        assigned_name = item["team"]["team_name"].lower()
        unit = next((u for u in odraf_units if u["name"].lower().split()[0] in assigned_name or assigned_name in u["name"].lower()), None)
        if unit:
            dist_km = item["team"]["distance_km"]
            folium.PolyLine(
                locations=[unit["loc"], [item["lat"], item["lon"]]],
                color="blue",
                weight=4,
                opacity=0.85,
                tooltip=f"ODRAF Route: {item['team']['team_name']} ({dist_km} km)"
            ).add_to(m)

            # Midpoint distance label badge
            mid_lat = (unit["loc"][0] + item["lat"]) / 2
            mid_lon = (unit["loc"][1] + item["lon"]) / 2
            folium.Marker(
                [mid_lat, mid_lon],
                icon=folium.DivIcon(
                    html=f"""<div style="font-size: 11px; font-weight: bold; background: white; padding: 2px 6px; border: 1px solid blue; border-radius: 4px; color: blue;">
                                🚤 {dist_km} km
                             </div>"""
                )
            ).add_to(m)

    # Route from SOS site to Shelter
    if item["shelter"]:
        assigned_sh = item["shelter"]["name"].lower()
        sh = next((s for s in shelters if s["name"].lower().split()[0] in assigned_sh or assigned_sh in s["name"].lower()), None)
        if sh:
            dist_km = item["shelter"]["distance_km"]
            # 1. Dashed evacuation line
            folium.PolyLine(
                locations=[[item["lat"], item["lon"]], sh["loc"]],
                color="green",
                weight=3,
                dash_array="6, 8",
                tooltip=f"Evacuation Route: {item['shelter']['name']} ({dist_km} km)"
            ).add_to(m)

            # 2. Midpoint badge showing distance to shelter
            mid_lat_sh = (sh["loc"][0] + item["lat"]) / 2
            mid_lon_sh = (sh["loc"][1] + item["lon"]) / 2
            folium.Marker(
                [mid_lat_sh, mid_lon_sh],
                icon=folium.DivIcon(
                    html=f"""<div style="font-size: 11px; font-weight: bold; background: #E8F5E9; padding: 2px 6px; border: 1px solid #2E7D32; border-radius: 4px; color: #2E7D32;">
                                🏠 {dist_km} km to Shelter
                             </div>"""
                )
            ).add_to(m)
            
# Display Map
st_folium(m, width=1100, height=580, key=f"map_{len(st.session_state.dispatches)}")
