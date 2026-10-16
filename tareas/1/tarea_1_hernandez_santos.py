'''
Tarea 1: Ejercicios de sincronización
Ejercicio seleccionado: Ejercicio 5 -> El servidor web

El problema central consiste en manejar la llegada continua y asíncrona de conexiones de red 
y distribuirlas de manera eficiente entre un grupo de k hilos que se encargarán de "procesarlos".

Hecho por: Hernández Andrade Miguel Ángel, Santos Cruz Lair Abraham
Sistemas Operativos -> Grupo 7 -> Prof. Gunnar Eyal Wolf Iszaevich 
'''

import threading
import random
import time
from collections import deque

# Definición de variables globales
num_trabajadores = 5   
peticiones = threading.Semaphore(0) # Semáforo para controlar el número de solicitudes pendientes
mutex = threading.Semaphore(1) # Semáforo para proteger el acceso a la cinta
cinta = deque()

# Función para mostrar un mensaje con el rol e ID del trabajador
def msg(rol, id_num, mensaje):
    print(f"[{rol} {id_num}] {mensaje}")

# Función del jefe: Genera solicitudes de procesamiento de páginas web y las coloca en la cinta
def jefe():
    contador = 1
    while True:
        time.sleep(random.random()*2) # Randomiza el tiempo de espera entre solicitudes
        pagina = f"pagina_web_{contador}.html"
        msg("Jefe", "Unico", f"Recibí conexión de red. Precesando {pagina}...")
        
        # Agregamos la solicitud a la cinta
        with mutex:
            cinta.append(pagina) 
        
        peticiones.release()
        contador +=1 # Se incrementa el contador de solicitudes

# Función del trabajador: Procesa las solicitudes de la cinta
def trabajador(id_trabajador):
    tareas_completadas = 0
    tiempo_total = 0

    while True:
        peticiones.acquire()

        # Obtenemos la tarea de la cinta
        with mutex: 
            tarea = cinta.popleft()
        msg("Trabajador", id_trabajador, f"Despertado. Atendiendo solicitud: {tarea}")

        tiempo_procesamiento= random.random()*3 # Randomiza el tiempo de procesamiento de la solicitud
        time.sleep(tiempo_procesamiento) # Simula el tiempo de procesamiento de la solicitud

        # Se actualizan las estadísticas del trabajador
        tareas_completadas += 1
        tiempo_total += tiempo_procesamiento

        msg("Trabajador", id_trabajador, f"Finalicé solicitud: {tarea}. Tiempo de procesamiento: {tiempo_procesamiento:.2f}s. Total tareas completadas: {tareas_completadas}.")

# Ejecución del programa
if __name__ == "__main__":
    print("[Sistema] Iniciando servidores y trabajadores...")

    # Iniciamos un único hilo del jefe
    j = threading.Thread(target=jefe)
    j.start()

    # Iteraciones de creación de los hilos de los k trabajadores
    for i in range(num_trabajadores):

        # Iniciamos un hilo para cada trabajador
        t = threading.Thread(target=trabajador, args=(i+1,))
        t.start()

    
