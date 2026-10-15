#!/usr/bin/python3
import threading
import time
import random

k = 3
num_conexiones = 10
paginas = ['/index.html', '/tareas.html', '/fotos.html', '/contacto.html']

conexiones = []
mutex = threading.Semaphore(1)
hay_conexion = threading.Semaphore(0)
reporte = []
mutex_reporte = threading.Semaphore(1)
hilos = []

def trabajador(num):
    print(f'    T{num}: Listo, me voy a dormir')
    hay_conexion.acquire()
    with mutex:
        pagina = conexiones.pop(0)
    if pagina is None:
        print(f'    T{num}: El servidor cierra, me voy')
        return
    print(f'    T{num}: Me despertaron, atiendo {pagina}')
    inicio = time.time()
    time.sleep(random.random())
    with mutex_reporte:
        reporte.append((num, pagina, time.time() - inicio))
    print(f'    T{num}: Terminé {pagina}')

def lanza_trabajador():
    hilo = threading.Thread(target=trabajador, args=[len(hilos)])
    hilos.append(hilo)
    hilo.start()

for i in range(k):
    lanza_trabajador()
for i in range(num_conexiones):
    time.sleep(random.random() / 2)
    pagina = random.choice(paginas)
    print(f'J: Llegó una conexión pidiendo {pagina}')
    with mutex:
        conexiones.append(pagina)
    hay_conexion.release()
    lanza_trabajador()
for i in range(k):
    with mutex:
        conexiones.append(None)
    hay_conexion.release()
for hilo in hilos:
    hilo.join()
print('\nReporte de los trabajadores:')
for num, pagina, tiempo in reporte:
    print(f'T{num}: {pagina} en {tiempo:.2f} s')
