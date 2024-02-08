--##########################################################################
--Run the queries in clickhouse-ddl.sql first.
--##########################################################################

--Really useful for debugging.
select * from system.kafka_consumers;

--##########################################################################
-- Join together the ship location and weather data with the ship metadata

select spw.mmsi,sid.shipname,sid.callsign,sid.shiptype,sid.destination,spw.status,spw.heading,spw.speed,spw.lat,spw.lon,spw.region,spw.locale,spw.condition,spw.temp_f,spw.wind_dir,spw.wind_mph,spw.timestamp
from nst.ship_pos_and_wx_mv spw
left outer join nst.ship_info_and_destination_mv sid on spw.mmsi = sid.mmsi
where sid.shipname != ''