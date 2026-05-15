const int sampleWindow = 50; // Ancho de muestra en ms (20Hz)
unsigned int sample;

void setup() {
  Serial.begin(9600);
  // El MKR 1000 no requiere configuracion especial para A1
}

void loop() {
  unsigned long startMillis = millis(); 
  unsigned int peakToPeak = 0;   

  unsigned int signalMax = 0;
  unsigned int signalMin = 1023;

  // Recolectar datos por 50ms
  while (millis() - startMillis < sampleWindow) {
    sample = analogRead(A1);
    if (sample < 1023) {
      if (sample > signalMax) signalMax = sample;
      else if (sample < signalMin) signalMin = sample;
    }
  }
  peakToPeak = signalMax - signalMin;  // Amplitud del sonido
  
  // Mapeo simple para el dashboard
  int volts = (peakToPeak * 3.3) / 1023; 

  Serial.print("Nivel de Sonido: ");
  Serial.println(peakToPeak);

  // Aqui iran las reglas de control automatico despues
  if (peakToPeak > 500) { 
    Serial.println("ALERTA: Ruido detectado"); 
  }
  
  delay(500);
}