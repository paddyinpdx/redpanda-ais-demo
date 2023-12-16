import logging
import time
import json
import weather
import utils
from uuid import uuid4

logger = utils.get_logger()
config = utils.get_config()

if len(logger.handlers) == 0:
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

if __name__ == '__main__':
    group_id = "position-events-consumer-group"
    consumer_topic = "position-events-raw"
    producer_topic = "position-events-with-weather"
    producer_schema = "position-event-with-weather"
    producer = utils.get_producer(producer_schema, logger)
    consumer = utils.get_consumer(group_id, consumer_topic, logger)

    logger.info(f'Starting kafka avro consumer loop, topic: {consumer_topic}. ^C to exit.')

    try:
        consumer.subscribe([consumer_topic])
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
                utils.publish_message(producer, logger, producer_topic, key, value)
    except KeyboardInterrupt:
        logger.info('Caught KeyboardInterrupt, stopping.')
    except Exception as e:
        logger.error(f'Exception in consumer loop: {e}')
    finally:
        if consumer is not None:
            consumer.commit()
            consumer.close()
        if producer is not None:
            producer.flush()
