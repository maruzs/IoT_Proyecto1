# Spec: Registro Histórico — Persistencia de Datos en CSV o Base de Datos

## Contexto

El sistema DEBE registrar continuamente un histórico de datos para análisis posterior. El registro incluye timestamp, variables físicas y estado de alertas. Se puede usar archivo CSV o base de datos (InfluxDB / SQLite).

## Requisitos Funcionales

### RF-1: Datos a registrar

Cada registro DEBE incluir como mínimo:
- **timestamp**: fecha y hora de la lectura (ISO 8601)
- **temperatura**: valor en °C
- **humedad**: valor en %
- **gas**: valor analógico o ppm
- **sensor_extra**: valor del sensor diferencial (sonido)
- **alerta**: estado de alerta (true/false o descripción)

### RF-2: Formato CSV

Si se usa CSV, el archivo DEBE tener la siguiente estructura:
```csv
timestamp,temperatura,humedad,gas,sensor_extra,alerta
2026-05-26T10:30:00Z,25.3,60.2,320,45,false
2026-05-26T10:30:02Z,25.4,60.1,325,47,false
2026-05-26T10:30:04Z,26.1,59.8,410,52,"gas_alto"
```

### RF-3: Implementación en Node-RED

- El registro DEBE implementarse como un flujo de Node-RED
- Suscribirse a los tópicos de sensores y consolidar los datos
- Escribir un registro por cada ciclo de lectura (cada 2-5 segundos)
- Usar `node-red-contrib-file` o `node-red-node-csv` para escritura CSV
- O usar `node-red-contrib-influxdb` / SQLite para base de datos

### RF-4: Rotación de archivos

- Si se usa CSV, el archivo DEBE rotarse diariamente o al alcanzar un tamaño máximo
- Formato de nombre: `smarthome_equipoXX_YYYY-MM-DD.csv`
- Los archivos antiguos NO deben eliminarse automáticamente (se necesitan para el informe)

### RF-5: Ubicación del archivo

- Los archivos CSV DEBEN guardarse en un directorio accesible
- Ruta recomendada: `data/historico/` dentro del repositorio o directorio del proyecto
- El directorio DEBE crearse automáticamente si no existe

### RF-6: Registro de eventos de alerta

- Además del registro periódico, registrar cada evento de alerta con:
  - Timestamp
  - Tipo de alerta
  - Valor que disparó la alerta
  - Acciones ejecutadas

## Requisitos No Funcionales

### RNF-1: Rendimiento

- La escritura del histórico NO debe bloquear el flujo principal
- Usar escritura asíncrona o buffer para evitar pérdida de datos
- Máximo 100ms de latencia adicional por escritura

### RNF-2: Integridad de datos

- NO perder datos si Node-RED se reinicia
- Si se usa CSV, asegurar que el archivo se cierre correctamente
- Usar append mode para evitar sobrescribir datos existentes

### RNF-3: Accesibilidad para el informe

- Los datos registrados DEBEN ser fácilmente exportables para el informe técnico
- Formato CSV es preferible para análisis con Excel, Python, etc.
- Incluir encabezados descriptivos en el archivo

## Escenarios de Aceptación

### Escenario 1: Registro continuo
```
DADO que el sistema está corriendo
CUANDO pasan 10 minutos
ENTONCES el archivo CSV contiene al menos 100 registros
Y cada registro tiene timestamp, temperatura, humedad, gas, sensor_extra y alerta
```

### Escenario 2: Registro de alerta
```
DADO que se detectó gas alto
CUANDO se escribe el registro correspondiente
ENTONCES el campo "alerta" contiene "gas_alto" o descripción similar
Y los valores de sensores se registran correctamente
```

### Escenario 3: Rotación diaria
```
DADO que es medianoche
CUANDO se escribe el primer registro del nuevo día
ENTONCES se crea un nuevo archivo con la fecha actual
Y el archivo anterior se mantiene intacto
```

### Escenario 4: Datos accesibles para análisis
```
DADO que el sistema ha estado corriendo por 1 hora
CUANDO se abre el archivo CSV en Excel
ENTONCES los datos se importan correctamente en columnas
Y se puede generar un gráfico a partir de los datos
```

## Criterios de Éxito

1. [ ] Archivo CSV o base de datos se crea automáticamente
2. [ ] Los registros incluyen todos los campos requeridos
3. [ ] El registro es continuo (cada 2-5 segundos)
4. [ ] Los eventos de alerta se registran con detalle
5. [ ] Los archivos rotan diariamente o por tamaño
6. [ ] Los datos son exportables y analizables externamente
7. [ ] La escritura no bloquea el flujo principal
