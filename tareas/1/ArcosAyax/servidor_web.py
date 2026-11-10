import threading
import time
import random
from collections import deque

NUM_TRABAJADORES = 4

paginas = [
    "/index.html",
    "/login.html",
    "/contacto.html",
    "/productos.html",
    "/ayuda.html",
    "/perfil.html",
    "/noticias.html",
    "/salir.html"
]

cola = deque()

mutex_cola = threading.Lock()
hay_trabajo = threading.Semaphore(0)

mutex_registro = threading.Lock()
registro = []


def trabajador(numero):
    while True:
        # Espera hasta que el jefe indique que hay trabajo
        hay_trabajo.acquire()

        with mutex_cola:
            solicitud = cola.popleft()

        # None indica que ya no quedan solicitudes
        if solicitud is None:
            break

        inicio = time.time()

        print(f"[Trabajador {numero}] Atiende {solicitud}")

        # Se simula el tiempo que tarda en atenderla
        time.sleep(random.uniform(0.5, 1.5))

        tiempo = time.time() - inicio

        with mutex_registro:
            registro.append((numero, solicitud, tiempo))

        print(
            f"[Trabajador {numero}] Termino {solicitud} "
            f"en {tiempo:.2f} segundos"
        )


trabajadores = []

for numero in range(1, NUM_TRABAJADORES + 1):
    hilo = threading.Thread(target=trabajador, args=(numero,))
    hilo.start()
    trabajadores.append(hilo)


print("\n   Servidor Web   \n")

for pagina in paginas:
    print(f"[Jefe] Llego una solicitud: {pagina}")

    with mutex_cola:
        cola.append(pagina)

    # Despierta a uno de los trabajadores
    hay_trabajo.release()

    time.sleep(random.uniform(0.2, 0.7))


# Señal de terminacion para cada trabajador
for _ in trabajadores:
    with mutex_cola:
        cola.append(None)

    hay_trabajo.release()


for hilo in trabajadores:
    hilo.join()


print("\n    Registro final    ")

for numero, pagina, tiempo in registro:
    print(
        f"Trabajador {numero}: {pagina} "
        f"({tiempo:.2f} segundos)"
    )

print("\nTodas las solicitudes fueron atendidas.")
