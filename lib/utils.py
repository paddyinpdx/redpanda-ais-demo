import logging
import configparser

from time import gmtime
from datetime import datetime, timezone
from confluent_kafka import avro
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka import SerializingProducer
from confluent_kafka import DeserializingConsumer
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.cimpl import KafkaError

def get_config():
    config = configparser.ConfigParser()
    config.read('../config.ini')
    return config['DEFAULT']

def delivery_callback(error, original_event):
    if error:
        print("Failed to send the message: %s" % error)
        print("Original event: %s" % original_event)

def publish_message(producer, logger, topic, key, value):
    logger.info(value)
    producer.produce(
        topic = topic,
        key = key,
        value = value,
        on_delivery = delivery_callback
    )

    producer.poll(0)
    producer.flush()

def get_logger():
    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d|%(levelname)s|%(filename)s| %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    formatter.converter = gmtime

    if len(logger.handlers) == 0:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)

    return logger

def get_consumer(group_id, topic, logger):
    config = get_config()

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
        # 'group.id': f'{group_id}-{time.strftime("%Y%m%d-%H%M%S")}',
        'group.id': group_id,
        'key.deserializer': key_deserializer,
        'value.deserializer': value_deserializer,
        'auto.offset.reset': 'earliest',
        'error_cb': on_error_callback,
        # 'debug': 'all',
        'logger': logger
    }

    return DeserializingConsumer(kafka_config)

def get_producer(schema_name, logger):
    config = get_config()

    schema_registry_conf = {'url': config['schema_registry_url']}
    schema_registry_client = SchemaRegistryClient(schema_registry_conf)
    key_schema, value_schema = load_avro_ais_schema(schema_name)
    key_serializer = AvroSerializer(schema_registry_client, f"{key_schema}")
    value_serializer = AvroSerializer(schema_registry_client, f"{value_schema}")

    producer_config = {
        'bootstrap.servers': config['bootstrap_servers'],
        'key.serializer': key_serializer,
        'value.serializer': value_serializer,
        'acks': 'all',
        # 'debug': 'all',
        'logger': logger
    }

    return SerializingProducer(producer_config)

def load_avro_ais_schema(schema_name):
    key_schema_string = """
    {"type": "string"}
    """

    key_schema = avro.loads(key_schema_string)
    value_schema = avro.load(f"../schemas/{schema_name}.avsc")

    return key_schema, value_schema

def epoch_to_iso_8601_utc(epoch):
    return datetime.utcfromtimestamp(epoch).isoformat() + 'Z'

def on_error_callback(error: KafkaError):
    logger = get_logger()
    logger.error(error)