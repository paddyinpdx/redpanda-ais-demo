import utils
import streamlit as st
import folium
import clickhouse_connect

from streamlit_folium import folium_static

st.set_page_config(layout="wide")
config = utils.get_config()

"# Norwegian Ship and Weather Tracker Demo"
left_col, right_col = st.columns(2)
with left_col:
    st.image(
            "https://images.ctfassets.net/paqvtpyf8rwu/GeLUVavqqxhFZolzU9jM3/3b8dddc74a632e63f17e0a5e40b971bb/super-panda-update.svg",
            width=100,
    )
with right_col:
    st.image("https://www.kystverket.no/UI/Icons/logo.svg")

st.write("A dashboard showing the [Norwegian AIS shipping feed](https://www.kystverket.no/en/navigation-and-monitoring/ais/access-to-ais-data/) enriched with real-time weather data from [WeatherAPI.com](https://rapidapi.com/weatherapi/api/weatherapi-com/), built with [Redpanda](https://redpanda.com/), PostgreSQL, [ClickHouse](https://clickhouse.com/), and [Streamlit](https://streamlit.io/). Note: MMSI is the acronym for Maritime Mobile Service Identity, a unique 9-digit number that identifies a ship.")
st.divider()

# ClickHouse client connection
client = clickhouse_connect.get_client(
    host = config['ch_host'],
    port = config['ch_port'],
    username = config['ch_user'],
    password = config['ch_password']
)

total_ship_count_query = """
select count(distinct mmsi) as ship_count from nst.ship_pos_and_wx_mv
"""
df_total_ship_count = client.query_df(total_ship_count_query)

moving_gt_10_kts_ship_count_query = """
select count(distinct mmsi) as ship_count from nst.ship_pos_and_wx_mv where speed > 10
"""
df_moving_gt_10_kts_ship_count = client.query_df(moving_gt_10_kts_ship_count_query)

ship_details_query = """
select mv.mmsi,t.name,t.callsign,t.type,t.destination,mv.status,mv.heading,mv.speed,mv.lat,mv.lon,mv.region,mv.locale,mv.condition,mv.temp_f,mv.wind_dir,mv.wind_mph,mv.timestamp
from nst.ship_pos_and_wx_mv mv
left outer join nst.ship_and_voyage t on mv.mmsi = t.mmsi
where t.name != ''
"""
df_ship_details = client.query_df(ship_details_query)
if df_ship_details.empty:
    st.error("No ships found. The ClickHouse materialized view is empty. It can only be populated by running the `consumer-and-producer-enrich-position-with-weather.py` script.")
    st.stop()

def_lat_lon = df_ship_details[['lat', 'lon']]
m = folium.Map(def_lat_lon.mean().values.tolist())

icon_color_map = {
    'Tanker': 'red',
    'Law': 'blue',
    'Military': 'gray',
    'Pilot': 'lightred',
    'Medical': 'darkred',
    'Cargo': 'purple',
    'Search': 'orange',
    'NonCombat': 'beige',
    'Passenger': 'green',
    'Dredging': 'darkgreen',
    'Law': 'lightgreen',
    'AntiPollution': 'darkblue',
    'Fishing': 'lightblue',
    'Towing': 'darkpurple',
    'HSC': 'pink',
    'OtherType': 'cadetblue',
    'Tug': 'black'
}

default_color = 'lightgray'
# ship_types = df_ship_details['type'].tolist()
# icon_colors = [icon_color_map.get(next((prefix for prefix in icon_color_map if ship_type.startswith(prefix)), default_color)) for ship_type in ship_types]

for i,r in df_ship_details.iterrows():
    lat = r['lat']
    lon = r['lon']
    lat_units = '°N' if lat > 0 else '°S'
    lon_units = '°E' if lon > 0 else '°W'
    tooltip = f"Name: {r['name']}, Callsign: {r['callsign']}, Type: {r['type']}, Status: {r['status']}"
    popup = f"<strong>Lat:</strong> {lat}{lat_units}<br/><strong>Lon:</strong> Lon: {lon}{lon_units}<br/><strong>Course:</strong> {r['heading']}° at {r['speed']} knots<br/><strong>Condition:</strong> {r['condition']}<br/><strong>Wind:</strong> {r['wind_mph']} mph {r['wind_dir']}<br/><strong>Temp:</strong> {r['temp_f']}°F<br/><strong>Location:</strong> {r['locale']}, {r['region']}"
    icon_color = icon_color_map.get(next((prefix for prefix in icon_color_map if r['type'].startswith(prefix)), default_color))
    icon = folium.Icon(icon="ship", prefix="fa", color=icon_color)
    folium.Marker([r.lat, r.lon], popup=popup, tooltip=tooltip, icon=icon).add_to(m)

sw = def_lat_lon.min().values.tolist()
ne = def_lat_lon.max().values.tolist()

m.fit_bounds([sw, ne])

metric1, metric2 = st.columns(2)
metric1.metric(
    label="Total ships",
    value=df_total_ship_count['ship_count'].values[0]
)
metric2.metric(
    label="Ships moving > 10 knots",
    value=df_moving_gt_10_kts_ship_count['ship_count'].values[0]
)

st.dataframe(
    df_ship_details,
    hide_index=True,
    use_container_width=True
)

folium_static(m, width=1440, height=800)