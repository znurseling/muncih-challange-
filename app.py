import streamlit as st
import pandas as pd
import pydeck as pdk
from geopy.distance import geodesic
from gtts import gTTS
import io
import requests
import polyline

from fetch_air_quality import fetch_air_quality
from pm25_to_score import pm25_to_score

# Clear cache only once at startup, not continuously
if 'cache_cleared' not in st.session_state:
    st.cache_data.clear()
    st.session_state.cache_cleared = True

# --- CONFIGURATION ---
st.set_page_config(page_title="CityTour Munich", layout="centered")

# MAPBOX TOKEN
MAPBOX_API_KEY = ""

# === IMAGE MAPPING - INSERT YOUR IMAGE URLS HERE ===
LANDMARK_IMAGES = {
    "Eisbachwelle": "https://a.travel-assets.com/findyours-php/viewfinder/images/res40/195000/195001.jpg",  # Insert image URL for Eisbachwelle
    "Monopteros": "https://www.muenchen.de/sites/default/files/styles/3_2_w1216/public/2022-06/210108_monopteros-herbst_Mde-MichaelHofmann.jpg.webp",  # Insert image URL for Monopteros
    "Friedensengel": "https://de.wikipedia.org/wiki/Datei:M%C3%BCnchen_-_Friedensengel_mit_Font%C3%A4ne_(tone-mapping).jpg",  # Insert image URL for Friedensengel
    "Chinesischer Turm": "https://www.muenchen.de/sites/default/files/styles/3_2_w1216/public/2022-06/20201204-kocherlball-4-3.jpg.webp",  # Insert image URL for Chinesischer Turm
    "Viktualienmarkt": "https://www.travelguide.de/media/1200x800/muenchen-viktualienmarkt-1200x800.avif",  # Insert image URL for Viktualienmarkt
    # more landmarks
    #"Pinakothek der Moderne": "YOUR_IMAGE_URL_HERE",
    #"Deutsches Museum": "YOUR_IMAGE_URL_HERE",
    # etc...
}

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
    
    /* Landmark Image Styling */
    .landmark-image {
        border-radius: 15px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        margin: 10px 0;
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

from landmarks import landmark_list
import time

@st.cache_data
def load_air_quality_data():
    try:
        df = pd.read_csv("air_quality_stations.csv")
        return df
    except FileNotFoundError:
        return pd.DataFrame()

df = load_data()
aq_df = load_air_quality_data()

# Debug output
print(f"DEBUG: Places loaded: {len(df)}")
print(f"DEBUG: Air quality stations loaded: {len(aq_df)}")
if not aq_df.empty:
    print(f"DEBUG: AQ columns: {aq_df.columns.tolist()}")


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
        default=available_categories[:1] if available_categories else []
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

        # Toggle for Air Quality Layer
        show_aq = st.checkbox("🌫️ Show Air Quality Stations", value=True)

        layers = []
        view_state = pdk.ViewState(latitude=48.137, longitude=11.575, zoom=13, pitch=45)

        # mode 1 -> guided path (Proaktiver Modus)
        if st.session_state.user_mode == "Guided":
            st.caption("Follow the blue line to reach your Target.")

            if not filtered_df.empty:
                # optimize the nodes
                filtered_df = optimize_route_ordering(filtered_df)

                # Fetch air quality data for each location
                for idx, row in filtered_df.iterrows():
                    aq_data = fetch_air_quality(row['lat'], row['lon'])
                    if aq_data:
                        filtered_df.at[idx, 'pm25'] = aq_data.get('pm25', 0)
                        filtered_df.at[idx, 'pm10'] = aq_data.get('pm10', 0)
                        filtered_df.at[idx, 'no2'] = aq_data.get('no2', 0)
                        filtered_df.at[idx, 'air_quality'] = pm25_to_score(filtered_df.at[idx, 'pm25'])
                    else:
                        filtered_df.at[idx, 'pm25'] = 0
                        filtered_df.at[idx, 'pm10'] = 0
                        filtered_df.at[idx, 'no2'] = 0
                        filtered_df.at[idx, 'air_quality'] = 50

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
                    get_color="[noise_level * 2.5, (100 - noise_level) * 2.5, 50, 200]",
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

        # Add Air Quality Grid Layer (for both modes)
        if show_aq and not aq_df.empty:
            aq_df_copy = aq_df.copy()

            # Color mapping for PM2.5 levels
            def get_color_for_pm25(pm25):
                if pm25 < 12:
                    return [0, 220, 100, 80]  # Green - Good
                elif pm25 < 35:
                    return [255, 220, 0, 80]  # Yellow - Moderate
                elif pm25 < 55:
                    return [255, 140, 0, 80]  # Orange - Unhealthy for Sensitive
                else:
                    return [255, 50, 50, 80]  # Red - Unhealthy

            aq_df_copy['color'] = aq_df_copy['pm25'].apply(get_color_for_pm25)

            # Create grid cells using ColumnLayer for fixed visible grid
            layers.append(pdk.Layer(
                "ColumnLayer",
                aq_df_copy,
                get_position='[lon, lat]',
                get_elevation='pm25 * 50',  # Height based on PM2.5
                elevation_scale=1,
                radius=400,  # Size of each grid cell
                get_fill_color='color',
                pickable=True,
                auto_highlight=True,
                extruded=True,
                coverage=1,
                opacity=0.01
            ))

            # Add grid borders/outlines for better visibility
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                aq_df_copy,
                get_position='[lon, lat]',
                get_fill_color='[50, 50, 50, 0]',  # Transparent fill
                get_line_color='[255, 255, 255, 180]',  # White border
                get_radius=400,
                line_width_min_pixels=2,
                stroked=True,
                filled=False,
                pickable=True
            ))

            # Add text labels showing PM2.5 values on each grid cell
            layers.append(pdk.Layer(
                "TextLayer",
                aq_df_copy,
                get_position='[lon, lat]',
                get_text='pm25',
                get_color=[255, 255, 255, 255],
                get_size=14,
                get_alignment_baseline="'center'",
                get_pixel_offset=[0, 0],
                billboard=True
            ))

        # mode 2 -> spontaneuos (explore as you go)
        else:
            st.caption("Use the Slider to move, the places should appear if you get close to them!")

            # Two sliders
            col_nav1, col_nav2 = st.columns(2)
            with col_nav1:
                lat_val = st.slider("↕️ Nord-Süd", 0, 100, 50, key='lat_slider')
            with col_nav2:
                lon_val = st.slider("↔️ West-Ost", 0, 100, 50, key='lon_slider')

            # User Position (Ursprung: Marienplatz Center)
            user_lat = 48.1370 + ((lat_val - 50) * 0.0004)
            user_lon = 11.5750 + ((lon_val - 50) * 0.0006)

            # Init last update wenn nicht vorhanden
            if 'last_landmark_update' not in st.session_state:
                st.session_state.last_landmark_update = 0

            current_time = time.time()

            if current_time - st.session_state.last_landmark_update > 15:
                for lm in landmark_list:
                    lm.get_scaled_radius(user_lat, user_lon)  # Trigger berechnung
                st.session_state.last_landmark_update = current_time

            # Check Proximity Logic
            nearby_place = None
            for _, row in filtered_df.iterrows():
                if geodesic((row['lat'], row['lon']), (user_lat, user_lon)).km < 0.25: # 250m radius
                    # Create a copy of the row as a dict to avoid Series reference issues
                    nearby_place = row.to_dict()

                    if row['name'] not in st.session_state.visited:
                        st.session_state.visited.append(row['name'])

                    # Fetch air quality data for the nearby place
                    aq_data = fetch_air_quality(row['lat'], row['lon'])
                    if aq_data:
                        nearby_place['pm25'] = aq_data.get('pm25', 0)
                        nearby_place['pm10'] = aq_data.get('pm10', 0)
                        nearby_place['no2'] = aq_data.get('no2', 0)
                        nearby_place['air_quality'] = pm25_to_score(nearby_place['pm25'])
                    else:
                        nearby_place['pm25'] = 0
                        nearby_place['pm10'] = 0
                        nearby_place['no2'] = 0
                        nearby_place['air_quality'] = 50

                    break  # Stop after finding the first nearby place

            # Layer 1: User Avatar
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                data=[{"lon": user_lon, "lat": user_lat, "noise_level": 50}],
                get_position='[lon, lat]',
                get_color="[100, 150, 255, 220]",
                get_radius=100,
            ))
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                data=[{"lon": user_lon, "lat": user_lat, "noise_level": 50}],
                get_position='[lon, lat]',
                get_color="[0, 150, 255, 220]",
                get_radius=30,
            ))

            # Discovered points (Green)
            discovered_df = filtered_df[filtered_df['name'].isin(st.session_state.visited)]
            if not discovered_df.empty:
                layers.append(pdk.Layer(
                    "ScatterplotLayer",
                    discovered_df,
                    get_position='[lon, lat]',
                    get_color="[100, 200, 100, 220]",
                    get_radius=60,
                    pickable=True
                ))

            # follow user as they move
            view_state.latitude = user_lat
            view_state.longitude = user_lon
            view_state.zoom = 15
            view_state.bearing = 0

            # === NOTIFICATIONS WITH IMAGES ===
            if nearby_place is not None:
                st.success(f"Found: {nearby_place['name']}!")

                # Create two columns: one for image, one for info
                col_img, col_info = st.columns([1, 1])

                with col_img:
                    # Display image if available in the mapping
                    place_name = nearby_place['name']
                    if place_name in LANDMARK_IMAGES and LANDMARK_IMAGES[place_name] != "YOUR_IMAGE_URL_HERE":
                        st.markdown(
                            f'<img src="{LANDMARK_IMAGES[place_name]}" class="landmark-image" width="100%">',
                            unsafe_allow_html=True
                        )
                    else:
                        # Placeholder if no image is set
                        st.info("https://upload.wikimedia.org/wikipedia/commons/d/d8/DEU_M%C3%BCnchen_COA.svg")

                with col_info:
                    st.markdown(f"""
                    **Umwelt-Info:**  
                    - Lärm: {nearby_place.get('noise_level', 'N/A')} 🔊  
                    - Luftqualität: {nearby_place.get('air_quality', 'N/A')} 🌫️  
                    - Schatten: {nearby_place.get('shade_score', 'N/A')} 🌳  
                    - Barrierefreiheit: {nearby_place.get('barrier_free_score', 'N/A')} ♿
                    - PM2.5: {nearby_place.get('pm25', 'N/A')} µg/m³
                    - PM10: {nearby_place.get('pm10', 'N/A')} µg/m³
                    - NO2: {nearby_place.get('no2', 'N/A')} µg/m³
                    """)

                if st.button("🔊 Listen the information"):
                    aud = text_to_speech(nearby_place.get('desc', 'No description available'))
                    if aud: st.audio(aud, format='audio/mp3')

        # Map (NO LANDMARK ICONS RENDERED HERE ANYMORE)
        if MAPBOX_API_KEY:
            map_style = "mapbox://styles/mapbox/dark-v10"
            api_keys = {"mapbox": MAPBOX_API_KEY}
        else:
            map_style = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
            api_keys = None

        # === RENDER MAP (without landmark icons) ===
        st.pydeck_chart(pdk.Deck(
            map_style=map_style,
            initial_view_state=view_state,
            layers=layers,
            api_keys=api_keys,
            tooltip={
                "html": """
                <b>{name}</b><br/>
                <b style='color: #00d4ff'>PM2.5:</b> {pm25} µg/m³<br/>
                <b style='color: #00d4ff'>PM10:</b> {pm10} µg/m³<br/>
                <b style='color: #00d4ff'>NO2:</b> {no2} µg/m³<br/>
                <b style='color: #00ff88'>Quality:</b> {quality_category}
                """,
                "style": {
                    "backgroundColor": "rgba(0, 0, 0, 0.8)",
                    "color": "white",
                    "fontSize": "12px",
                    "padding": "10px",
                    "borderRadius": "5px"
                }
            }
        ), height=400)

        # Air Quality Legend
        if show_aq and not aq_df.empty:
            st.markdown("### 🌫️ Air Quality Legend")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown("🟢 **Good**<br/><12 µg/m³", unsafe_allow_html=True)
            with col2:
                st.markdown("🟡 **Moderate**<br/>12-35 µg/m³", unsafe_allow_html=True)
            with col3:
                st.markdown("🟠 **Sensitive**<br/>35-55 µg/m³", unsafe_allow_html=True)
            with col4:
                st.markdown("🔴 **Unhealthy**<br/>>55 µg/m³", unsafe_allow_html=True)

        # LIST OF STOPS (WITH IMAGES IN GUIDED MODE)
        if st.session_state.user_mode == "Guided":
            st.markdown("### Your route")
            for idx, row in filtered_df.reset_index(drop=True).iterrows():
                with st.expander(f"{idx+1}. {row['name']}"):
                    # Show image in expander if available
                    place_name = row['name']
                    if place_name in LANDMARK_IMAGES and LANDMARK_IMAGES[place_name] != "YOUR_IMAGE_URL_HERE":
                        st.markdown(
                            f'<img src="{LANDMARK_IMAGES[place_name]}" class="landmark-image" width="100%">',
                            unsafe_allow_html=True
                        )

                    st.write(row.get('desc', 'No description available'))
                    st.markdown(f"""
                    **Umwelt-Info:**  
                    - Lärm: {row.get('noise_level', 'N/A')} / 100 🔊
                    - Luftqualität: {row.get('air_quality', 'N/A')} / 100 🌫️
                    - Schatten: {row.get('shade_score', 'N/A')} / 100 🌳
                    - Barrierefreiheit: {row.get('barrier_free_score', 'N/A')} / 100 ♿
                    - PM2.5: {row.get('pm25', 'N/A')} µg/m³
                    - PM10: {row.get('pm10', 'N/A')} µg/m³
                    - NO2: {row.get('no2', 'N/A')} µg/m³
                    """)
                    if st.button("🔊 Audio", key=f"btn_{idx}"):
                        aud = text_to_speech(row.get('desc', 'No description available'))
                        if aud: st.audio(aud, format='audio/mp3')