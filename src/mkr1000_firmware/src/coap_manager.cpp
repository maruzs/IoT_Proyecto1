#include "coap_manager.h"
#include "config.h"
#include <Arduino.h>

static WiFiUDP coapUdp;
static Coap coapClient(coapUdp);

static const char* coapServer = nullptr;
static uint16_t coapPort = 0;

void initCoAP(const char* server, uint16_t port) {
  coapServer = server;
  coapPort = port;
  Serial.print("CoAP server: "); Serial.print(server); Serial.print(":"); Serial.println(port);
}

static void sendSensor(IPAddress ip, const char* path, const char* payload) {
  coapClient.send(
    ip, coapPort, path,
    COAP_NONCON, COAP_POST,
    nullptr, 0,
    reinterpret_cast<const uint8_t*>(payload), strlen(payload),
    COAP_APPLICATION_JSON
  );
}

void coapSendSensorData(const SensorData& data) {
  if (coapServer == nullptr || coapPort == 0) return;

  IPAddress ip;
  if (WiFi.hostByName(coapServer, ip) != 1) {
    Serial.print("CoAP DNS fail: "); Serial.println(coapServer);
    return;
  }

  // Abrimos el socket UDP solo para este ciclo de envios y lo cerramos
  // despues, evitando mantenerlo persistente en el ATWINC1500.
  if (!coapUdp.begin(COAP_LOCAL_PORT)) {
    Serial.println("CoAP UDP begin failed");
    return;
  }

  char payload[64];

  if (data.temperatureValid) {
    snprintf(payload, sizeof(payload), "{\"temperatura\":%.2f}", data.temperature);
    sendSensor(ip, "sensores/temperatura", payload);
  }

  if (data.humidityValid) {
    snprintf(payload, sizeof(payload), "{\"humedad\":%.2f}", data.humidity);
    sendSensor(ip, "sensores/humedad", payload);
  }

  if (data.gasValid) {
    snprintf(payload, sizeof(payload), "{\"gas\":%d}", data.gas);
    sendSensor(ip, "sensores/gas", payload);
  }

  coapUdp.stop();
}
