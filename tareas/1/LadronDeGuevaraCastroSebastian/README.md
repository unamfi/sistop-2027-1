# Tarea 1. Ejercicios de sincronización

Ladrón de Guevara Castro Sebastián (`Sebastian82879`), entrega individual.

## Problema elegido

Elegí la intersección de caminos. Es un cruce sin señalamiento vial al que
pueden llegar autos desde los cuatro puntos cardinales en cualquier momento.
No puede haber dos autos en la misma sección del cruce a la vez, nadie puede
rebasar y ninguna dirección se debe quedar esperando indefinidamente.

## Lenguaje y entorno

Lo hice en Python 3 sobre macOS. Lo probé con Python 3.13, aunque debería
funcionar con cualquier versión a partir de la 3.8. Solo usa la biblioteca
estándar (`threading`, `collections` y `argparse`), por lo que no hace falta
instalar nada adicional. En Linux debería correr igual.

La interfaz usa colores ANSI y algunos caracteres Unicode, así que conviene
ejecutarlo en una terminal normal (Terminal.app, iTerm o cualquier terminal
de Linux) con una ventana de unos 110 × 30 caracteres para que se vea
completo.

### Cómo ejecutarlo

    $ python3 cruce.py                 # animación, se termina con Ctrl+C
    $ python3 cruce.py --duracion 30   # se detiene solo a los 30 segundos

También acepta algunas opciones.

| Opción | Qué hace |
|---|---|
| `--pausa 0.5` | segundos que tarda un auto en cruzar un cuadrante |
| `--intervalo 0.6` | tiempo máximo entre la llegada de dos autos (menos tiempo, más tráfico) |
| `--autos N` | genera N autos y termina cuando todos cruzaron |
| `--sin-interfaz` | no muestra la animación, solo el resumen final |

Para hacer una prueba de estrés con miles de autos y casi sin pausas se
puede usar

    $ python3 cruce.py --sin-interfaz --autos 3000 --pausa 0.0005 --intervalo 0.0003

### Qué se ve en pantalla

Del lado izquierdo aparece el cruce visto desde arriba. Cada auto es una
celda con el color de la dirección de la que viene (N rojo, E azul, S verde
y O amarillo) y una flecha que indica hacia dónde va, `↱` si gira a la
derecha, `↑` si sigue de frente y `↰` si gira a la izquierda. Los autos que
todavía no entran se van formando en su carril.

Del lado derecho hay un panel con los autos que están dentro del cruce, los
que esperan y los que ya pasaron por cada dirección, la espera más larga que
ha habido y el número de choques, que siempre debe quedarse en 0. Debajo se
muestran los últimos movimientos.

## Estrategia de sincronización

Usé semáforos de tres formas.

1. Cada uno de los cuatro cuadrantes del cruce (NO, NE, SE y SO) tiene un
   semáforo inicializado en 1 que funciona como mutex. Así no puede haber
   dos autos en el mismo cuadrante.
2. Cada carril tiene también un mutex, para que solo el primer auto de la
   fila pueda intentar entrar. Lo suelta en cuanto llega a su primer
   cuadrante y entonces se acerca el siguiente. De esta manera no hay
   rebase.
3. Un multiplex de 3 limita cuántos autos pueden estar dentro del cruce al
   mismo tiempo. Esto es lo que evita el bloqueo mutuo.

Cada auto avanza tomando primero el cuadrante al que va y soltando después
el que deja atrás, de modo que nunca queda con un pie fuera de la
intersección.

Aparte de los semáforos, el programa lleva un registro de quién ocupa cada
cuadrante y cuenta un choque si alguien entra a uno ocupado. Ese registro no
sincroniza nada, solo lo agregué para poder comprobar que los semáforos
hacen su trabajo.

### Por qué no hay bloqueo mutuo

Los autos recorren los cuadrantes siempre en el mismo sentido (NO, SO, SE,
NE y de vuelta a NO). Si llegan cuatro autos al mismo tiempo, uno por cada
dirección, cada uno puede tomar su cuadrante de entrada y quedarse esperando
el siguiente, que tiene otro auto. Es la misma situación que en la cena de
los filósofos.

Para que ese ciclo se cierre se necesitan cuatro autos con un cuadrante cada
uno. Como ningún auto se queda esperando mientras tiene más de un cuadrante,
con un máximo de tres autos adentro siempre queda un cuadrante libre y
alguno puede avanzar. Es la misma idea de `filosofos_multiplex.py` que vimos
en clase.

Lo comprobé cambiando el multiplex a 4. Con ese valor la prueba de estrés se
congela en pocos segundos, mientras que con 3 pasaron miles de autos en
varias corridas sin bloqueos y sin choques.

### Por qué no hay inanición

El `threading.Semaphore` de Python no garantiza el orden en que despierta a
los hilos. Cuando alguien hace `release()`, un hilo que acaba de llegar
puede quedarse con el permiso antes que otro que llevaba más tiempo
esperando. Con tráfico constante en un sentido eso podría dejar a un auto de
otra dirección esperando para siempre.

Para evitarlo escribí la clase `SemaforoJusto`. Cada hilo que tiene que
esperar se forma en una fila (`deque`) con su propio semáforo. Al hacer
`release()` el permiso se le pasa directamente al primero de la fila en
lugar de regresarlo al contador. De esta forma nadie se puede adelantar.
Todos los semáforos del programa son de este tipo, incluidos los de los
cuadrantes, los carriles y el multiplex. El primer auto de cada carril se
forma en la fila del multiplex y entra cuando le toca, aunque haya mucho
tráfico en otra dirección. En la prueba de estrés la espera más larga se
mantuvo acotada.

## Refinamientos

Implementé los dos refinamientos.

En el primero no se bloquea toda la intersección, solo el cuadrante que el
auto está ocupando. Los autos que no se estorban pueden cruzar al mismo
tiempo, por ejemplo dos que dan vuelta a la derecha o uno del norte y otro
del sur que siguen de frente. En el panel se puede ver que normalmente hay
hasta tres autos dentro a la vez.

En el segundo cada auto elige al azar si gira a la derecha (usa un
cuadrante), sigue de frente (usa dos) o gira a la izquierda (usa tres). La
función `ruta()` calcula los cuadrantes que recorre según su origen y su
maniobra. Los bloqueos mutuos se evitan como expliqué arriba.

## Dudas y posibles mejoras

El multiplex de 3 es algo conservador. A veces deja esperando a un cuarto
auto que podría entrar sin problema, por ejemplo cuando los cuatro van a
dar vuelta a la derecha y ninguno estorba a otro. Otra opción sería que cada
auto apartara todos sus cuadrantes en un orden fijo antes de entrar. Eso sí
dejaría pasar a esos cuatro autos, pero tiene la desventaja de reservar
cuadrantes antes de usarlos. No tengo claro cuál de las dos soluciones sería
más correcta.

En la realidad la vuelta a la izquierda cruza el tráfico que viene de
frente. Aquí lo modelé solo como ocupar tres cuadrantes seguidos, sin darle
preferencia a nadie.

El estado que se muestra en pantalla está protegido con un `Lock` aparte.
Ese `Lock` no forma parte de la solución, solo evita que la interfaz lea
datos que se están actualizando en ese momento.
