import logging
import time
import psycopg2
import utils

logger = utils.get_logger()
config = utils.get_config()

if __name__ == '__main__':
    group_id = "ship-and-voyage-events-consumer-group"
    consumer_topic = "ship-and-voyage-events-raw"
    consumer = utils.get_consumer(group_id, consumer_topic, logger)

    pg_config = {
        'dbname': config['pg_dbname'],
        'user': config['pg_user'],
        'password': config['pg_password'],
        'host': config['pg_host'],
        'port': config['pg_port']
    }
    conn = psycopg2.connect(**pg_config)
    cursor = conn.cursor()

    logger.info(f'Starting kafka avro consumer loop, topic: {consumer_topic}. ^C to exit.')

    try:
        consumer.subscribe([consumer_topic])
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
