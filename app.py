import streamlit as st
import pandas as pd
import pydeck as pdk
from geopy.distance import geodesic
from gtts import gTTS
import io

# WELCOME SCREEN

if "setup_complete" not in st.session_state:
    st.session_state.setup_complete = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "user_interests" not in st.session_state:
    st.session_state.user_interests = []
if "user_mode" not in st.session_state:
    st.session_state.user_mode = ""

# vor setup welcome page
if not st.session_state.setup_complete:
    st.title("Hey und Willkommen beim neuen Munich Explorer")
    st.subheader("Erschaffe deine persönliche München Exprience")

    st.session_state.user_name = st.text_input(
        "Wie dürfen wir dich nennen?", placeholder= "Dein name"
    )

    st.markdown("## Verrate uns Interessen")
    all_interests = ["Architektur",
                     "Geschichte",
                     "Natur",
                     "Ruhe / Entspannung",
                     "Barrierefreiheit",
                     "Stadtbild",
                     "Biodiversität",
                     "Umwelt (Luft, Lärm, Hitze)",
                     "Kulturelle Events"
                     ]

    st.session_state.user_interests = st.multiselect(
        "Was interessiert dich auf deinem Spaziergang am meisten?",
        all_interests
    )
    st.markdown("Mode")
    st.session_state.user_mode = st.radio(
        "Wie möchtest du geführt werden?",
        ["🧭 Proaktiver Modus (Wir schlagen dir Dinge automatisch vor)",
         "📘 Nur Präferenzen (Du entscheidest selbst)"]
    )
    st.write("---")

    if st.button("Los gehts!"):
        if st.session_state.user_name=="":
            st.warning("Bitte gebe Deinen Namen ein 😊")
        elif len(st.session_state.user_interests)==0:
            st.warning(" Bislang keine Interessen, bitte wählen welche aus 😊")
        else:
            st.session_state.setup_complete = True
            st.success("Perfekt! Deine personalisierte München-Map wird vorbereitet...")
            st.experimental_rerun()

    st.write()


# --- Jetzt Setup config ---
st.set_page_config(page_title="Munich Vibe Guide", page_icon="🥨", layout="wide")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    try:
        # Load data from the CSV file
        df = pd.read_csv("places-in-munich.csv")
        return df
    except FileNotFoundError:
        st.error("Could not find 'places-in-munich.csv'. Please make sure the file exists in the same folder.")
        return pd.DataFrame() 

df = load_data()

# --- HELPER FUNCTIONS ---
def text_to_speech(text):
    """Generates audio from text using Google TTS."""
    tts = gTTS(text=text, lang='en')
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    return audio_fp

def get_route_stats(points_df):
    """Calculates total distance and estimated walking time."""
    if len(points_df) < 2:
        return 0, 0
    total_dist_km = 0
    for i in range(len(points_df) - 1):
        p1 = (points_df.iloc[i]['lat'], points_df.iloc[i]['lon'])
        p2 = (points_df.iloc[i+1]['lat'], points_df.iloc[i+1]['lon'])
        total_dist_km += geodesic(p1, p2).km
    
    # Avg walking speed ~5 km/h
    duration_min = int((total_dist_km / 5) * 60) 
    return total_dist_km, duration_min

# --- SIDEBAR ---
st.sidebar.title("🦁 Munich Explorer")
st.sidebar.header("Customize Your Walk")

if not df.empty:
    interest = st.sidebar.radio(
        "What is the purpose of today's walk?",
        df['category'].unique() # Dynamically get categories from CSV
    )

    mode = st.sidebar.selectbox(
        "Choose your Mode:",
        ["🧭 Fixed Path (Guided)", "🎲 Spontaneous (Discovery)"]
    )

    # Filter Data based on Interest
    filtered_df = df[df['category'] == interest]

    # --- MAIN APP ---
    st.title(f"Munich {interest} Walk")

    # --- MODE 1: FIXED PATH ---
    if mode == "🧭 Fixed Path (Guided)":
        st.info(f"We curated a perfect **{interest}** route for you.")

        # Calculate Stats
        dist, duration = get_route_stats(filtered_df)
        col1, col2 = st.columns(2)
        col1.metric("Total Distance", f"{dist:.2f} km")
        col2.metric("Est. Duration", f"{duration} min")

        # Map Layer: Scatterplot (Points) + PathLayer (Route)
        layer_points = pdk.Layer(
            "ScatterplotLayer",
            filtered_df,
            get_position='[lon, lat]',
            get_color='[200, 30, 0, 160]',
            get_radius=50,
            pickable=True
        )

        # Create path data (list of coordinates)
        path_data = [{"path": filtered_df[['lon', 'lat']].values.tolist()}]

        layer_path = pdk.Layer(
            "PathLayer",
            path_data,
            get_path="path",
            get_color='[0, 0, 255, 200]',
            width_scale=20,
            width_min_pixels=2,
            pickable=True
        )

        # Render Map
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(
                latitude=48.145,
                longitude=11.58,
                zoom=13,
                pitch=0,
            ),
            layers=[layer_path, layer_points],
            tooltip={"text": "{name}\n{desc}"}
        ))

        st.subheader("Stops along the way:")
        for i, row in filtered_df.iterrows():
            with st.expander(f"{i+1}. {row['name']}"):
                st.write(row['desc'])
                if st.button(f"🔊 Listen to Info for {row['name']}", key=f"btn_{i}"):
                    audio_data = text_to_speech(row['desc'])
                    st.audio(audio_data, format="audio/mp3")

    # +filter+ nach indivd. nutzerinteressen
    filtered_df = df[df['category'].isin(st.session_state.user_interests)]

    # Sortieren nach live Entfernung
    filtered_df['distance_km'] = filtered_df.apply(
        lambda row: geodesic((row['lat'], row['lon']), (current_lat, current_lon)).km,axis=1)

    filtered_df = filtered_df.sort_values('distance_km')
    if filtered_df.empty:
        st.warning("Leider haben wir keine passenden Orte für deine Interessen gefunden, stay tuned")





    # --- MODE 2: SPONTANEOUS ---
    elif mode == "🎲 Spontaneous (Discovery)":
        st.success("Start walking! We will notify you when you pass something cool.")

        # Simulation Slider (Essential for Hackathon Demos!)
        st.markdown("### 🚶‍♂️ Simulation: Walk through the city")
        progress = st.slider("Move the slider to simulate walking south-north:", 0, 100, 0)

        # Simulate a user walking from Marienplatz (south) northwards
        start_lat, start_lon = 48.1351, 11.575  # Near Marienplatz
        current_lat = start_lat + (progress * 0.0003) # Moving North slightly
        current_lon = start_lon + (progress * 0.0001) # Moving East slightly

        user_pos = pd.DataFrame([{"lat": current_lat, "lon": current_lon, "name": "You"}])

        # Check proximity to any interesting point
        proximity_threshold_km = 0.3 # 300 meters
        nearby_place = None

        for _, row in filtered_df.iterrows():
            place_loc = (row['lat'], row['lon'])
            user_loc = (current_lat, current_lon)
            distance = geodesic(place_loc, user_loc).km

            if distance < proximity_threshold_km:
                nearby_place = row
                break

        # Map Layer: User + All Potential Interest Points
        layer_user = pdk.Layer(
            "ScatterplotLayer",
            user_pos,
            get_position='[lon, lat]',
            get_color='[0, 128, 255, 200]', # Blue for user
            get_radius=80,
            pickable=True,
        )

        layer_targets = pdk.Layer(
            "ScatterplotLayer",
            filtered_df,
            get_position='[lon, lat]',
            get_color='[255, 140, 0, 160]', # Orange for targets
            get_radius=50,
            pickable=True
        )

        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(
                latitude=current_lat,
                longitude=current_lon,
                zoom=14,
                pitch=40,
            ),
            layers=[layer_user, layer_targets],
            tooltip={"text": "{name}"}
        ))

        # --- THE "EVENT" TRIGGER ---
        if nearby_place is not None:
            st.toast(f"📍 You are near {nearby_place['name']}!", icon="🎉")

            with st.container():
                st.markdown(f"## 🏛️ Found: {nearby_place['name']}")
                st.write(f"**Why it fits your '{interest}' walk:**")
                st.write(nearby_place['desc'])

                col_audio, col_action = st.columns([1, 3])
                with col_audio:
                    st.markdown("Listen to the story:")
                    # Auto-generate audio only when near
                    audio_bytes = text_to_speech(f"Hey! You just discovered {nearby_place['name']}. {nearby_place['desc']}")
                    st.audio(audio_bytes, format='audio/mp3', start_time=0)
        else:
            st.markdown("*Keep walking... nothing nearby yet.*")
else:
    st.warning("Data not loaded. Please ensure 'places-in-munich.csv' is in the directory.")