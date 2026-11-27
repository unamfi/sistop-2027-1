# Tarea 1 - Ejercicios de sincronización
# Problema: Los alumnos y el asesor
# Arturo Gutiérrez Gutiérrez

import threading
import random
import time

NUM_ALUMNOS = 6
SILLAS = 3          # x: sillas en el cubículo
MAX_PREGUNTAS = 3   # y: máximo de preguntas por alumno

sillas = threading.Semaphore(SILLAS)  # máximo x alumnos adentro
turno = threading.Lock()              # sólo un alumno pregunta a la vez
pregunta = threading.Semaphore(0)     # el alumno despierta al profe
respuesta = threading.Semaphore(0)    # el profe avisa que ya respondió


def profesor():
    while True:
        pregunta.acquire()   # si nadie pregunta, el profe se queda dormido aquí
        print("   Profe: responde la duda", flush=True)
        time.sleep(1)
        respuesta.release()


def alumno(n):
    time.sleep(random.uniform(0, 3))          # llega en algún momento
    print(f"Alumno {n} toca la puerta", flush=True)

    sillas.acquire()                          # espera si no hay silla libre
    print(f"Alumno {n} se sienta", flush=True)

    for k in range(random.randint(1, MAX_PREGUNTAS)):
        with turno:                           # espera su turno para preguntar
            print(f"Alumno {n} hace una pregunta", flush=True)
            pregunta.release()                # despierta al profe
            respuesta.acquire()               # espera la respuesta
        time.sleep(0.5)                       # deja que otros pregunten

    print(f"Alumno {n} se va", flush=True)
    sillas.release()                          # libera su silla


print("El profe se duerme la siesta...", flush=True)
threading.Thread(target=profesor, daemon=True).start()

alumnos = [threading.Thread(target=alumno, args=(i,)) for i in range(1, NUM_ALUMNOS + 1)]
for a in alumnos:
    a.start()
for a in alumnos:
    a.join()

print("Terminó la asesoría", flush=True)
