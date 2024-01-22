import time
import json
import fastavro
import utils
from uuid import uuid4
from confluent_kafka import KafkaException
from pyais.stream import TCPConnection

logger = utils.get_logger()
config = utils.get_config()

ship_position_topic = config["ship_position_topic"]
ship_position_schema_name = config["ship_position_schema_name"]
ship_position_producer = utils.get_producer(ship_position_schema_name, logger)

ship_info_and_destination_topic = config["ship_info_and_destination_topic"]
ship_info_and_destination_schema_name = config["ship_info_and_destination_schema_name"]
ship_info_and_destination_producer = utils.get_producer(
    ship_info_and_destination_schema_name, logger
)

try:
    for msg in TCPConnection(
        host=config["ais_feed_host"], port=int(config["ais_feed_port"])
    ):
        decoded_message = msg.decode()
        m = decoded_message.asdict()

        # Only proceed if there is a tag block because it has the timestamp
        # (may also be OK to use a current timestamp, but wasn't sure)
        if msg.tag_block:
            msg.tag_block.init()
            t = msg.tag_block.asdict()
            timestamp = int(t["receiver_timestamp"], 10)
            msg_type = m["msg_type"]
            # print(f"Publishing message with message type {msg_type}")
            match msg_type:
                case 1 | 3 | 18:
                    # See https://www.navcen.uscg.gov/ais-messages. The Norwegian Coastal Administration seems to send only
                    # position reports of type 1, 3, and 18.
                    status = m.get("status", {})
                    if hasattr(status, "value"):
                        status = status.name
                    else:
                        status = "NotReported"

                    # Set the key to the MMSI so that all messages for a given ship end up in the same partition,
                    # and thus are stored in the same order as they were sent.
                    key = str(m["mmsi"])
                    speed = m["speed"]
                    heading = m["heading"]
                    lat = m["lat"]
                    lon = m["lon"]
                    # Ignore ships with erroneous data or almost no movement.
                    if (
                        speed > 2
                        and speed < 75
                        and lat <= 90
                        and lon <= 180
                        and heading < 360
                    ):
                        value = {
                            "mmsi": key,
                            "timestamp": timestamp,
                            "status": status,
                            "location": {"lat": lat, "lon": lon},
                            "speed": speed,
                            "heading": m["heading"],
                        }

                        utils.publish_message(
                            ship_position_producer,
                            logger,
                            ship_position_topic,
                            key,
                            value,
                        )
                case 5:
                    shiptype = m.get("ship_type", {})
                    if hasattr(shiptype, "value"):
                        shiptype = shiptype.name
                    else:
                        shiptype = "NotReported"

                    # Set the key to the MMSI so that all messages for a given ship end up in the same partition,
                    # and thus are stored in the same order as they were sent.
                    key = str(m["mmsi"])
                    value = {
                        "mmsi": key,
                        "timestamp": timestamp,
                        "shipname": m["shipname"],
                        "callsign": m["callsign"],
                        "shiptype": shiptype,
                        "destination": m["destination"],
                    }

                    utils.publish_message(
                        ship_info_and_destination_producer,
                        logger,
                        ship_info_and_destination_topic,
                        key,
                        value,
                    )
except KafkaException as e:
    print("Error occurred when publishing message:", e)
except KeyboardInterrupt:
    logger.info("Caught KeyboardInterrupt, stopping.")
finally:
    if ship_position_producer is not None:
        ship_position_producer.flush()
    if ship_info_and_destination_producer is not None:
        ship_info_and_destination_producer.flush()
