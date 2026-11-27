# Tarea 1: Ejercicios de sincronización

**Alumno:** Arturo Gutiérrez Gutiérrez

## Problema elegido

**Los alumnos y el asesor.** Un profesor tiene *x* sillas en su cubículo y, si no
hay alumnos, se duerme la siesta. Pueden entrar a lo más *x* alumnos, sólo uno
puede presentar su duda a la vez y cada alumno hace entre 1 y *y* preguntas,
dejando que los demás pregunten entre una y otra.

## Lenguaje y entorno

- Python 3 (sólo usa la biblioteca estándar: `threading`, `random`, `time`).
- Lo desarrollé y probé en Windows con Git Bash.

### ¿Cómo ejecutarlo?

Sólo se necesita tener Python 3 instalado:

```
python asesor.py
```

Los valores (6 alumnos, 3 sillas, hasta 3 preguntas) están al inicio del
archivo y se pueden cambiar ahí.

## Estrategia de sincronización

El profesor es un hilo y cada alumno es otro hilo. Usé cuatro semáforos:

| Semáforo | Patrón | Para qué sirve |
|---|---|---|
| `sillas = Semaphore(x)` | Multiplex | Que no haya más de *x* alumnos dentro. Si está lleno, el alumno se queda esperando afuera. |
| `turno = Lock()` | Mutex | Que sólo un alumno presente su duda a la vez. |
| `pregunta = Semaphore(0)` | Señalización | El alumno despierta al profesor. Si nadie pregunta, el profesor se queda bloqueado ahí (dormido). |
| `respuesta = Semaphore(0)` | Señalización (rendezvous con `pregunta`) | El alumno espera a que el profesor termine de responder. |

Después de cada pregunta el alumno suelta el `turno` y espera un momento, para
que otro alumno pueda preguntar entre una y otra.

## Refinamientos

No implementé refinamientos; es la solución base.

## Dudas / cosas que podrían mejorar

- El `Lock` de Python no garantiza orden de llegada, así que en teoría un alumno
  podría tardar más en obtener su turno que otro. Se podría mejorar usando una
  cola para que pregunten en orden.
- La salida es sencilla (sólo mensajes en texto).
