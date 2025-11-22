import streamlit as st
import pandas as pd
import pydeck as pdk
from geopy.distance import geodesic
from gtts import gTTS
import io
import requests
import polyline
from streamlit_js_eval import get_geolocation
import time 

# --- CONFIGURATION ---
st.set_page_config(page_title="CityTour Munich", layout="centered")

# MAPBOX TOKEN
MAPBOX_API_KEY = "" 

# CSS (DARK MODE) 
st.markdown("""
    <style>
    /* Dark Mode Backgrounds */
    .stApp { background-color: #1b1b1c; }
    
    /* Mobile-like Container */
    .main .block-container {
        max-width: 500px; 
        padding-top: 2rem;
        padding-bottom: 2rem;
        background-color: #2f2e30; 
        border-radius: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        margin: 0 auto;
        color: white; 
    }
    
    /* Text Colors */
    h1, h2, h3, p, span, div, label, .stMarkdown, .stRadio { color: #ffffff !important; }
    
    /* Input Fields */
    .stTextInput input { background-color: #3d3d3d; color: white; border: none; }
    .stMultiSelect div[data-baseweb="select"] > div { background-color: #3d3d3d; color: white; }
    
    /* Hide Header */
    header {visibility: hidden;}
    
    /* Buttons */
    div.stButton > button {
        border-radius: 25px;
        padding: 0.5rem 1rem;
        background-color: #444444; 
        color: white;
        border: 1px solid #555555;
        width: 100%;
    }
    div.stButton > button:hover {
        border-color: #00aaff;
        color: #00aaff;
    }
    </style>
""", unsafe_allow_html=True)


if "setup_complete" not in st.session_state:
    st.session_state.setup_complete = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "user_interests" not in st.session_state:
    st.session_state.user_interests = []
if "user_mode" not in st.session_state:
    st.session_state.user_mode = ""
if "visited" not in st.session_state:
    st.session_state.visited = []

# Initialize last known location (Prevents map flickering)
if "last_lat" not in st.session_state:
    st.session_state.last_lat = 48.1370 
if "last_lon" not in st.session_state:
    st.session_state.last_lon = 11.5750 

# getting data
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("places-in-munich.csv")
        return df
    except FileNotFoundError:
        return pd.DataFrame()

df = load_data()


def text_to_speech(text):
    try:
        tts = gTTS(text=text, lang='en')
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        return audio_fp
    except:
        return None

@st.cache_data
def get_osrm_route(locations):
    if not locations: return []
    try:
        loc_string = ";".join([f"{lon},{lat}" for lat, lon in locations])
        url = f"http://router.project-osrm.org/route/v1/foot/{loc_string}?overview=full&geometries=polyline"
        r = requests.get(url, timeout=2)
        if r.status_code == 200:
            res = r.json()
            encoded = res['routes'][0]['geometry']
            decoded = polyline.decode(encoded)
            return [[lon, lat] for lat, lon in decoded]
    except:
        pass
    return [[lon, lat] for lat, lon in locations]

def optimize_route_ordering(df):
    """
    Start point: Closest to Marienplatz.
    Next point: Closest unvisited neighbor.
    """
    if len(df) < 3:
        return df
        
    points = df.to_dict('records')
    
    marienplatz = (48.1372, 11.5755)
    start_node = min(points, key=lambda p: geodesic((p['lat'], p['lon']), marienplatz).km)
    
    # Greedy Algorithm
    ordered_path = [start_node]
    points.remove(start_node)
    
    while points:
        current = ordered_path[-1]
        nearest = min(points, key=lambda p: geodesic((current['lat'], current['lon']), (p['lat'], p['lon'])).km)
        ordered_path.append(nearest)
        points.remove(nearest)
        
    return pd.DataFrame(ordered_path)

# WELCOME SCREEN (SETUP)
if not st.session_state.setup_complete:
    st.title("Heyy, Welcome!")
    st.subheader("Build your personal Munich Experience")

    st.session_state.user_name = st.text_input(
        "How should we call you?", placeholder="Your name"
    )

    st.markdown("### What are we exploring today")
    
    # CSV catagories
    available_categories = list(df['category'].unique()) if not df.empty else []
    
    st.session_state.user_interests = st.multiselect(
        "What are your interests?",
        available_categories,
        default=available_categories[:1]
    )

    st.markdown("### Modus")
    mode_selection = st.radio(
        "How would like to sightsee?",
        ["🧭 Automatic route built just for you!",
         "🎲 Explore freely as you go!"]
    )
    
    # Map the long text to simple internal keys
    if "Automatic" in mode_selection:
        st.session_state.user_mode = "Guided"
    else:
        st.session_state.user_mode = "Spontaneous"

    st.write("---")

    if st.button("Let's go!"):
        if st.session_state.user_name == "":
            st.warning("Please enter your name 😊")
        elif len(st.session_state.user_interests) == 0:
            st.warning("Please choose at least one interest 😊")
        else:
            st.session_state.setup_complete = True
            st.success("Perfect! We are preparing your map...")
            st.rerun()

# MAIN APP (AFTER SETUP)
else:
    if df.empty:
        st.error("CSV not found! Please check places-in-munich.csv")
    else:
        # filter input 
        filtered_df = df[df['category'].isin(st.session_state.user_interests)].copy()
        
        # Reset Button (Top Right logic via Expander)
        with st.expander(f"👤 Profil: {st.session_state.user_name}", expanded=False):
            st.write(f"**Interests:** {', '.join(st.session_state.user_interests)}")
            st.write(f"**Mode:** {st.session_state.user_mode}")
            if st.button("Reset Profile"):
                st.session_state.setup_complete = False
                st.session_state.visited = []
                st.rerun()

        st.markdown(f"## Your Munich Walk")

        # GPS Toggle 
        use_gps = st.toggle("🛰️ Use Real GPS", value=False)
        
        @st.fragment(run_every=3 if use_gps else None)
        def view_map_logic(filtered_df):
            # start location 
            user_lat = st.session_state.last_lat 
            user_lon = st.session_state.last_lon

            if use_gps:
                # --- FIXED GPS LOGIC ---
                # 1. Init key if needed
                if 'gps_key' not in st.session_state:
                    st.session_state.gps_key = f"gps_{time.time()}"
                
                # 2. Ask for location using CURRENT key
                loc = get_geolocation(component_key=st.session_state.gps_key)
                
                if loc:
                    user_lat = loc['coords']['latitude']
                    user_lon = loc['coords']['longitude']
                    # Save valid location
                    st.session_state.last_lat = user_lat
                    st.session_state.last_lon = user_lon
                    
                    # 3. ONLY NOW generate new key for NEXT update
                    st.session_state.gps_key = f"gps_{time.time()}"
                    st.toast(f" GPS Updated", icon="📡")
                else:
                    # If None, it means "Waiting for phone to answer".
                    # DO NOT change the key here, or we lose the answer!
                    st.warning("Waiting for GPS...")
            else:
                st.caption("Simulation Mode: Use sliders to move.") 
                col_nav1, col_nav2 = st.columns(2)
                with col_nav1:
                    lat_val = st.slider("↕️ North-South", 0, 100, 50)
                with col_nav2:
                    lon_val = st.slider("↔️ West-East", 0, 100, 50)
                
                user_lat = 48.1370 + ((lat_val - 50) * 0.0004)
                user_lon = 11.5750 + ((lon_val - 50) * 0.0006)
                
                st.session_state.last_lat = user_lat
                st.session_state.last_lon = user_lon

            
            layers = []
            view_state = pdk.ViewState(latitude=user_lat, longitude=user_lon, zoom=17, pitch=45)

            # User Avatar Layer
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                data=[{"lon": user_lon, "lat": user_lat}],
                get_position='[lon, lat]',
                get_color='[0, 128, 255, 200]', 
                get_radius=3, 
            ))
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                data=[{"lon": user_lon, "lat": user_lat}],
                get_position='[lon, lat]',
                get_color='[255, 255, 255, 255]',
                get_radius=1, 
            ))

            # mode 1 -> guided path (Proaktiver Modus)
            if st.session_state.user_mode == "Guided":
                st.caption("Follow the blue line to reach your Target.")
                
                if not filtered_df.empty:
                    # Optimize Route
                    df_opt = optimize_route_ordering(filtered_df)
                    
                    route_points = list(zip(df_opt['lat'], df_opt['lon']))
                    
                    # Connect user to route
                    if use_gps or True: 
                        route_points.insert(0, (user_lat, user_lon))

                    real_path = get_osrm_route(route_points)
                    
                    layers.append(pdk.Layer(
                        "PathLayer",
                        data=[{"path": real_path}],
                        get_path="path",
                        get_color='[0, 150, 255, 200]',
                        width_scale=5,
                        width_min_pixels=3
                    ))
                    
                    df_opt['idx'] = range(1, len(df_opt) + 1)
                    layers.append(pdk.Layer(
                        "ScatterplotLayer",
                        df_opt,
                        get_position='[lon, lat]',
                        get_color='[255, 255, 255]',
                        get_line_color='[0, 150, 255]',
                        get_line_width=20,
                        get_radius=5,
                        pickable=True
                    ))
                    layers.append(pdk.Layer(
                        "TextLayer",
                        df_opt,
                        get_position='[lon, lat]',
                        get_text='idx',
                        get_color=[0, 0, 0],
                        get_size=14,
                        get_alignment_baseline="'center'"
                    ))

            # mode 2 -> spontaneuos (explore as you go)
            else:
                st.caption("Use the Slider to move, places appear when you get close!")
                nearby_place = None
                for _, row in filtered_df.iterrows():
                    if geodesic((row['lat'], row['lon']), (user_lat, user_lon)).km < 0.15:
                        nearby_place = row
                        if row['name'] not in st.session_state.visited:
                            st.session_state.visited.append(row['name'])
                
                discovered_df = filtered_df[filtered_df['name'].isin(st.session_state.visited)]
                if not discovered_df.empty:
                    layers.append(pdk.Layer(
                        "ScatterplotLayer",
                        discovered_df,
                        get_position='[lon, lat]',
                        get_color='[0, 255, 100, 200]',
                        get_radius=5,
                        pickable=True
                    ))

                if nearby_place is not None:
                    st.success(f"Found: {nearby_place['name']}!")
                    if st.button("🔊 Listen the information"):
                        aud = text_to_speech(nearby_place['desc'])
                        if aud: st.audio(aud, format='audio/mp3')

            # Render Map
            if MAPBOX_API_KEY:
                map_style = "mapbox://styles/mapbox/dark-v10"
                api_keys = {"mapbox": MAPBOX_API_KEY}
            else:
                map_style = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json" 
                api_keys = None

            st.pydeck_chart(pdk.Deck(
                map_style=map_style,
                initial_view_state=view_state,
                layers=layers,
                api_keys=api_keys,
                tooltip={"text": "{name}"}
            ), height=400) 

        # CALL THE FRAGMENTp
        

        # LIST OF STOPS (Outside fragment)
        if st.session_state.user_mode == "Guided":
            st.markdown("### Your route")
            for i, row in filtered_df.iterrows():
                with st.expander(f"{i+1}. {row['name']}"):
                    st.write(row['desc'])
                    if st.button("🔊 Audio", key=f"btn_{i}"):
                        aud = text_to_speech(row['desc'])
                        if aud: st.audio(aud, format='audio/mp3')