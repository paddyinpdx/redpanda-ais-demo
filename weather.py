import http.client

RAPID_API_KEY = '5c1fbab01amsh8f2b68f34c5f484p1afe63jsna472d586f39d'

class HttpsConnectionSingleton:
    _conn = None

    @classmethod
    def get_connection(cls):
        if cls._conn is None:
            cls._conn = http.client.HTTPSConnection("weatherapi-com.p.rapidapi.com")
        return cls._conn

def get_current_weather_for_location(lat, lon):
    conn = HttpsConnectionSingleton.get_connection()
    headers = {
        'X-RapidAPI-Key': RAPID_API_KEY,
        'X-RapidAPI-Host': "weatherapi-com.p.rapidapi.com"
    }

    conn.request("GET", f"/current.json?q={lat}%2C{lon}", headers=headers)

    res = conn.getresponse()
    data = res.read()

    return data.decode("utf-8")