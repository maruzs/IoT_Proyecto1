/**
 * burst_capture.cpp — Non-blocking burst capture state machine
 *
 * IDLE → BURSTING on {"accion":"iniciar_burst"}
 * BURSTING → IDLE after BURST_DURATION_S seconds
 * No delay() used; millis() comparison in checkBurstTimeout().
 */

#include "burst_capture.h"
#include "config.h"
#include "mqtt_bridge.h"
#include <esp_camera.h>
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
            burstState = STATE_BURSTING;
            burstStartMs = millis();

            camera_fb_t* fb = esp_camera_fb_get();
            if (fb) {
                publishCameraImage(fb->buf, fb->len);
                esp_camera_fb_return(fb);
            }
        }
    }
}

void checkBurstTimeout() {
    if (burstState == STATE_BURSTING) {
        if (millis() - burstStartMs >= BURST_DURATION_S * 1000UL) {
            publishToTopic(TOPIC_CAMARA_EVENTO, "{\"estado\":\"burst_complete\"}");
            burstState = STATE_IDLE;
        }
    }
}
