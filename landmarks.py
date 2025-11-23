from geopy.distance import geodesic
import pydeck as pdk

class Landmark:
    def __init__(self, name, lat, lon, desc, category=None, icon_data=None, icon_color=[0, 200, 100], base_radius=50):
        self.name = name
        self.lat = lat
        self.lon = lon
        self.desc = desc
        self.category = category
        self.icon_color = icon_color
        self.base_radius = base_radius
        # Icon configuration: URL oder emoji/symbol
        self.icon_data = icon_data or {
            "url": "https://img.icons8.com/emoji/96/round-pushpin.png",
            "width": 128,
            "height": 128
        }

    def get_scaled_radius(self, user_lat, user_lon, max_radius=150, min_distance=0.05, max_distance=0.5):
        """
        Skaliert die Icon-Größe abhängig von der Entfernung des Nutzers.
        - min_distance: Entfernung unterhalb derer das Icon max_radius hat
        - max_distance: Entfernung oberhalb derer das Icon min_radius hat
        """
        dist_km = geodesic((self.lat, self.lon), (user_lat, user_lon)).km
        if dist_km <= min_distance:
            return max_radius
        elif dist_km >= max_distance:
            return self.base_radius
        else:
            # Lineare Interpolation
            scale = max_radius - ((dist_km - min_distance) / (max_distance - min_distance)) * (max_radius - self.base_radius)
            return scale

    def get_icon_size(self, user_lat, user_lon, max_size=8, min_size=3):
        """
        Skaliert die Icon-Größe (für IconLayer) abhängig von der Entfernung.
        """
        dist_km = geodesic((self.lat, self.lon), (user_lat, user_lon)).km
        if dist_km <= 0.05:  # Weniger als 50m
            return max_size
        elif dist_km >= 0.5:  # Mehr als 500m
            return min_size
        else:
            # Lineare Interpolation
            scale = max_size - ((dist_km - 0.05) / 0.45) * (max_size - min_size)
            return scale

    def to_layer_data(self, user_lat, user_lon):
        """Gibt Daten-Dict für pydeck Layer zurück"""
        # Emoji/Symbol basierend auf dem Icon-Typ
        icon_symbol = "📍"  # Default
        if "wave" in self.icon_data["url"].lower() or "eisbach" in self.name.lower():
            icon_symbol = "🌊"
        elif "temple" in self.icon_data["url"].lower() or "monopteros" in self.name.lower():
            icon_symbol = "🏛️"
        elif "angel" in self.icon_data["url"].lower() or "friedens" in self.name.lower():
            icon_symbol = "👼"
        elif "tower" in self.icon_data["url"].lower() or "turm" in self.name.lower():
            icon_symbol = "🗼"
        elif "market" in self.icon_data["url"].lower() or "markt" in self.name.lower():
            icon_symbol = "🛒"

        return {
            "lon": self.lon,
            "lat": self.lat,
            "radius": self.get_scaled_radius(user_lat, user_lon),
            "icon_size": self.get_icon_size(user_lat, user_lon),
            "name": self.name,
            "desc": self.desc,
            "color": self.icon_color,
            "icon": self.icon_data["url"],
            "text": icon_symbol  # Für TextLayer
        }


# Icons URLs - direkt hardcoded (funktionieren garantiert)
ICON_WAVE = {
    "url": "https://cdn-icons-png.flaticon.com/128/4150/4150884.png",  # Wave
    "width": 128,
    "height": 128
}

ICON_TEMPLE = {
    "url": "https://cdn-icons-png.flaticon.com/128/3976/3976625.png",  # Temple
    "width": 128,
    "height": 128
}

ICON_ANGEL = {
    "url": "https://cdn-icons-png.flaticon.com/128/2913/2913133.png",  # Angel
    "width": 128,
    "height": 128
}

ICON_TOWER = {
    "url": "https://cdn-icons-png.flaticon.com/128/2920/2920264.png",  # Tower
    "width": 128,
    "height": 128
}

ICON_MARKET = {
    "url": "https://cdn-icons-png.flaticon.com/128/3081/3081559.png",  # Market/Shopping
    "width": 128,
    "height": 128
}


# Vordefinierte Landmarks für München mit individuellen Icons
landmark_list = [
    Landmark(
        name="Eisbachwelle",
        lat=48.1435,
        lon=11.5877,
        desc="Eine der berühmtesten stehenden Wellen der Welt. Hier surfen Münchner das ganze Jahr über im eiskalten Eisbach.",
        category="Nature",
        icon_data=ICON_WAVE,
        icon_color=[0, 150, 255],
        base_radius=40
    ),
    Landmark(
        name="Monopteros",
        lat=48.1539,
        lon=11.5963,
        desc="Ein griechischer Rundtempel im Englischen Garten mit wunderschönem Blick über München.",
        category="Historical",
        icon_data=ICON_TEMPLE,
        icon_color=[200, 150, 50],
        base_radius=45
    ),
    Landmark(
        name="Friedensengel",
        lat=48.1550,
        lon=11.5940,
        desc="Ein 23 Meter hoher Engel auf einer Säule, der an 25 Jahre Frieden nach dem Deutsch-Französischen Krieg erinnert.",
        category="Historical",
        icon_data=ICON_ANGEL,
        icon_color=[255, 215, 0],
        base_radius=45
    ),
    Landmark(
        name="Chinesischer Turm",
        lat=48.1545,
        lon=11.5935,
        desc="Ein 25 Meter hoher Holzpagode im Englischen Garten.",
        category="Nature",
        icon_data=ICON_TOWER,
        icon_color=[180, 100, 50],
        base_radius=50
    ),
    Landmark(
        name="Viktualienmarkt",
        lat=48.1351,
        lon=11.5762,
        desc="Der traditionelle Lebensmittelmarkt im Herzen Münchens seit 1807.",
        category="Culture",
        icon_data=ICON_MARKET,
        icon_color=[255, 100, 100],
        base_radius=55
    )
]