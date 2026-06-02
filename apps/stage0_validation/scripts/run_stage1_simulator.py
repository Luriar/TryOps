"""
🟢 신뢰도: 높음 (Stage 1 docker-compose 시뮬레이션용)
"""

import time
import requests
import json
import logging
import sys

try:
    import paho.mqtt.publish as publish
except ImportError:
    print("Please pip install paho-mqtt requests")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stage1_simulator")

def run():
    broker = "localhost"
    port = 1883
    topic = "tryops/store/123/raw"
    
    logger.info("Sending mock MQTT events to %s:%s...", broker, port)
    
    # 1. Send an event simulating RFID tag entering the fitting room
    payload1 = {
        "sensor_id": "rfid_01",
        "timestamp": int(time.time()),
        "event_type": "tag_read",
        "sku": "TSHIRT-WHT-M"
    }
    
    try:
        publish.single(topic, payload=json.dumps(payload1), hostname=broker, port=port)
        logger.info("Sent MQTT Event: %s", payload1)
    except Exception as e:
        logger.error("MQTT Publish failed (Is Mosquitto running?): %s", e)
        return

    # Wait for gateway to process and ingest
    logger.info("Waiting 3 seconds for gateway to process and Ingest API to forward...")
    time.sleep(3)
    
    # 2. Check the local Query API
    query_url = "http://localhost:8081/api/v1/store/123/status"
    logger.info("Querying local dashboard API at %s...", query_url)
    
    try:
        headers = {"Authorization": "Bearer mock-token-data-lead"}
        res = requests.get(query_url, headers=headers)
        if res.status_code == 200:
            logger.info("Success! Query API Response:")
            logger.info(json.dumps(res.json(), indent=2))
        else:
            logger.error("Query API Error: %s %s", res.status_code, res.text)
    except Exception as e:
        logger.error("Query HTTP Request failed (Is gcp-query running?): %s", e)

if __name__ == "__main__":
    run()
