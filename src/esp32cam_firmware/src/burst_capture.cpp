/**
 * burst_capture.cpp — Non-blocking burst capture state machine
 *
 * IDLE → BURSTING on {"accion":"iniciar_burst"}
 * BURSTING → IDLE after BURST_DURATION_S seconds
 * No delay() used; millis() comparison in checkBurstTimeout().
 */

#include "burst_capture.h"
#include "config.h"
#include "camera_server.h"
#include "mqtt_bridge.h"
#include <WiFi.h>
#include <Arduino.h>

enum BurstState {
    STATE_IDLE,
    STATE_BURSTING
};

static BurstState burstState = STATE_IDLE;
static unsigned long burstStartMs = 0;

void handleBurstCommand(const char* payload) {
    if (strstr(payload, "iniciar_burst") != NULL) {
        if (burstState == STATE_IDLE) {
            startCameraServer();
            IPAddress ip = WiFi.localIP();
            char url[64];
            snprintf(url, sizeof(url), "http://%d.%d.%d.%d/",
                     ip[0], ip[1], ip[2], ip[3]);
            publishToTopic(TOPIC_CAMARA_URL, url);
            burstState = STATE_BURSTING;
            burstStartMs = millis();
        }
    }
}

void checkBurstTimeout() {
    if (burstState == STATE_BURSTING) {
        if (millis() - burstStartMs >= BURST_DURATION_S * 1000UL) {
            stopCameraServer();
            publishToTopic(TOPIC_CAMARA_EVENTO, "{\"estado\":\"burst_complete\"}");
            burstState = STATE_IDLE;
        }
    }
}
