# Tarea de sincronización Cruce del río

Integrantes: Rodrigo Imanol Casas Pérez y Paris Samantha Malfavon Lemus.
Materia: Sistemas Operativos. Profesor: Gunnar Wolf. Semestre 2027-1.

## Problema elegido

Simulamos personas que llegan a una orilla y deben cruzar en una sola balsa. Cada persona es un hilo y pertenece a uno de dos grupos: hackers (H, desarrolladores de Linux) o serfs (S, desarrolladores de Microsoft). La balsa solo puede salir con cuatro personas. Las combinaciones permitidas son 4H, 4S o 2H y 2S. No se permiten grupos de tres de un tipo y uno del otro. El regreso de la balsa no se modela, de acuerdo con el enunciado.

## Lenguaje y entorno

El programa está escrito en Python 3 y utiliza únicamente módulos de la biblioteca estándar: threading, time, random, argparse y collections. Requiere Python 3.6 o posterior. No requiere instalar paquetes con pip. Se verificó con Python 3 en Linux.

Desde una terminal, entrar a la carpeta que contiene T1.py y ejecutar:

```bash
python3 T1.py
```

En Windows, si Python está instalado mediante su lanzador:

```powershell
py -3 T1.py
```

Por defecto se crean ocho hackers y ocho serfs. Para cambiar las cantidades y fijar el generador de llegadas:

```bash
python3 T1.py --hackers 6 --serfs 2 --semilla 42
python3 T1.py --hackers 4 --serfs 0
python3 T1.py --help
```

Cada cantidad debe ser un entero no negativo y par; el total debe ser positivo y múltiplo de cuatro. Estas restricciones permiten transportar a todos. Por ejemplo, tres hackers y un serf no pueden cruzar juntos y no hay más personas para completar otra combinación. El programa rechaza esos parámetros en lugar de quedar esperando indefinidamente.

La semilla fija el orden aleatorio de lanzamiento y las pausas, pero no garantiza una salida idéntica: el sistema operativo también decide el orden de ejecución de los hilos.

## Estrategia de sincronización

### Exclusión mutua

Un threading.Lock protege las colas, el número de viaje, la ocupación de la balsa y los pasajeros seleccionados y abordados. Solo un hilo puede modificar ese estado a la vez. Los permisos se esperan fuera del candado para que los demás hilos puedan continuar.

### Colas y semáforos personales

Cada grupo tiene una cola deque. Se seleccionan primero dos de cada grupo cuando esa combinación está disponible; de lo contrario, cuatro de un mismo grupo. Dentro de cada tipo se respeta el orden de entrada a la cola.

Cada persona tiene un threading.Semaphore inicialmente en cero. Una vez seleccionada para el viaje recibe un permiso mediante release y puede continuar desde acquire. El permiso personal evita que una llegada posterior consuma el permiso de otra persona seleccionada.

### Una sola balsa

El indicador balsa_ocupada se consulta y modifica bajo el candado. Se activa antes de liberar los permisos y permanece activo hasta que termina el cruce. Durante ese tiempo pueden llegar más personas y formarse en las colas, pero no puede autorizarse otro viaje.

### Barrera de cuatro pasajeros

Los cuatro pasajeros autorizados registran su abordaje y esperan en threading.Barrier(4). Al llegar el cuarto, la acción zarpar se ejecuta una sola vez. Se verifica la composición y se simula el viaje. Al llegar a la otra orilla se registra el grupo, se libera la balsa y se intenta formar el siguiente. La barrera es reutilizable; los hilos del siguiente grupo deben esperar a la siguiente generación.

### Impresiones y terminación

Otro Lock evita que se mezclen las impresiones. Esto conserva cada mensaje completo, pero no impone un orden idéntico de ejecución entre distintas corridas. Las pausas solo simulan llegadas y duración del viaje; no sustituyen la sincronización.

Los hilos no son daemon. El hilo principal usa join para esperar a todos y después verifica que cada persona haya cruzado exactamente una vez, que las colas estén vacías y que la balsa esté libre.

## Refinamientos y mejoras

La presentación no enumera refinamientos específicos para este problema. Entregamos la solución base y añadimos validación de parámetros, colas por tipo, semáforos personales, mensajes de seguimiento y comprobaciones internas con assert. No presentamos los diccionarios o la barrera como crédito adicional garantizado.

## Verificación

Se realizaron 90 simulaciones con diez semillas para cada distribución: 8H/8S, 4H/0S, 0H/4S, 2H/2S, 6H/2S, 2H/6S, 20H/20S, 0H/16S y 16H/0S. Para forzar llegadas concentradas se eliminaron las pausas en estas pruebas. Todas completaron el transporte; las comprobaciones verificaron cuatro pasajeros por viaje, composición válida, correspondencia entre seleccionados y abordados y ausencia de pasajeros repetidos o pendientes. Se rechazaron cinco entradas inválidas: 3H/1S, 1H/3S, 2H/0S, 0H/0S y -4H/8S.

Estas pruebas ayudan a detectar errores, pero no cubren todos los órdenes posibles de ejecución. Mantener assert habilitado permite conservar las comprobaciones; no ejecutar Python con la opción -O si se quieren utilizar.

## Limitaciones y dudas

La simulación usa una población finita con cantidades válidas. Dentro de cada tipo se atiende en orden FIFO, pero no hay un orden FIFO global entre tipos ni se demuestra equidad para llegadas infinitas. Un grupo espera hasta que exista una combinación legal. La llegada se registra cuando el hilo obtiene el candado, no necesariamente en el orden en que se crearon los hilos.

No se implementa cancelación interactiva coordinada ni recuperación de fallos internos de los hilos. En una aplicación más grande habría que propagar esos errores y cancelar las esperas de forma controlada. No se afirma que la salida por Ctrl+C sea una terminación limpia.

## Entrega

Esta carpeta contiene T1.py y este archivo de texto README.md. Colocarla dentro del directorio de la tarea correspondiente en el repositorio, conservando el nombre CasasRodrigo-MalfavonParis. La entrega se completa con un pull request al repositorio del profesor. El historial debe registrar avances reales; no se deben fabricar commits retroactivos para simular trabajo anterior.
