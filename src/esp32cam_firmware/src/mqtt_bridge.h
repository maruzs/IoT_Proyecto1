/**
 * mqtt_bridge.h — ESP32-CAM MQTT Integration
 *
 * Declara funciones para conectar el ESP32-CAM al broker MQTT,
 * publicar eventos de cámara y suscribirse a comandos de control.
 */

#ifndef MQTT_BRIDGE_H
#define MQTT_BRIDGE_H

#include <WiFi.h>
#include <PubSubClient.h>

void initCameraMQTT(WiFiClient& wifiClient, const char* server);
bool ensureCameraMQTTConnected();
bool isCameraMQTTConnected();
bool publishCameraEvent(const char* event);
void subscribeToCameraControl(void (*callback)(char*, byte*, unsigned int));
void mqttLoop();

#endif
