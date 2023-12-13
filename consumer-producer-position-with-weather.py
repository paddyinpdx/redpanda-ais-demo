import logging
import time
import json
import weather
import utils

from uuid import uuid4
from confluent_kafka import DeserializingConsumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.cimpl import KafkaError

logger = utils.get_logger()
config = utils.get_config()

if len(logger.handlers) == 0:
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

def on_error_callback(error: KafkaError):
    logger.error(error)

if __name__ == '__main__':
    group_id = "position_event_consumer"
    consume_topic = "ais-position-events-raw"
    produce_topic = "ais-position-events-with-weather"
    position_with_weather_producer = utils.get_producer("ais-position-event-with-weather", logger)

    # Schema registry client configuration
    schema_registry_conf = {'url': config['schema_registry_url']}
    schema_registry_client = SchemaRegistryClient(schema_registry_conf)

    key_deserializer = AvroDeserializer(schema_registry_client)
    value_deserializer = AvroDeserializer(schema_registry_client)

    kafka_config = {
        'bootstrap.servers': config['bootstrap_servers'],
        # Normally one would set a non-changing group id, but for a demo, it's nice to be able to
        # run the script and have all messages in the topic be consumed. If you want a fixed group_id,
        # swap the commented lines below.
        # See https://stackoverflow.com/questions/49945450/why-is-kafka-consumer-ignoring-my-earliest-directive-in-the-auto-offset-reset
        'group.id': f'{group_id}-{time.strftime("%Y%m%d-%H%M%S")}',
        # 'group.id': group_id,
        'key.deserializer': key_deserializer,
        'value.deserializer': value_deserializer,
        'auto.offset.reset': 'earliest',
        'error_cb': on_error_callback,
        # 'debug': 'all',
        'logger': logger
    }

    consumer = DeserializingConsumer(kafka_config)

    logger.info(f'Starting kafka avro consumer loop, topic: {consume_topic}. ^C to exit.')

    try:
        consumer.subscribe([consume_topic])
        while True:
            msg = consumer.poll()

#             if msg.offset() > 0:
#                 break

            if msg is None:
                continue

            if msg.error():
                logger.error(f'Error returned by poll: {msg.error()}')
            else:
                v = msg.value()
                loc = v['location']
                current_weather = json.loads(weather.get_current_weather_for_location(loc['lat'], loc['lon']))

                wx_loc = current_weather['location']
                wx = current_weather['current']
                name =  wx_loc['name']
                region = wx_loc['region']
                country = wx_loc['country']
                condition = wx['condition']['text']
                temp = wx['temp_f']
                wind_mph = wx['wind_mph']
                wind_dir = wx['wind_dir']

                logger.info(f'Current weather for {name}, {region}, {country}: {condition}, temp {temp}°F, wind {wind_mph}mph {wind_dir}')
                logger.info(
                    f'offset {msg.offset()} key: {str(msg.key())} value: {str(v)}'
                )

                consumer.commit()

                key = str(uuid4())
                value = {
                    "mmsi": v["mmsi"],
                    "timestamp": utils.epoch_to_iso_8601_utc(v["timestamp"]),
                    "status": v["status"],
                    "location": {
                        "lat": v["location"]["lat"],
                        "lon": v["location"]["lon"],
                        "locale": name,
                        "region": region,
                        "country": country
                    },
                    "speed": v["speed"],
                    "heading": v["heading"],
                    "weather": {
                        "condition": condition,
                        "temp_f": temp,
                        "wind": {
                            "mph": wind_mph,
                            "dir": wind_dir
                        }
                    }
                }
                utils.publish_message(position_with_weather_producer, logger, produce_topic, key, value)
    except KeyboardInterrupt:
        logger.info('Caught KeyboardInterrupt, stopping.')
    except Exception as e:
        logger.error(f'Exception in consumer loop: {e}')
    finally:
        if consumer is not None:
            consumer.commit()
            consumer.close()
        if position_with_weather_producer is not None:
            position_with_weather_producer.flush()
