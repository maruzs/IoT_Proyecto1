# Inventario

## Inventario Placas/ Sensores

| Componente     | Nombre           |
| -------------- | ---------------- |
| Placa Port.    | Arduino MKR 1000 |
| S. Gas         | MQ Sensor        |
| Camara         | ESP 32-CAM       |
| S. Temperatura | SHT30            |
| S. Humedad     | SHT30            |
| Microfono      | MAX4466          |

## Inventario Componentes

| Componente     | Cantidad |
| -------------- | -------- |
| Potenciometros | 4        |
| Led Amarillo   | 7        |
| Led Verde      | 9        |
| Led Rojos      | 10       |
| Led Azules     | 4        |


---

## Diagrama de pines:
Componente        |  Pin Sensor             |  Pin MKR 1000    |  Tipo de Señal
MQ Sensor (Gas)   |  VCC / GND / AO         |  VCC / GND / A0  |  Analógica   
MAX4466 (Sonido)  |  VCC / GND / OUT        |  VCC / GND / A1  |  Analógica   
SHT30 (Temp/Hum)  |  VCC / GND / SDA / SCL  |  VCC / GND / 11 / 12  |  I2C [Inventario]
LED Alerta        |  Ánodo (+)              |  Pin 6           |  Digital