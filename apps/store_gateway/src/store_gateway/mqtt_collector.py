import json
import logging
import asyncio
import paho.mqtt.client as mqtt
from .config import config
from .storage import storage

logger = logging.getLogger(__name__)

class MQTTCollector:
    """Listens to ESP32-S3 CSI data over MQTT and inserts into SQLite."""
    
    def __init__(self):
        self.client = mqtt.Client(client_id=f"{config.STORE_ID}_gateway")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT Broker at {config.MQTT_HOST}:{config.MQTT_PORT}")
            self.client.subscribe("csi/+")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")

    def on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from MQTT broker with code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            
            node_id = payload.get("node_id")
            fitting_room_id = payload.get("fitting_room_id")
            timestamp_ms = payload.get("timestamp_ms")
            rssi = payload.get("rssi")
            csi_data = payload.get("csi_data")
            
            # Simple compression for local storage: just store as JSON string
            csi_blob = json.dumps(csi_data) if csi_data else "{}"
            
            if node_id and fitting_room_id and timestamp_ms:
                storage.insert_raw_csi(
                    node_id=node_id,
                    fitting_room_id=fitting_room_id,
                    timestamp_ms=timestamp_ms,
                    rssi=rssi,
                    csi_blob=csi_blob
                )
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def start(self):
        """Start the MQTT loop in a background thread (managed by paho-mqtt)."""
        logger.info("Starting MQTT Collector...")
        try:
            self.client.connect(config.MQTT_HOST, config.MQTT_PORT, 60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Failed to start MQTT collector: {e}")

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
