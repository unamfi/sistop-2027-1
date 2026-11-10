# Peralta Rojas Jose Daniel
# Tarea 1 Sistemas Operativos

import threading
import time
import random

# Variables iniciales
k_trabajadores = 5
capacidad_max = 10

# Estructuras a usar
cola_solicitudes = []
estadisticas = {}

# Inicialización previa de diccionario
for i in range(num_trabajadores):
    estadisticas[i] = 0

# Semaforos mutex
mutex_cola = threading.Semaphore(1)
mutex_estadisticas = threading.Semaphore(1)

# semaforos de control
sem_elementos = threading.Semaphore(0)
sem_espacios = threading.Semaphore(capacidad_max)

def trabajador(id_trabajador):
    while True:
        # Intenta consumir elemneto
        sem_elementos.acquire()
        
        #  Extrae protegiendo con semaforo
        with mutex_cola:
            solicitud = cola_solicitudes.pop()
            
        sem_espacios.release()
        
        # Simular teimpo de trabajo
        tiempo_procesamiento = (random.random() * 0.4) + 0.1
        time.sleep(tiempo_procesamiento)
        
        # Trabaja con el diccionario de estadisticas de forma protejida
        with mutex_estadisticas:
            # El trabajador notifica informacion de su rendimiento (cuantas paginas ha trabajado)
            estadisticas[id_trabajador] += 1
            
        print(f"[Trabajador {id_trabajador}] Atendió {solicitud}. Total atendidas: {estadisticas[id_trabajador]}")

def jefe():
    contador_solicitudes = 0
    while True:
        # Simula tiempo de retraso
        time.sleep((random.random() * 0.15) + 0.05)
        contador_solicitudes += 1
        solicitud = f"Pagina_{contador_solicitudes}.html"
        
        sem_espacios.acquire()
        
        # Inserta de forma protejida
        with mutex_cola:
            cola_solicitudes.append(solicitud)
            print(f"[Jefe] Encoló {solicitud}")
            
        sem_elementos.release()

# Arranca los hilos
for i in range(k_trabajadores):
    threading.Thread(target=trabajador, args=[i]).start()

jefe()