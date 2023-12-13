import logging
import configparser

from time import gmtime
from datetime import datetime, timezone
from confluent_kafka import avro
from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer

def get_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
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

def get_producer(schema_name, logger):
    schema_registry_conf = {'url': 'http://localhost:18081'}
    schema_registry_client = SchemaRegistryClient(schema_registry_conf)
    key_schema, value_schema = load_avro_ais_schema(schema_name)
    key_serializer = AvroSerializer(schema_registry_client, f"{key_schema}")
    value_serializer = AvroSerializer(schema_registry_client, f"{value_schema}")

    config = {
        'bootstrap.servers' : "localhost:19092",
        'schema.registry.url' : "http://localhost:18081"
    }
    producer_config = {
        'bootstrap.servers': 'localhost:19092',
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
    value_schema = avro.load(f"./schemas/{schema_name}.avsc")

    return key_schema, value_schema

def epoch_to_iso_8601_utc(epoch):
    return datetime.utcfromtimestamp(epoch).isoformat() + 'Z'