#ifndef MKR1000_SENSOR_READER_H
#define MKR1000_SENSOR_READER_H

/**
 * sensor_reader.h — Lectura modular de sensores MKR1000
 *
 * Agrupa lecturas de SHT30, MQ-2 y MAX4466 en un struct con flags
 * de validez para poder publicar null cuando un sensor falla.
 */

struct SensorData {
    float temperature;
    bool temperatureValid;
    float humidity;
    bool humidityValid;
    int gas;
    bool gasValid;
    int sound;
    bool soundValid;
};

/** Inicializa sensores (verifica comunicacion con SHT30). */
void initSensors();

/** Lee todos los sensores y devuelve un SensorData con flags de validez. */
SensorData readAllSensors();

#endif
