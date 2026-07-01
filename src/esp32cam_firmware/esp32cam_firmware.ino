// MQTT_MAX_PACKET_SIZE debe definirse antes que cualquier include de PubSubClient
#define MQTT_MAX_PACKET_SIZE 65536
#include "src/config.h"
#include "src/secrets.h"
#include "src/camera_server.h"
#include "src/mqtt_bridge.h"
#include "src/burst_capture.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <time.h>
#include "Arduino.h"

WiFiClientSecure secureClient;

// NTP: Argentina GMT-3
static const long GMT_OFFSET_SEC = -3 * 3600;
static const int  DAYLIGHT_OFFSET_SEC = 0;

static bool syncNTP() {
    configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, "pool.ntp.org", "time.nist.gov");
    Serial.print("NTP sync");
    struct tm timeinfo;
    int retries = 20;
    while (!getLocalTime(&timeinfo) && retries-- > 0) {
        delay(500);
        Serial.print(".");
    }
    if (retries <= 0) {
        Serial.println(" FALLO");
        return false;
    }
    Serial.println(" OK");
    return true;
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    char msg[128] = {0};
    unsigned int n = length < 127 ? length : 127;
    memcpy(msg, payload, n);
    msg[n] = '\0';
    Serial.print("CMD: "); Serial.println(msg);

    if (strcmp(topic, TOPIC_CAMARA_CAPTURA) == 0) {
        handleBurstCommand(msg);
    }
}

void setup() {
    Serial.begin(115200);
    Serial.println();  // blank line after bootloader noise
    Serial.println("ESP32-CAM boot");
    
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi OK");
    Serial.print("IP: "); Serial.println(WiFi.localIP());
    
    // NTP: obligatorio para validar fecha del certificado TLS
    if (!syncNTP()) {
        Serial.println("WARN: NTP fallo, TLS puede fallar por fecha invalida");
    }
    
    if (!initCamera()) {
        Serial.println("ERROR: initCamera fallo");
        return;
    }
    Serial.println("Camara OK");
    
    delay(500);
    Serial.print("MQTT TLS -> "); Serial.print(MQTT_SERVER); Serial.print(":"); Serial.print(MQTT_PORT); Serial.print("... ");
    initCameraMQTT(secureClient, MQTT_SERVER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD, CA_CERT);
    
    if (ensureCameraMQTTConnected()) {
        Serial.println("CONECTADO");
    } else {
        Serial.println("FALLO");
        return;
    }
    subscribeToCameraControl(mqttCallback);
    
    // Small delay to let MQTT pipeline stabilize before publishing
    delay(500);
    if (publishCameraEvent("camara_lista")) {
        Serial.println("Evento camara_lista publicado");
    } else {
        Serial.println("WARN: Evento camara_lista NO publicado (reintentando)");
        delay(1000);
        mqttLoop();
        if (publishCameraEvent("camara_lista")) {
            Serial.println("Evento camara_lista publicado (2do intento)");
        } else {
            Serial.println("WARN: Evento camara_lista NO publicado incluso tras reintento");
        }
    }
    Serial.println("Listo.");
}

void loop() {
    if (!isCameraMQTTConnected()) {
        Serial.println("MQTT desconectado, reconectando...");
        ensureCameraMQTTConnected();
    }
    mqttLoop();
    checkBurstTimeout();
    delay(MQTT_LOOP_DELAY_MS);
}
