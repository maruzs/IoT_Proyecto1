#ifndef MKR1000_MQTT_MANAGER_H
#define MKR1000_MQTT_MANAGER_H

/**
 * mqtt_manager.h — Gestion de conexion MQTT para MKR1000
 *
 * Abstrae reconexion, publicacion, suscripcion a topicos de control
 * y el callback de mensajes entrantes.
 */

#include <WiFi101.h>
#include <PubSubClient.h>

/** Configura el cliente MQTT con el WiFiClient y el broker. */
void initMQTT(WiFiClient& wifiClient, const char* server);

/** Reconecta al broker si es necesario y resuscribe a topicos de control. */
bool ensureConnected();

/** Publica el payload JSON en TOPIC_DATOS. */
bool publishData(const char* payload);

/** Publica un mensaje de alerta en TOPIC_ALERTA. */
bool publishAlert(const char* alertMsg);

/** Suscribe a los topicos de control remoto (LED y buzzer). */
void subscribeToControlTopics();

/** Procesa el loop interno del cliente MQTT (keepalive + callbacks). */
void mqttLoop();

/** Callback de mensajes MQTT entrantes; activa/desactiva actuadores. */
void mqttCallback(char* topic, byte* payload, unsigned int length);

#endif
