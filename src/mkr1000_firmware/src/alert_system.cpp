#include "alert_system.h"
#include "config.h"

const char* evaluateAndActuate(const SensorData& data) {
    bool triggered = false;

    if (data.gasValid && data.gas > UMBRAL_GAS) {
        triggered = true;
    }
    if (data.temperatureValid && data.temperature > UMBRAL_TEMP) {
        triggered = true;
    }
    if (data.soundValid && data.sound > UMBRAL_SONIDO) {
        triggered = true;
    }

    if (triggered) {
        setActuatorState(PIN_LED, true);
        setActuatorState(PIN_BUZZER, true);
        return "Condicion anomala detectada";
    }

    setActuatorState(PIN_LED, false);
    setActuatorState(PIN_BUZZER, false);
    return nullptr;
}

void setActuatorState(int pin, bool state) {
    digitalWrite(pin, state ? HIGH : LOW);
}
