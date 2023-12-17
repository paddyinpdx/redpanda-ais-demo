import streamlit as st
import folium
import clickhouse_connect
from streamlit_folium import folium_static

"# streamlit-folium"

# ClickHouse client connection
client = clickhouse_connect.get_client(
    host = "localhost",
    port = 18123,
    username = "default",
    password = ""
)

with st.echo():
    import streamlit as st
    from streamlit_folium import folium_static
    import folium

    query = """
    select mmsi, status, lat, lon, speed, heading, wind_mph, wind_dir, temp_f, condition, locale, region
    from nst.ship_view
    """
    ship_positions = client.query_df(query)
    def_lat_lon = ship_positions[['lat', 'lon']]
    m = folium.Map(def_lat_lon.mean().values.tolist())

    for i,r in ship_positions.iterrows():
        lat = r['lat']
        lon = r['lon']
        lat_units = '°N' if lat > 0 else '°S'
        lon_units = '°E' if lon > 0 else '°W'
        tooltip = f"MMSI: {r['mmsi']}, Status: {r['status']}, Lat: {lat}{lat_units}, Lon: {lon}{lon_units}"
        popup = f"<strong>Course:</strong> {r['heading']}° at {r['speed']} knots<br/><strong>Condition:</strong> {r['condition']}<br/><strong>Wind:</strong> {r['wind_mph']} mph {r['wind_dir']}<br/><strong>Temp:</strong> {r['temp_f']}°F<br/><strong>Location:</strong> {r['locale']}, {r['region']}"
        folium.Marker([r.lat, r.lon], popup=popup, tooltip=tooltip).add_to(m)

    sw = def_lat_lon.min().values.tolist()
    ne = def_lat_lon.max().values.tolist()

    m.fit_bounds([sw, ne])
    folium_static(m)