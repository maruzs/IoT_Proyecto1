#include <Arduino.h>
#include <Wire.h>
#include "Adafruit_SHT31.h"

// Creamos un objeto para el sensor
Adafruit_SHT31 sht30 = Adafruit_SHT31();

void setup() {
  // Iniciamos la comunicación serial a 9600 baudios
  Serial.begin(9600);
  
  // Esperamos a que se abra el Monitor Serie (útil para placas MKR)
  while (!Serial)
    delay(10);     

  Serial.println("Prueba de Sensor SHT30 con MKR1000");

  // Iniciamos el sensor en la dirección I2C 0x44
  // Si te da error de conexión, intenta cambiar a 0x45
  if (!sht30.begin(0x44)) {
    Serial.println("¡No se pudo encontrar un SHT30! Revisa las conexiones.");
    while (1) delay(1); // Detiene el código aquí si hay error
  }
  
  Serial.println("Sensor SHT30 detectado con éxito.");
  Serial.println("-----------------------------------");
}

void loop() {
  // Leemos la temperatura y la humedad
  float temperatura = sht30.readTemperature();
  float humedad = sht30.readHumidity();

  // Verificamos si las lecturas fallaron (NaN = Not a Number)
  if (!isnan(temperatura)) {  
    Serial.print("Temperatura: ");
    Serial.print(temperatura);
    Serial.println(" °C");
  } else { 
    Serial.println("Error al leer la temperatura");
  }

  if (!isnan(humedad)) {  
    Serial.print("Humedad: ");
    Serial.print(humedad);
    Serial.println(" %");
  } else { 
    Serial.println("Error al leer la humedad");
  }

  Serial.println("-----------------------------------");
  
  // Esperamos 2 segundos antes de la siguiente lectura
  delay(1000);
}
