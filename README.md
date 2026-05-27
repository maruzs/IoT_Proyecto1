# Inventario

## Inventario Placas/ Sensores

| Componente     | Nombre           | Voltaje 
| -------------- | ---------------- |-----------
| Placa Port.    | Arduino MKR 1000 |3.3v
| S. Gas         | MQ Sensor        |5v
| Camara         | ESP 32-CAM       |USB
| S. Temperatura | SHT30            |3.3v
| S. Humedad     | SHT30            |3.3v
| Microfono      | MAX4466          |3.3v

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
| Componente | Pin Sensor | Pin MKR 1000 | Tipo de Señal |
| ---------- | ---------- | ------------ | ------------- |
| MQ Sensor (Gas)   |  VCC / GND / AO         |  VCC / GND / A0  |  Analógica   |
| MAX4466 (Sonido)  |  VCC / GND / OUT        |  VCC / GND / A1  |  Analógica   |
| SHT30 (Temp/Hum)  |  VCC / GND / SDA / SCL  |  VCC / GND / 11 / 12  |  I2C [Inventario] |
| LED Alerta        |  Ánodo (+)              |  Pin 6           |  Digital |

### Pines SHT30

|**Color del Cable**|**Función I2C**|**Pin en el Arduino MKR1000**|
|---|---|---|
|🔴 **Rojo**|**VCC** (Energía)|**VCC** (Te entregará 3.3V, ideal para el SHT30)|
|⚫ **Negro**|**GND** (Tierra)|**GND**|
|🟡 **Amarillo**|**SCL** (Reloj)|**Pin 12**|
|🟢 **Verde**|**SDA** (Datos)|**Pin 11**|
sa