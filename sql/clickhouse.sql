create database norwegian_ais;

--##########################################################################

create table if not exists norwegian_ais.ship_pos_and_wx (
    event_id String,
    mmsi UInt32,
    timestamp DateTime('UTC'),
    status String,
    lat Decimal,
    lon Decimal,
    country String,
    region String,
    locale String,
    condition String,
    temp_f Decimal,
    wind_dir String,
    wind_mph Decimal,
    heading Decimal,
    speed Decimal
) ENGINE = Kafka()
settings
    kafka_broker_list = 'redpanda:9092',
    kafka_topic_list = 'ais-position-events-with-weather',
    kafka_group_name = 'position_event_consumer-group',
    kafka_format = 'JSON'

describe table norwegian_ais.ship_pos_and_wx;

--##########################################################################

create table if not exists norwegian_ais.ship_and_voyage (
    event_id String,
    mmsi UInt32,
    timestamp DateTime('UTC'),
    name String,
    type String,
    callsign String,
    destination String
) ENGINE = Kafka()
settings
    kafka_broker_list = 'redpanda:9092',
    kafka_topic_list = 'ais-ships-and-voyage-events-raw',
    kafka_group_name = 'ship_voyage_event_consumer-group',
    kafka_format = 'JSON'

describe table norwegian_ais.ship_and_voyage;

--##########################################################################

create materialized view norwegian_ais.ship_view
    ENGINE = Memory
as

select p.*, v.name, v.type, v.callsign, v.destination
from norwegian_ais.ship_pos_and_wx p
join norwegian_ais.ship_and_voyage v
on p.mmsi = v.mmsi

settings
stream_like_engine_allow_direct_select = 1;

show view norwegian_ais.ship_view;

--##########################################################################

select
    sv.*, sv.name
from norwegian_ais.ship_view as sv
group by name
order by sum(mmsi) desc
limit 10;