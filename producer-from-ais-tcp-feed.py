import time
import json
import fastavro
import utils
from uuid import uuid4
from confluent_kafka import KafkaException
from pyais.stream import TCPConnection

logger = utils.get_logger()
config = utils.get_config()

position_topic = "position-events-raw"
position_schema_name = "position-event"
ship_and_voyage_topic = "ship-and-voyage-events-raw"
ship_and_voyage_schema_name = "ship-and-voyage-event"
position_producer = utils.get_producer(position_schema_name, logger)
ship_voyage_producer = utils.get_producer(ship_and_voyage_schema_name, logger)

try:
    for msg in TCPConnection(host=config['ais_feed_host'], port=int(config['ais_feed_port'])):
        decoded_message = msg.decode()
        m = decoded_message.asdict()

        if msg.tag_block:
            # Only proceed if there is a tag block because it has the timestamp
            # (but maybe it would be OK to use the current time in that case?)
            msg.tag_block.init()
            t = msg.tag_block.asdict()

            msg_type = m["msg_type"]
            key = str(uuid4())
            # print(f"Publishing message with message type {msg_type}")
            try:
                match msg_type:
                    case 1 | 3 | 18:
                        # See https://www.navcen.uscg.gov/ais-messages. The Norwegian Coastal Administration seems to send only
                        # position reports of type 1, 3, and 18.
                        status = m.get("status", {})
                        if hasattr(status, "value"):
                            status = status.name
                        else:
                            status = "NotReported"

                        speed = m["speed"]
                        # Ignore ships that are probably not moving, or
                        # are reporting moving too fast, which is probably
                        # an error (quite a few report 102 for some reason).
                        if speed > 2 and speed < 75:
                            value = {
                                "mmsi": m["mmsi"],
                                "timestamp": int(t["receiver_timestamp"], 10),
                                "status": status,
                                "location": {
                                  "lat": m["lat"],
                                  "lon": m["lon"]
                                },
                                "speed": speed,
                                "heading": m["heading"]
                            }

                            utils.publish_message(position_producer, logger, position_topic, key, value)
                    case 5:
                        shiptype = m.get("ship_type", {})
                        if hasattr(shiptype, "value"):
                            shiptype = shiptype.name
                        else:
                            shiptype = "NotReported"

                        value = {
                            "mmsi": m["mmsi"],
                            "timestamp": int(t["receiver_timestamp"], 10),
                            "shipname": m["shipname"],
                            "callsign": m["callsign"],
                            "shiptype": shiptype,
                            "destination": m["destination"]
                        }

                        utils.publish_message(ship_voyage_producer, logger, ship_and_voyage_topic, key, value)
                    case _:
                        logger.info(f"Ignoring message with type {msg_type}")
            except KafkaException as e:
                print("Error occurred during message production:", e)
except KeyboardInterrupt:
    logger.info('Caught KeyboardInterrupt, stopping.')
finally:
    if position_producer is not None:
        position_producer.flush()
    if ship_voyage_producer is not None:
        ship_voyage_producer.flush()