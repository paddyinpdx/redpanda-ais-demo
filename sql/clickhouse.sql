create database nst;

--##########################################################################
-- Use https://clickhouse.com/docs/en/integrations/kafka/kafka-table-engine
create table if not exists nst.ship_pos_and_wx_queue (
    mmsi String,
    timestamp DateTime('UTC'),
    status String,
    heading Decimal,
    speed Decimal,
    lat Float64,
    lon Float64,
    country String,
    region String,
    locale String,
    condition String,
    temp_f Decimal,
    wind_dir String,
    wind_mph Decimal
) ENGINE = Kafka()
-- https://clickhouse.com/docs/en/engines/table-engines/integrations/kafka
settings
    -- Same as the Kafka bootstrap.servers property, but for the internal network.
    kafka_broker_list = 'redpanda-1.redpanda.default.svc.cluster.local.:9093',
    kafka_topic_list = 'ship-position-events-with-weather',
    kafka_group_name = 'ship-position-events-with-weather-consumer-group',
    kafka_format = 'AvroConfluent',
    format_avro_schema_registry_url = 'http://redpanda-1.redpanda.default.svc.cluster.local.:8081'

--##########################################################################

describe table nst.ship_pos_and_wx_queue;

--##########################################################################

-- Really useful for debugging.
select * from system.kafka_consumers;

--##########################################################################

create materialized view nst.ship_pos_and_wx_mv
            ENGINE = Memory
as
select *
from nst.ship_pos_and_wx_queue
         settings
    stream_like_engine_allow_direct_select = 1;

--##########################################################################

show view nst.ship_pos_and_wx_mv;

--##########################################################################

select count() from nst.ship_pos_and_wx_mv;

--##########################################################################
-- Pull in ship metadata from PostgreSQL

create table if not exists nst.ship_and_voyage (
    mmsi UInt32,
    timestamp DateTime64(3, 'UTC'),
    name String,
    type String,
    callsign String,
    destination String
) ENGINE = PostgreSQL('postgres-postgresql.default.svc.cluster.local:5432', 'ship_voyage', 'ship', 'clickhouse_consumer_user', 'password456', 'public');

--##########################################################################

show table nst.ship_and_voyage;

--##########################################################################
-- Join together the ship location and weather data with the ship metadata

select mv.mmsi,t.name,t.callsign,t.type,t.destination,mv.status,mv.heading,mv.speed,mv.lat,mv.lon,mv.region,mv.locale,mv.condition,mv.temp_f,mv.wind_dir,mv.wind_mph,mv.timestamp
from nst.ship_pos_and_wx_mv mv
left outer join nst.ship_and_voyage t on mv.mmsi = t.mmsi