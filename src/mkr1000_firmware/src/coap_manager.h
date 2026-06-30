#ifndef MKR1000_COAP_MANAGER_H
#define MKR1000_COAP_MANAGER_H

/**
 * coap_manager.h — Publicacion CoAP NON POST de sensores MKR1000
 *
 * Envia cada sensor valido como un POST individual al CoAP Bridge.
 * No bloquea el canal MQTT; fallos de UDP se ignoran silenciosamente.
 */

#include "sensor_reader.h"
#include <WiFi101.h>
#include <WiFiUdp.h>

// Buffer para PDUs CoAP. La libreria usa COAP_BUF_MAX_SIZE; mantenemos
// COAP_MAX_PDU_SIZE por compatibilidad con la especificacion SDD.
#define COAP_MAX_PDU_SIZE 256
#define COAP_BUF_MAX_SIZE 256
#include <coap-simple.h>

/** Guarda servidor/puerto e imprime configuracion CoAP. */
void initCoAP(const char* server, uint16_t port);

/** Envia 3 POSTs NON (temperatura, humedad, gas) si son validos. */
void coapSendSensorData(const SensorData& data);

#endif
