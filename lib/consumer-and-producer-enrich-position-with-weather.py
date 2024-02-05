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

group_id = "ship-position-events-consumer-group"
consumer_topic = config["ship_position_topic"]
consumer = utils.get_consumer(group_id, consumer_topic, logger)

producer_topic = config["ship_position_with_weather_topic"]
producer_schema = "ship-position-event-with-weather"
producer = utils.get_producer(producer_schema, logger)

logger.info(f"Starting kafka avro consumer loop, topic: {consumer_topic}. ^C to exit.")

try:
    consumer.subscribe([consumer_topic])
    while True:
        msg = consumer.poll()

        if msg is None:
            continue

        if msg.error():
            logger.error(f"Error returned by poll: {msg.error()}")
        else:
            v = msg.value()
            loc = v["location"]
            current_weather = json.loads(
                weather.get_current_weather_for_location(loc["lat"], loc["lon"])
            )
            if "error" in current_weather:
                logger.error(
                    f'Error returned by weather API: {current_weather["error"]}'
                )
                continue
            required_keys = ["location", "current"]
            if not all(key in current_weather for key in required_keys):
                logger.error(f"{current_weather}")
                continue
            wx_loc = current_weather["location"]
            wx = current_weather["current"]

            name = wx_loc["name"]
            region = wx_loc["region"]
            country = wx_loc["country"]
            condition = wx["condition"]["text"]
            temp = wx["temp_f"]
            wind_mph = wx["wind_mph"]
            wind_dir = wx["wind_dir"]

            logger.info(
                f"Current weather for {name}, {region}, {country}: {condition}, temp {temp}°F, wind {wind_mph}mph {wind_dir}"
            )
            logger.info(f"offset {msg.offset()} key: {str(msg.key())} value: {str(v)}")

            consumer.commit()

            # Set the key to the MMSI so that all messages for a given ship end up in the same partition,
            # and thus are stored in the same order as they were sent.
            key = str(v["mmsi"])
            value = {
                "mmsi": key,
                "timestamp": v["timestamp"],
                "status": v["status"],
                "speed": v["speed"],
                "heading": v["heading"],
                "lat": v["location"]["lat"],
                "lon": v["location"]["lon"],
                "locale": name,
                "region": region,
                "country": country,
                "condition": condition,
                "temp_f": temp,
                "wind_mph": wind_mph,
                "wind_dir": wind_dir,
            }
            utils.publish_message(producer, logger, producer_topic, key, value)
except KeyboardInterrupt:
    logger.info("Caught KeyboardInterrupt, stopping.")
except Exception as e:
    logger.exception(f"Exception in consumer loop: {e}")
    print("Handling the exception:", str(e))
finally:
    if consumer is not None:
        consumer.commit()
        consumer.close()
    if producer is not None:
        producer.flush()
