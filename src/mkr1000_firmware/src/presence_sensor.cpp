#include "presence_sensor.h"
#include "config.h"
#include <Arduino.h>

static bool stableState = false;
static bool lastReading = false;
static unsigned long lastDebounceTime = 0;

bool readPresence() {
    bool reading = digitalRead(PIN_PRESENCIA) == HIGH;
    unsigned long now = millis();

    if (reading != lastReading) {
        lastDebounceTime = now;
        lastReading = reading;
    }

    if ((now - lastDebounceTime) >= 1000) {
        stableState = reading;
    }

    return stableState;
}
