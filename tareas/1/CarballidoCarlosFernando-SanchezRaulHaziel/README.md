# Tarea 1: Ejercicios de sincronización
## Problema del elevador

Sistemas Operativos, grupo 7, semestre 2027-1

Profesor: Gunnar Eyal Wolf Iszaevich
Entrega: 15 de octubre de 2026
Integrantes:

- Carlos Fernando Carballido Carrillo, 320310186
- Raúl Haziel Sánchez Soperanes, 321026303

## Problema y ejecución
Simulamos un elevador para cinco pisos (0 a 4), con capacidad de cinco pasajeros y 15 personas representadas por hilos. Cada persona elige un origen y un destino diferentes al azar. Puede abordar aunque el elevador viaje en sentido contrario a su destino, si hay espacio.

Desarrollamos el programa en Java con Visual Studio Code en macOS. Se necesita un JDK con java y javac disponibles. No usa bibliotecas externas.

Desde esta carpeta:

    javac EjercicioElevador.java
    java EjercicioElevador

Los mensajes aparecen en la terminal y la ejecución termina con:
Todos llegaron. El elevador se detiene.

## Sincronización
Un semáforo mutex protege las modificaciones de los contadores compartidos. Hay un semáforo de ascenso y otro de descenso por piso. Los pasajeros se bloquean hasta recibir permiso. Dos semáforos de aviso confirman al elevador que terminaron los ascensos y descensos autorizados antes de continuar. Las esperas de confirmación ocurren sin mantener el mutex. Thread.sleep simula tiempos; la sincronización se realiza con semáforos.

## Refinamiento y límites
Consideramos la prevención de inanición con un recorrido por todos los pisos y semáforos justos por piso. La política justa ordena las adquisiciones en el semáforo, no las llegadas globales ni la atención entre pisos. No se asegura que una persona aborde en una sola vuelta. La simulación contiene 15 viajes finitos; no demuestra ausencia de inanición ante solicitudes ilimitadas.

## Dudas y posibles mejoras
El elevador sigue recorriendo el edificio mientras haya personas pendientes, incluso si momentáneamente está vacío. Los catch vacíos no resuelven una interrupción: podría faltar una confirmación y quedar un hilo esperando. Podrían agregarse espera por nuevas solicitudes, cancelación coordinada, semilla configurable, ocupación visible y una política de justicia entre pisos para demanda continua. Queda abierta la posibilidad de usar una señal explícita para indicar la terminación.

## Archivos de la entrega

- `EjercicioElevador.java`: programa completo para compilar y ejecutar.
- `README.md`: descripción del problema, requisitos, ejecución, sincronización, refinamiento y posibles mejoras.
- Reporte en PDF: portada, explicación por segmentos, capturas de ejecución y código completo como anexo.

Para ejecutar la simulación basta con el archivo Java. El README y el PDF documentan la solución.
