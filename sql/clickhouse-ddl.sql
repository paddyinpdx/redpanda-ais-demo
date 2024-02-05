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

create materialized view nst.ship_pos_and_wx_mv
            ENGINE = Memory
as
select *
from nst.ship_pos_and_wx_queue
         settings
    stream_like_engine_allow_direct_select = 1;

--##########################################################################
-- Use https://clickhouse.com/docs/en/integrations/kafka/kafka-table-engine
create table if not exists nst.ship_info_and_destination_queue (
     mmsi String,
     shipname String,
     shiptype String,
     callsign String,
     destination String,
     timestamp DateTime('UTC')
) ENGINE = Kafka()
-- https://clickhouse.com/docs/en/engines/table-engines/integrations/kafka
settings
    -- Same as the Kafka bootstrap.servers property, but for the internal network.
    kafka_broker_list = 'redpanda-1.redpanda.default.svc.cluster.local.:9093',
    kafka_topic_list = 'ship-info-and-destination-events',
    kafka_group_name = 'ship-info-and-destination-events-consumer-group',
    kafka_format = 'AvroConfluent',
    format_avro_schema_registry_url = 'http://redpanda-1.redpanda.default.svc.cluster.local.:8081'

--##########################################################################

create materialized view nst.ship_info_and_destination_mv
            ENGINE = Memory
as
select *
from nst.ship_info_and_destination_queue
         settings
    stream_like_engine_allow_direct_select = 1;