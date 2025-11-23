class Landmark:
    def __init__(self,  name, lat, lon, desc, category=None, icon_color=[0, 200, 100], base_radius=50):
        self.name=name
        self.lat=lat
        self.lon=lon
        self.desc = desc
        self.category=category
        self.icon_color = icon_color
        self.base_radius=base_radius
        '''
        self.icon_data = icon_data or {
            "url": "",
            "width": 128,
            "height": 128
        }
        '''


    def get_scaled_radius(self, user_lat, user_lon, max_radius=150, min_distance=0.05, max_distance=0.5):
         """
         Skaliert die Icon-Größe abhängig von der Entfernung des Nutzers.
         - min_distance: Entfernung unterhalb derer das Icon max_radius hat
         - max_distance: Entfernung oberhalb derer das Icon min_radius hat
         """
         from geopy.distance import geodesic
         dist_km = geodesic((self.lat, self.lon), (user_lat, user_lon)).km
         if dist_km <= min_distance:
             return max_radius
         elif dist_km >= max_distance:
             return self.base_radius
         else:
             #lineare Interpolation
             scale = max_radius - ((dist_km - min_distance) / (max_distance - min_distance)) * (max_radius - self.base_radius)
             return scale

    def to_layer_data(self, user_lat, user_lon):
        return {
            "lon": self.lon,
            "lat": self.lat,
            "radius": self.get_scaled_radius(user_lat, user_lon),
            "name": self.name,
            "desc": self.desc,
            "color": self.icon_color
        }