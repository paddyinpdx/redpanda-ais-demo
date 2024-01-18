import utils
import http.client

config = utils.get_config()
rapid_api_key = config["rapid_api_key"]


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
        "X-RapidAPI-Key": rapid_api_key,
        "X-RapidAPI-Host": "weatherapi-com.p.rapidapi.com",
    }

    conn.request("GET", f"/current.json?q={lat}%2C{lon}", headers=headers)

    res = conn.getresponse()
    data = res.read()

    return data.decode("utf-8")
