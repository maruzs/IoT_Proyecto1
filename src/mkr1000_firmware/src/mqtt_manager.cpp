#include "mqtt_manager.h"
#include "config.h"
#include <ArduinoJson.h>
#include <string.h>
#include <Arduino.h>

static PubSubClient mqttClient;
static unsigned long doorLedOnTime = 0;
static bool doorLedTimed = false;
static const char* mqttUsername = nullptr;
static const char* mqttPassword = nullptr;

static void setActuatorState(int pin, bool state) {
    digitalWrite(pin, state ? HIGH : LOW);
}

void initMQTT(WiFiSSLClient& sslClient, const char* server,
              uint16_t port, const char* username,
              const char* password, const char* caCert) {
    // WiFi101 (SAMD21/MKR1000): WiFiSSLClient no expone setCACert() ni 
    // setEphemeralKeyPair(). El canal TLS se establece pero sin verificar 
    // el certificado del servidor. La autenticación MQTT (usuario/password) 
    // sigue activa. Para verificar la CA hay que usar WiFi101 Firmware Updater.
    // Parámetro caCert reservado para compatibilidad con ESP32-CAM.
    (void)caCert;
    mqttClient.setClient(sslClient);
    mqttClient.setServer(server, port);
    mqttClient.setCallback(mqttCallback);
    mqttUsername = username;
    mqttPassword = password;
}

bool ensureConnected() {
    if (!mqttClient.connected()) {
        if (mqttClient.connect(EQUIPO_ID, mqttUsername, mqttPassword)) {
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
                if (strcmp(accion, "ON") == 0 || strcmp(accion, "on") == 0) {
                    setActuatorState(PIN_LED_PUERTA, true);
                    doorLedOnTime = millis();
                    doorLedTimed = true;
                } else {
                    setActuatorState(PIN_LED_PUERTA, false);
                    doorLedTimed = false;
                }
            }
        }
    }
}

void checkDoorLedTimeout() {
    if (doorLedTimed && (millis() - doorLedOnTime >= 3000)) {
        setActuatorState(PIN_LED_PUERTA, false);
        doorLedTimed = false;
    }
}
