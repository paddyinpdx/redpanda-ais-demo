create database nst;

--##########################################################################
-- Use https://clickhouse.com/docs/en/integrations/kafka/kafka-table-engine
create table if not exists nst.ship_pos_and_wx_queue (
    mmsi UInt32,
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
    kafka_broker_list = 'redpanda:9092',
    kafka_topic_list = 'position-events-with-weather',
    kafka_group_name = 'position-events-with-weather-consumer-group',
    kafka_num_consumers = 1,
    kafka_format = 'AvroConfluent',
    format_avro_schema_registry_url = 'http://redpanda:18081'

--##########################################################################

describe table nst.ship_pos_and_wx_queue;
select * from system.kafka_consumers;

--##########################################################################

create table if not exists nst.ship_and_voyage_queue (
    mmsi UInt32,
    timestamp DateTime64(3, 'UTC'),
    name String,
    type String,
    callsign String,
    destination String
) ENGINE = Kafka()
settings
    --TODO: add postgres source

describe table nst.ship_and_voyage_queue;

--##########################################################################

create materialized view nst.ship_view
    ENGINE = Memory
as
select *
from nst.ship_pos_and_wx_queue
settings
stream_like_engine_allow_direct_select = 1;

--##########################################################################

show view nst.ship_view;
select count() from nst.ship_view;

--##########################################################################

select
    sv.*, sv.name
from nst.ship_view as sv
group by name
order by sum(mmsi) desc
limit 10;