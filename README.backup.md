# Inventario

## Inventario Placas/ Sensores

| Componente     | Nombre           | Voltaje |
| -------------- | ---------------- | ------- |
| Placa Port.    | Arduino MKR 1000 | 3.3v    |
| S. Gas         | MQ Sensor        | 5v      |
| Camara         | ESP 32-CAM       | USB     |
| S. Temperatura | SHT30            | 3.3v    |
| S. Humedad     | SHT30            | 3.3v    |
| Microfono      | MAX4466          | 3.3v    |

## Inventario Componentes

| Componente     | Cantidad |
| -------------- | -------- |
| Potenciometros | 4        |
| Led Amarillo   | 7        |
| Led Verde      | 9        |
| Led Rojos      | 10       |
| Led Azules     | 4        |


---

## Diagrama de pines — MKR1000

### Actuadores

| Componente | Pin MKR1000 | Tipo de Señal |
| ---------- | ----------- | ------------- |
| LED Alerta | **6** | Digital (PWM) |
| LED Puerta | **8** | Digital (PWM) |

### MQ Sensor (Gas)

| Pin Sensor | Pin MKR1000 | Tipo de Señal |
| ---------- | ----------- | ------------- |
| AO         |  **A0**     | Analógica     |
| D0         |  **A2**     | Digital       |
| VCC        |  **5V**     |               |
| GND        |  **GND**    |               |

### MAX4466 (Sonido)

| Pin Sensor | Pin MKR1000 | Tipo de Señal |
| ---------- | ----------- | ------------- |
| OUT        |  **A1**     | Analógica     |
| VCC        | **VCC (3.3V)** |            |
| GND        |  **GND**    |               |

### Pines SHT30 (Temp/Hum) — Detalle por color de cable

| Color del Cable | Función I2C | Pin MKR1000 |
| --------------- | ----------- | ----------- |
| 🔴 Rojo   | VCC (3.3V) | VCC |
| ⚫ Negro  | GND        | GND |
| 🟢 Verde  | SDA (Datos) | **11** |
| 🟡 Amarillo | SCL (Reloj) | **12** |


> Para cambiar un pin, editá solo `src/mkr1000_firmware/src/config.h`.
