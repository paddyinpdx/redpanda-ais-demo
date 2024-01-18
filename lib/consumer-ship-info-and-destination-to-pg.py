import logging
import time
import psycopg2
import utils

logger = utils.get_logger()
config = utils.get_config()

group_id = "ship-info-and-destination-events-consumer-group"
ship_info_and_destination_topic = config["ship_info_and_destination_topic"]
consumer = utils.get_consumer(group_id, ship_info_and_destination_topic, logger)

pg_config = {
    "dbname": config["pg_dbname"],
    "user": config["pg_user"],
    "password": config["pg_password"],
    "host": config["pg_host"],
    "port": config["pg_port"],
}
conn = psycopg2.connect(**pg_config)
cursor = conn.cursor()

logger.info(
    f"Starting kafka avro consumer loop, topic: {ship_info_and_destination_topic}. ^C to exit."
)

try:
    consumer.subscribe([ship_info_and_destination_topic])
    while True:
        msg = consumer.poll()

        if msg is None:
            continue

        if msg.error():
            logger.error(f"Error returned by poll: {msg.error()}")
        else:
            v = msg.value()

            logger.info(f"offset {msg.offset()} key: {str(msg.key())} value: {str(v)}")

            query = cursor.mogrify(
                "INSERT INTO ship (mmsi, name, type, callsign, destination, timestamp) "
                "VALUES (%s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (mmsi) "
                "DO UPDATE SET destination = %s",
                (
                    v["mmsi"],
                    v["shipname"],
                    v["shiptype"],
                    v["callsign"],
                    v["destination"],
                    v["timestamp"],
                    v["destination"],
                ),
            )

            logger.info(query)
            cursor.execute(query)
            conn.commit()
            consumer.commit()
except KeyboardInterrupt:
    logger.info("Caught KeyboardInterrupt, stopping.")
except Exception as e:
    logger.error(f"Exception in consumer loop: {e}")
finally:
    if consumer is not None:
        consumer.commit()
        consumer.close()
