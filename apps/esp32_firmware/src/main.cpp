#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// WiFi Configuration
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// MQTT Configuration
const char* mqtt_server = "192.168.1.100"; // Local gateway IP
const int mqtt_port = 1883;
const char* mqtt_topic_csi = "tryops/store/123/csi";
const char* node_id = "node_01";
const int fitting_room_id = 1;

WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
    delay(10);
    Serial.println();
    Serial.print("Connecting to ");
    Serial.println(ssid);

    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("");
    Serial.println("WiFi connected");
    Serial.println("IP address: ");
    Serial.println(WiFi.localIP());
}

void reconnect() {
    while (!client.connected()) {
        Serial.print("Attempting MQTT connection...");
        if (client.connect(node_id)) {
            Serial.println("connected");
        } else {
            Serial.print("failed, rc=");
            Serial.print(client.state());
            Serial.println(" try again in 5 seconds");
            delay(5000);
        }
    }
}

void setup() {
    Serial.begin(115200);
    setup_wifi();
    client.setServer(mqtt_server, mqtt_port);
}

void loop() {
    if (!client.connected()) {
        reconnect();
    }
    client.loop();

    // 10Hz sampling rate simulation
    static unsigned long lastMsg = 0;
    unsigned long now = millis();
    if (now - lastMsg > 100) {
        lastMsg = now;

        StaticJsonDocument<256> doc;
        doc["node_id"] = node_id;
        doc["fitting_room_id"] = fitting_room_id;
        // In a real device, this would be epoch time via NTP
        doc["timestamp_ms"] = now; 
        // Dummy RSSI
        doc["rssi"] = random(-70, -40);
        
        JsonArray csi = doc.createNestedArray("csi_data");
        // Sending a few dummy subcarriers for skeleton
        for (int i = 0; i < 4; i++) {
            csi.add(random(-128, 127));
        }

        char output[256];
        serializeJson(doc, output);
        
        client.publish(mqtt_topic_csi, output);
    }
}
