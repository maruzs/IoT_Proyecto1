# Justificaciones para decisiones tecnicas tomadas

## Eleccion del modelo de prediccion - Linear Regression
En este caso el uso de LR es seleccionada por sobre otros modelos predictivos debido a la simplicidad y eficiencia que ofrecen, ya que al estar corriendo junto al LLM es importante reducir el uso de recursos. Ademas de que para ventanas cortas (60 minutos) los modelos complejos como Neural Networks o Prophet tienden a fallar por la baja cantidad de datos para entrenar y pueden generar Overfitting o dar proyecciones absurdas, los polinomios de grados superiores pueden oscilar excesivamente ante una fluctuacion momentanea del sensor.

