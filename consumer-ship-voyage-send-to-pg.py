import logging
import time
import psycopg2
import utils

from confluent_kafka import DeserializingConsumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.cimpl import KafkaError

logger = utils.get_logger()
config = utils.get_config()

def on_error_callback(error: KafkaError):
    logger.error(error)

if __name__ == '__main__':
    group_id = "ship_voyage_event_consumer"
    topic = "ais-ship-and-voyage-events-raw"

    # Schema registry client configuration
    schema_registry_conf = {'url': config['schema_registry_url']}
    schema_registry_client = SchemaRegistryClient(schema_registry_conf)

    key_deserializer = AvroDeserializer(
        schema_registry_client
    )

    value_deserializer = AvroDeserializer(
        schema_registry_client
    )

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
    pg_config = {
        'dbname': config['pg_dbname'],
        'user': config['pg_user'],
        'password': config['pg_password'],
        'host': config['pg_host'],
        'port': config['pg_port']
    }
    conn = psycopg2.connect(**pg_config)
    cursor = conn.cursor()

    logger.info(f'Starting kafka avro consumer loop, topic: {topic}. ^C to exit.')

    try:
        consumer.subscribe([topic])
        while True:
            msg = consumer.poll()

            if msg is None:
                continue

            if msg.error():
                logger.error(f'Error returned by poll: {msg.error()}')
            else:
                v = msg.value()

                timestamp_iso = utils.epoch_to_iso_8601_utc(v['timestamp'])

                logger.info(
                    f'offset {msg.offset()} key: {str(msg.key())} value: {str(v)}'
                )

                query = cursor.mogrify("INSERT INTO ship (mmsi, name, type, callsign, destination, receiver_timestamp) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (mmsi) DO UPDATE SET destination = %s", (v['mmsi'],v['shipname'],v['shiptype'],v['callsign'],v['destination'],timestamp_iso,v['destination']))
                logger.info(query)
                cursor.execute(query)
                conn.commit()

                consumer.commit()
    except KeyboardInterrupt:
        logger.info('Caught KeyboardInterrupt, stopping.')
    except Exception as e:
        logger.error(f'Exception in consumer loop: {e}')
    finally:
        if consumer is not None:
            consumer.commit()
            consumer.close()
