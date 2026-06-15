#ifndef MKR1000_MQTT_MANAGER_H
#define MKR1000_MQTT_MANAGER_H

/**
 * mqtt_manager.h — Gestion de conexion MQTT para MKR1000
 *
 * Abstrae reconexion, publicacion, suscripcion a topicos de control
 * y el callback de mensajes entrantes.
 */

#include <WiFi101.h>
#include <WiFiSSLClient.h>
#include <PubSubClient.h>

/** Configura el cliente MQTT con el WiFiSSLClient y el broker. */
void initMQTT(WiFiSSLClient& sslClient, const char* server,
              uint16_t port, const char* username,
              const char* password, const char* caCert);

/** Reconecta al broker si es necesario y resuscribe a topicos de control. */
bool ensureConnected();

/** Publica el payload JSON en TOPIC_DATOS. */
bool publishData(const char* payload);

/** Publica un mensaje de alerta en TOPIC_ALERTA. */
bool publishAlert(const char* alertMsg);

/** Suscribe a los topicos de control remoto (LED, buzzer y puerta). */
void subscribeToControlTopics();

/** Procesa el loop interno del cliente MQTT (keepalive + callbacks). */
void mqttLoop();

/** Verifica y apaga el LED de puerta si pasaron 2 segundos desde su activación. */
void checkDoorLedTimeout();

/** Callback de mensajes MQTT entrantes; activa/desactiva actuadores. */
void mqttCallback(char* topic, byte* payload, unsigned int length);

#endif
