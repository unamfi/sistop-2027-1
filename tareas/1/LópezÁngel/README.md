# Ejercicio de sincronización: Alumnos y asesor

Autor: López Vizcarra Ángel David

---

## Problema que se decidió resolver
Elegí resolver el problema de “Los alumnos y el asesor”. Consiste en modelar el horario de atención de un profesor dentro de su cubículo, el cual tiene un cupo máximo de `X` sillas. Si no hay nadie que atender, el profesor usa las sillas c para dormir. Los alumnos llegan en cualquier momento con un número variable de dudas ,entre 1 y `Y`; si encuentran silla disponible entran, y solo un alumno a la vez puede plantear su pregunta y esperar respuesta mientras los demás esperan su turno sentados, alternándose entre pregunta y pregunta para que la espera sea corta para todos.

## Lenguaje y entorno
El programa está hecho en Python 3 utilizando los módulos estándar `threading`, `time` y `random`.

## Ejecución
Desde la terminal:

```bash
python3 asesor.py
```

## Estrategia de sincronización
Concentré el estado compartido dentro de la clase `CubiculoAsesor` y sincronicé los hilos del profesor y de los alumnos combinando dos candados y dos semáforos inicializados en cero:
* `mutex_puerta` :Protege la variable `alumnos_adentro` cada vez que alguien toca la puerta para ver si hay cupo o cuando sale del cubículo.
* `turno_pregunta` : Garantiza que solo un alumno sentado pueda hablar con el profesor a la vez.
* `despertar_profesor` :Mantiene al hilo del profesor durmiendo hasta que un alumno en turno le indica que tiene una pregunta lista.
* `respuesta_lista` :Bloquea al alumno que acaba de preguntar hasta que el profesor termina de explicarle la respuesta.

## Cómo funciona el programa
El programa inicia el hilo del profesor y lanza los hilos de los `NUM_ALUMNOS` con una cantidad aleatoria de preguntas. Cada alumno llega tras una pausa aleatoria y toca la puerta revisando con `mutex_puerta` si hay lugar; si el cubículo está lleno (`X_SILLAS`), espera afuera un momento antes de volver a intentar. Una vez sentado adentro, entra a un ciclo `for` por cada una de sus dudas: adquiere `turno_pregunta`, despierta al profesor con `release()`, espera la explicación con `acquire()` y luego suelta el candado del turno haciendo una breve pausa para anotar en su cuaderno. Cuando todos los hilos de los alumnos terminan (`join()`), el programa cambia la bandera `horario_activo` a `False` y despierta una última vez al profesor para cerrar el programa limpiamente.

## Detalles de sincronización
Para lograr que la espera fuera corta y nadie acaparara al profesor, coloqué el candado `turno_pregunta` dentro del ciclo de preguntas de cada estudiante y no afuera. Así, cada vez que el profesor termina de responder una duda individual y el alumno libera `turno_pregunta`, provocando un cambio de contexto para que otro compañero sentado tome el turno antes de que el mismo alumno haga su siguiente pregunta. También cuidé que la lectura de `alumnos_adentro == 0` siempre estuviera dentro de `mutex_puerta` para que el profesor sepa exactamente cuándo el cubículo quedó vacío y pueda volver a dormir.

## Resultados
El profesor inicia dormido en el sillon porque no hay alumnos, posteriormente despierta y empieza a atender a los alumnos entran, y el siguiente toca la puerta. Posteriormente se observa como responde la pregunta mientras los alumnos que llegaron antes siguen el proceso de espera. Al final, cuando el profesor responde a todos los alumnos, duerme.

## Problemas que tuve
Un detalle importante fue lograr que el hilo del profesor terminara correctamente cuando ya habían pasado todos los alumnos, ya que al principio se quedaba bloqueado para siempre esperando en `despertar_profesor.acquire()`. Lo resolví agregando la bandera `horario_activo` junto con un `release()` final en `main()` después del `join()` de los alumnos, para que el profesor despertara, viera que ya había terminado el horario sin alumnos adentro y saliera del ciclo `while`.