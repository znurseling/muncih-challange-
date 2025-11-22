import requests
import pandas as pd

def fetch_osm_data():
    query = """""
    [out:json][timeout:100];
    (
        node["tourism"](48.061,11.360,48.220,11.720);
    node["historic"](48.061,11.360,48.220,11.720);
    node["amenity"="park"](48.061,11.360,48.220,11.720);
    node["leisure"="park"](48.061,11.360,48.220,11.720);
    node["amenity"="museum"](48.061,11.360,48.220,11.720);
    node["artwork"](48.061,11.360,48.220,11.720);
    );
    out body;
    """
    url = "https://overpass-api.de/api/interpreter"
    response = requests.post(url, data=query)
    data = response.json()

    rows = []
    for element in data["elements"]:
        name = element["tags"].get("name")
        if not name:
            continue

        category = ""
        tags = element["tags"]

        # categorizing
        if "museum" in tags.get("amenity", "") or tags.get("tourism") == "museum":
            category = "Art"
        elif tags.get("historic"):
            category = "Historical"
        elif tags.get("leisure") == "park" or tags.get("amenity") == "park":
            category = "Nature"
        elif tags.get("tourism") == "attraction":
            category = "Sight"
        else:
            category = "General"

        rows.append({
            "name": name,
            "lat": element["lat"],
            "lon": element["lon"],
            "category": category,
            "desc": tags.get("description", "No description available"),
            "noise_level": 50,
            "air_quality": 50,
            "shade_score": 50,
            "barrier_free_score": 50
        })
    df = pd.DataFrame(rows)
    df.to_csv("places-in-munich.csv", index = False)
    print(("CSV successfully created with", len(df), "locations."))
if __name__ == "__main__":
    fetch_osm_data()

