#include "src/config.h"
#include "src/secrets.h"
#include "src/sensor_reader.h"
<<<<<<< HEAD
#include "src/mqtt_manager.h"
#include "src/message_builder.h"
#include "src/alert_system.h"
#include <WiFi101.h>
#include <Arduino.h> 
=======
#include "Arduino.h"
>>>>>>> 788047d0e5f603fcc241bd9306032586a46c6b3a

WiFiClient wifiClient;
unsigned long lastPublishTime = 0;

void setup() {
  Serial.begin(9600);
  // Opcional: while (!Serial) { }

  initSensors();
  initActuators();

  Serial.println("\n=== Diagnostico WiFi ===");
  Serial.print("Libreria WiFi101 version: ");
  Serial.println(WiFi.firmwareVersion());

  Serial.print("Conectando a SSID: '");
  Serial.print(WIFI_SSID);
  Serial.println("'");

  // Escanear redes visibles para ver si el hotspot es detectable
  Serial.println("Escaneando redes cercanas...");
  int numSsid = WiFi.scanNetworks();
  bool found = false;
  if (numSsid == -1) {
    Serial.println("Fallo al escanear redes WiFi.");
  } else {
    Serial.print("Redes encontradas: ");
    Serial.println(numSsid);
    for (int thisNet = 0; thisNet < numSsid; thisNet++) {
      Serial.print(thisNet + 1);
      Serial.print(") ");
      Serial.print(WiFi.SSID(thisNet));
      Serial.print("\tSeñal: ");
      Serial.print(WiFi.RSSI(thisNet));
      Serial.println(" dBm");
      if (strcmp(WiFi.SSID(thisNet), WIFI_SSID) == 0) {
        found = true;
      }
    }
  }

  if (found) {
    Serial.println("✓ Tu hotspot FUE detectado en el escaneo.");
  } else {
    Serial.println("✗ Tu hotspot NO fue detectado. Revisa si esta activo y en 2.4GHz.");
  }

  Serial.println("Iniciando conexion...");
  if (strlen(WIFI_PASSWORD) > 0) {
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  } else {
    WiFi.begin(WIFI_SSID);
  }
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    attempts++;
    Serial.print("Intento ");
    Serial.print(attempts);
    Serial.print(" - Estado WiFi: ");
    
    // Decodificar el estado de la conexion
    switch (WiFi.status()) {
      case WL_IDLE_STATUS:     Serial.println("WL_IDLE_STATUS (Inactivo)"); break;
      case WL_NO_SSID_AVAIL:   Serial.println("WL_NO_SSID_AVAIL (SSID no disponible)"); break;
      case WL_SCAN_COMPLETED:  Serial.println("WL_SCAN_COMPLETED (Escaneo completo)"); break;
      case WL_CONNECTED:       Serial.println("WL_CONNECTED (Conectado)"); break;
      case WL_CONNECT_FAILED:  Serial.println("WL_CONNECT_FAILED (Conexion fallida)"); break;
      case WL_CONNECTION_LOST: Serial.println("WL_CONNECTION_LOST (Conexion perdida)"); break;
      case WL_DISCONNECTED:    Serial.println("WL_DISCONNECTED (Desconectado)"); break;
      default:                 Serial.println(WiFi.status()); break;
    }

    if (attempts > 30) {
      Serial.println("Demasiados intentos. Reiniciando WiFi.begin...");
      WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
      attempts = 0;
    }
  }
  Serial.println("\n✓ WiFi Conectado Exitosamente!");
  Serial.print("IP Asignada: ");
  Serial.println(WiFi.localIP());

  // Inicializar MQTT
  initMQTT(wifiClient, MQTT_SERVER);
}

void loop() {
  // Asegura la conexión al broker
  if (!ensureConnected()) {
    delay(1000);
    return;
  }
  mqttLoop();

  // Publicar de manera no bloqueante cada X segundos
  if (millis() - lastPublishTime >= PUBLISH_INTERVAL_MS) {
    lastPublishTime = millis();
    
    SensorData data = readAllSensors();
    
    // Evaluar alertas locales y actuar sobre LED/Buzzer
    const char* alertMsg = evaluateAndActuate(data);
    
    // Construir JSON y publicar
    char jsonBuffer[256];
    buildSensorJSON(data, jsonBuffer, sizeof(jsonBuffer), alertMsg);
    
    if (publishData(jsonBuffer)) {
      Serial.print("Publicado MQTT: ");
      Serial.println(jsonBuffer);
    } else {
      Serial.println("Error al publicar en MQTT");
    }
  }
}

