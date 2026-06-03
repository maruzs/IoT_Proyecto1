#include "mqtt_manager.h"
#include "config.h"
#include "alert_system.h"
#include <ArduinoJson.h>
#include <string.h>

static PubSubClient mqttClient;

void initMQTT(WiFiClient& wifiClient, const char* server) {
    mqttClient.setClient(wifiClient);
    mqttClient.setServer(server, 1883);
    mqttClient.setCallback(mqttCallback);
}

bool ensureConnected() {
    if (!mqttClient.connected()) {
        if (mqttClient.connect(EQUIPO_ID)) {
            subscribeToControlTopics();
            return true;
        }
        return false;
    }
    return true;
}

bool publishData(const char* payload) {
    if (!mqttClient.connected()) return false;
    return mqttClient.publish(TOPIC_DATOS, payload);
}

bool publishAlert(const char* alertMsg) {
    if (!mqttClient.connected()) return false;
    return mqttClient.publish(TOPIC_ALERTA, alertMsg);
}

bool publishPresence(int estado) {
    if (!mqttClient.connected()) return false;
    StaticJsonDocument<64> doc;
    doc["sensor"] = "HC-SR501";
    doc["estado"] = estado;
    char buffer[64];
    serializeJson(doc, buffer);
    return mqttClient.publish(TOPIC_PRESENCIA, buffer);
}

void subscribeToControlTopics() {
    mqttClient.subscribe(TOPIC_CONTROL_LED);
    mqttClient.subscribe(TOPIC_CONTROL_BUZZER);
    mqttClient.subscribe(TOPIC_CONTROL_LED_PUERTA);
}

void mqttLoop() {
    mqttClient.loop();
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    char msg[16] = {0};
    unsigned int copyLen = length < 15 ? length : 15;
    memcpy(msg, payload, copyLen);
    msg[copyLen] = '\0';

    bool state = (strcmp(msg, "ON") == 0 || strcmp(msg, "on") == 0 || strcmp(msg, "1") == 0);

    if (strcmp(topic, TOPIC_CONTROL_LED) == 0) {
        setActuatorState(PIN_LED, state);
    } else if (strcmp(topic, TOPIC_CONTROL_BUZZER) == 0) {
        setActuatorState(PIN_BUZZER, state);
    } else if (strcmp(topic, TOPIC_CONTROL_LED_PUERTA) == 0) {
        StaticJsonDocument<64> doc;
        DeserializationError error = deserializeJson(doc, payload, length);
        if (!error) {
            const char* accion = doc["accion"];
            if (accion) {
                bool doorState = (strcmp(accion, "ON") == 0 || strcmp(accion, "on") == 0);
                setActuatorState(PIN_LED_PUERTA, doorState);
            }
        }
    }
}
