import pandas as pd

def create_munich_dataset():


    data = [
        # Nature
        {"name": "Eisbachwelle", "lat": 48.1435, "lon": 11.5877, "category": "Nature", "desc": "A famous river wave where surfers show off their skills in the middle of the city."},
        {"name": "Monopteros", "lat": 48.1539, "lon": 11.5963, "category": "Nature", "desc": "A Greek-style temple offering the best panoramic view of the English Garden."},
        {"name": "Kleinhesseloher See", "lat": 48.1607, "lon": 11.5977, "category": "Nature", "desc": "A peaceful lake perfect for renting a pedal boat or enjoying a beer at the Seehaus."},
        {"name": "Nymphenburger Schlosspark", "lat": 48.1582, "lon": 11.5036, "category": "Nature", "desc": "A vast baroque park with hidden pavilions, canals, and ancient trees."},
        {"name": "Flaucher", "lat": 48.1077, "lon": 11.5628, "category": "Nature", "desc": "The Isar river's pebble beaches where locals grill, swim, and relax in summer."},
        
        # Historical
        {"name": "Residenz München", "lat": 48.1411, "lon": 11.5780, "category": "Historical", "desc": "The former royal palace of the Wittelsbach monarchs of Bavaria."},
        {"name": "Feldherrnhalle", "lat": 48.1418, "lon": 11.5776, "category": "Historical", "desc": "A monumental loggia on Odeonsplatz modeled after the Loggia dei Lanzi in Florence."},
        {"name": "Alter Peter", "lat": 48.1364, "lon": 11.5751, "category": "Historical", "desc": "The oldest parish church in Munich. The view from the top is worth every step."},
        {"name": "Siegestor", "lat": 48.1526, "lon": 11.5819, "category": "Historical", "desc": "A three-arched triumphal arch crowned with a statue of Bavaria with four lions."},
        {"name": "Asamkirche", "lat": 48.1351, "lon": 11.5695, "category": "Historical", "desc": "A stunning Baroque church built by the Asam brothers as their private chapel."},

        # Art
        {"name": "Pinakothek der Moderne", "lat": 48.1471, "lon": 11.5722, "category": "Art", "desc": "One of the world's largest museums for modern and contemporary art."},
        {"name": "Brandhorst Museum", "lat": 48.1481, "lon": 11.5743, "category": "Art", "desc": "Famous for its multicolored facade and impressive collection of Andy Warhol pieces."},
        {"name": "Street Art Museum (MUCA)", "lat": 48.1372, "lon": 11.5698, "category": "Art", "desc": "Germany's first museum of urban art, hidden in a former power station."},
        {"name": "Alte Pinakothek", "lat": 48.1483, "lon": 11.5700, "category": "Art", "desc": "Home to one of the most important collections of Old Master paintings in the world."},
        {"name": "Lenbachhaus", "lat": 48.1470, "lon": 11.5637, "category": "Art", "desc": "Famous for its collection of works by the 'Blue Rider' group, including Kandinsky."}
    ]
    
    df = pd.DataFrame(data)
    df.to_csv("places-in-munich.csv", index=False)
    print("'places-in-munich.csv' has been created.")

if __name__ == "__main__":
    create_munich_dataset()

