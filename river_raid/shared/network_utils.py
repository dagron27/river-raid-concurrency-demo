import json
import logging

def serialize_message(message):
    try:
        serialized_message = json.dumps(message)
        #logging.info(f"Serialized message: {serialized_message}")
        return serialized_message
    except (TypeError, ValueError) as e:
        logging.error(f"Serialization error: {e}")
        return None

def deserialize_message(message_json):
    try:
        deserialized_message = json.loads(message_json)
        #logging.info(f"Deserialized message: {deserialized_message}")
        return deserialized_message
    except (json.JSONDecodeError, TypeError) as e:
        logging.error(f"Deserialization error: {e}, message_json: {message_json}")
        return None
