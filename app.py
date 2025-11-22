import streamlit as st
import pandas as pd
import pydeck as pdk
from geopy.distance import geodesic
from gtts import gTTS
import io
import requests
import polyline

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
        
        layers = []
        view_state = pdk.ViewState(latitude=48.137, longitude=11.575, zoom=13, pitch=45)

        # mode 1 -> guided path (Proaktiver Modus)
        if st.session_state.user_mode == "Guided":
            st.caption("Follow the blue line to reach your Target.")
            
            if not filtered_df.empty:
                # optimize the nodes
                filtered_df = optimize_route_ordering(filtered_df)
                
                # Calculate Route
                route_points = list(zip(filtered_df['lat'], filtered_df['lon']))
                real_path = get_osrm_route(route_points)
                
                # The Path
                layers.append(pdk.Layer(
                    "PathLayer",
                    data=[{"path": real_path}],
                    get_path="path",
                    get_color='[0, 150, 255, 200]',
                    width_scale=10,
                    width_min_pixels=3
                ))
                
                # Numbered Points
                filtered_df['idx'] = range(1, len(filtered_df) + 1)
                layers.append(pdk.Layer(
                    "ScatterplotLayer",
                    filtered_df,
                    get_position='[lon, lat]',
                    get_color='[255, 255, 255]',
                    get_line_color='[0, 150, 255]',
                    get_line_width=20,
                    get_radius=60,
                    pickable=True
                ))
                layers.append(pdk.Layer(
                    "TextLayer",
                    filtered_df,
                    get_position='[lon, lat]',
                    get_text='idx',
                    get_color=[0, 0, 0],
                    get_size=18,
                    get_alignment_baseline="'center'"
                ))
                
                # Center map on first point
                view_state.latitude = filtered_df.iloc[0]['lat']
                view_state.longitude = filtered_df.iloc[0]['lon']

        # mode 2 -> spontaneuos (explore as you go)
        else:
            st.caption("Use the Slider to move, the places should appear if you get close to them!")
            
            # Two sliders
            col_nav1, col_nav2 = st.columns(2)
            with col_nav1:
                lat_val = st.slider("↕️ Nord-Süd", 0, 100, 50)
            with col_nav2:
                lon_val = st.slider("↔️ West-Ost", 0, 100, 50)
            
            # User Position (Ursprung: Marienplatz Center)
            user_lat = 48.1370 + ((lat_val - 50) * 0.0004)
            user_lon = 11.5750 + ((lon_val - 50) * 0.0006)
            
            # Check Proximity Logic
            nearby_place = None
            for _, row in filtered_df.iterrows():
                if geodesic((row['lat'], row['lon']), (user_lat, user_lon)).km < 0.25: # 250m radius
                    nearby_place = row
                    if row['name'] not in st.session_state.visited:
                        st.session_state.visited.append(row['name'])
            
            # Layer 1: User Avatar
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                data=[{"lon": user_lon, "lat": user_lat}],
                get_position='[lon, lat]',
                get_color='[0, 150, 255, 150]',
                get_radius=100, 
            ))
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                data=[{"lon": user_lon, "lat": user_lat}],
                get_position='[lon, lat]',
                get_color='[255, 255, 255, 255]',
                get_radius=30, 
            ))

            # Discovered points (Green)
            discovered_df = filtered_df[filtered_df['name'].isin(st.session_state.visited)]
            if not discovered_df.empty:
                layers.append(pdk.Layer(
                    "ScatterplotLayer",
                    discovered_df,
                    get_position='[lon, lat]',
                    get_color='[0, 255, 100, 200]',
                    get_radius=60,
                    pickable=True
                ))
            
            # follow user as they move
            view_state.latitude = user_lat
            view_state.longitude = user_lon
            view_state.zoom = 15
            view_state.bearing = 0

            # Notifications
            if nearby_place is not None:
                st.success(f"Found: {nearby_place['name']}!")
                if st.button("🔊 Listen the information"):
                    aud = text_to_speech(nearby_place['desc'])
                    if aud: st.audio(aud, format='audio/mp3')

        # Map
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

        # LIST OF STOPS 
        if st.session_state.user_mode == "Guided":
            st.markdown("### Your route")
            for i, row in filtered_df.iterrows():
                with st.expander(f"{i+1}. {row['name']}"):
                    st.write(row['desc'])
                    if st.button("🔊 Audio", key=f"btn_{i}"):
                        aud = text_to_speech(row['desc'])
                        if aud: st.audio(aud, format='audio/mp3')