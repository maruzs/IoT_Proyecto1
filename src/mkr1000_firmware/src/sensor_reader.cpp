#include "sensor_reader.h"
#include "config.h"
#include <Wire.h>   
#include <Adafruit_SHT31.h>

static Adafruit_SHT31 sht30 = Adafruit_SHT31();


void initSensors() {
    // 2. Adafruit usa .begin(address) para inicializar. Retorna true si lo encuentra.
    if (!sht30.begin(0x44)) {
        // Opcional: Aquí podrías encender un led de error o mandar un mensaje por Serial
        // si el sensor no responde en la dirección 0x44
    }
    
    pinMode(PIN_GAS_DO, INPUT);
}

void initActuators() {
    pinMode(PIN_LED, OUTPUT);
    pinMode(PIN_BUZZER, OUTPUT);
    pinMode(PIN_LED_PUERTA, OUTPUT);
    pinMode(PIN_PRESENCIA, INPUT);
}

SensorData readAllSensors() {
    SensorData data = {};

    float temp = sht30.readTemperature();
    float hum = sht30.readHumidity();

    if (!isnan(temp) && !isnan(hum)) {
        data.temperature = temp; 
        data.humidity    = hum; 
        data.temperatureValid = true;
        data.humidityValid    = true;
    } else {
        data.temperatureValid = false;
        data.humidityValid    = false;
    }

    // MQ-2 (gas) — analogRead siempre devuelve valor; se considera valido.
    data.gas = analogRead(PIN_GAS);
    data.gasValid = true;

    // MQ-2 (gas digital) — HIGH = por debajo del umbral, LOW = por encima.
    data.gasDigital = digitalRead(PIN_GAS_DO);
    data.gasDigitalValid = true;

    // MAX4466 (sonido) — analogRead siempre devuelve valor; se considera valido.
    data.sound = analogRead(PIN_SONIDO);
    data.soundValid = true;

    return data;
}
