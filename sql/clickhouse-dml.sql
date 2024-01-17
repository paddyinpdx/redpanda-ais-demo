--##########################################################################
--Run the queries in clickhouse-ddl.sql first.
--##########################################################################

--Really useful for debugging.
select * from system.kafka_consumers;

--##########################################################################
-- Join together the ship location and weather data with the ship metadata

select mv.mmsi,t.name,t.callsign,t.type,t.destination,mv.status,mv.heading,mv.speed,mv.lat,mv.lon,mv.region,mv.locale,mv.condition,mv.temp_f,mv.wind_dir,mv.wind_mph,mv.timestamp
from nst.ship_pos_and_wx_mv mv
left outer join nst.ship_and_voyage t on mv.mmsi = t.mmsi