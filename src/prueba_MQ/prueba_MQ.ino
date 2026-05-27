#include <Arduino.h>

// Definimos el pin analógico para el sensor de gas
const int pinMQ = A0;

void setup() {
  // Iniciamos la comunicación serial a 9600 baudios
  Serial.begin(9600);
  
  // Esperamos a que se abra el Monitor Serie (útil para placas MKR)
  while (!Serial)
    delay(10);     

  Serial.println("Prueba de Sensor MQ (Gas) con MKR1000");
  Serial.println("Nota: El sensor requiere unos minutos de calentamiento.");
  Serial.println("-----------------------------------");
  
  // Configuramos el pin como entrada
  pinMode(pinMQ, INPUT);
}

void loop() {
  // Leemos el valor analógico del sensor de gas (0 a 1023)
  int valorGas = analogRead(pinMQ);

  // Verificamos si la lectura es válida 
  // (analogRead siempre devuelve un valor, pero validamos rango básico)
  if (valorGas >= 0) {  
    Serial.print("Nivel de Gas/Humo: ");
    Serial.print(valorGas);
    
    // Interpretación básica para el Monitor Serie
    if (valorGas > 400) {
      Serial.println(" [ALERTA: Concentracion Alta]");
    } else {
      Serial.println(" [Nivel Normal]");
    }
  } else { 
    Serial.println("Error al leer el sensor MQ");
  }

  Serial.println("-----------------------------------");
  
  // Esperamos 1 segundo antes de la siguiente lectura
  delay(1000);
}