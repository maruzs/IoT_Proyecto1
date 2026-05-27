#include "mqtt_manager.h"
#include "config.h"
#include "alert_system.h"
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

void subscribeToControlTopics() {
    mqttClient.subscribe(TOPIC_CONTROL_LED);
    mqttClient.subscribe(TOPIC_CONTROL_BUZZER);
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
    }
}
