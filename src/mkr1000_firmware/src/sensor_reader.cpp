#include "sensor_reader.h"
#include "config.h"
#include <WEMOS_SHT3X.h>

static SHT3X sht30(0x44);   // I2C address 0x44

void initSensors() {
    // Un get() inicial detecta desconexion temprana del SHT30.
    sht30.get();
}

void initActuators() {
    pinMode(PIN_LED, OUTPUT);
    pinMode(PIN_BUZZER, OUTPUT);
}

SensorData readAllSensors() {
    SensorData data = {};

    // SHT30: temperatura + humedad
    if (sht30.get() == 0) {
        data.temperature = sht30.cTemp;
        data.humidity    = sht30.humidity;
        data.temperatureValid = true;
        data.humidityValid    = true;
    } else {
        data.temperatureValid = false;
        data.humidityValid    = false;
    }

    // MQ-2 (gas) — analogRead siempre devuelve valor; se considera valido.
    data.gas = analogRead(PIN_GAS);
    data.gasValid = true;

    // MAX4466 (sonido) — analogRead siempre devuelve valor; se considera valido.
    data.sound = analogRead(PIN_SONIDO);
    data.soundValid = true;

    return data;
}
