#include <WiFi101.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <WEMOS_SHT3X.h>

// Configuración de Red y MQTT
const char* ssid = "TU_WIFI_NOMBRE";
const char* password = "TU_WIFI_PASSWORD";
const char* mqtt_server = "IP_DE_TU_SERVER_DOCKER"; // La IPv4 que obtuviste con ipconfig
const char* equipoID = "equipoXX"; // Cambia XX por tu numero

WiFiClient mkrClient;
PubSubClient client(mkrClient);
SHT3X sht30(0x44);

// Pines
const int pinGas = A0;
const int pinSonido = A1;
const int pinLED = 6;

void setup() {
  Serial.begin(9600);
  pinMode(pinLED, OUTPUT);
  
  // Conexión WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  
  client.setServer(mqtt_server, 1883);
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect(equipoID)) {
      // Suscribirse a tópicos de control si es necesario
      client.subscribe("smarthome/equipoXX/control/led");
    } else {
      delay(5000);
    }
  }
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  // Lectura de Sensores
  float temp = 0.0, hum = 0.0;
  if(sht30.get()==0){
    temp = sht30.cTemp;
    hum = sht30.humidity;
  }

  int valorGas = analogRead(pinGas);
  int valorSonido = analogRead(pinSonido); // Usado como sensor diferencial

  // Crear JSON 
  StaticJsonDocument<256> doc;
  doc["equipo"] = equipoID;
  doc["temperatura"] = temp;
  doc["humedad"] = hum;
  doc["gas"] = valorGas;
  doc["sensor_extra"] = valorSonido;

  // Evaluar Alerta simple (Control automático base) [cite: 68]
  if (valorGas > 400 || temp > 30) {
    doc["alerta"] = "Condicion anomala detectada";
    digitalWrite(pinLED, HIGH);
  } else {
    digitalWrite(pinLED, LOW);
  }

  char buffer[256];
  serializeJson(doc, buffer);

  // Publicar en jerarquía de tópicos [cite: 32, 33, 34]
  // Se recomienda enviar el JSON completo a un tópico base o separar por variable
  client.publish("smarthome/equipoXX/datos", buffer); 

  delay(2000); // Enviar cada 2 segundos
}