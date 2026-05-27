#include "src/config.h"
#include "src/sensor_reader.h"

void setup() {
  Serial.begin(9600);
  while (!Serial) { }  // Esperar a que el monitor serial se abra

  initSensors();
  initActuators();

  Serial.println("=== MKR1000 - Lectura de Sensores ===");
  Serial.print("Gas (MQ-2):    pin ");
  Serial.println(PIN_GAS);
  Serial.print("Sonido (MAX4466): pin ");
  Serial.println(PIN_SONIDO);
  Serial.println("SHT30: I2C (SDA=11, SCL=12)");
  Serial.println("=====================================");
}

void loop() {
  SensorData data = readAllSensors();

  Serial.print("Temperatura: ");
  if (data.temperatureValid) {
    Serial.print(data.temperature);
    Serial.print(" C");
  } else {
    Serial.print("ERROR (SHT30 no responde)");
  }

  Serial.print(" | Humedad: ");
  if (data.humidityValid) {
    Serial.print(data.humidity);
    Serial.print(" %");
  } else {
    Serial.print("ERROR (SHT30 no responde)");
  }

  Serial.print(" | Gas: ");
  Serial.print(data.gas);

  Serial.print(" | Gas DO: ");
  Serial.print(data.gasDigital == HIGH ? "NORMAL" : "ALERTA");

  Serial.print(" | Sonido: ");
  Serial.println(data.sound);

  delay(PUBLISH_INTERVAL_MS);
}
