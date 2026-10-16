import random
import threading
import time

K_GATOS = 3
L_RATONES = 5
M_PLATOS = 2
RONDAS = 3

class cambio:
    def __init__(self):
        self.contador = 0
        self.mutex = threading.Lock()

    def lock(self, recurso: threading.Semaphore):
        with self.mutex:
            self.contador += 1
            if self.contador == 1:
                recurso.acquire()

    def unlock(self, recurso: threading.Semaphore):
        with self.mutex:
            self.contador -= 1
            if self.contador == 0:
                recurso.release()

cuarto = threading.Semaphore(1)
torniquete = threading.Semaphore(1)
cambio_gatos = cambio()
cambio_ratones = cambio()

platos = threading.Semaphore(M_PLATOS)
mutex_platos = threading.Lock()
platos_libres = list(range(M_PLATOS))

print_lock = threading.Lock()

def log(msg: str):
    with print_lock:
        print(msg, flush=True)

def comer(nombre: str, tipo: str):
    platos.acquire()
    with mutex_platos:
        plato = platos_libres.pop()
    log(f"{tipo} {nombre} come en el plato {plato}")
    time.sleep(random.uniform(0.1, 0.4))
    log(f"{tipo} {nombre} termina el plato {plato}")
    with mutex_platos:
        platos_libres.append(plato)
    platos.release()

def gato(i: int):
    for _ in range(RONDAS):
        time.sleep(random.uniform(0, 0.5))
        log(f"Gato {i} quiere comer")
        torniquete.acquire()
        cambio_gatos.lock(cuarto)
        torniquete.release()
        comer(str(i), "Gato")
        cambio_gatos.unlock(cuarto)

def raton(i: int):
    for _ in range(RONDAS):
        time.sleep(random.uniform(0, 0.5))
        log(f"Ratón {i} quiere comer")
        torniquete.acquire()
        cambio_ratones.lock(cuarto)
        torniquete.release()
        comer(str(i), "Ratón")
        cambio_ratones.unlock(cuarto)

if __name__ == "__main__":
    hilos = [threading.Thread(target=gato, args=(i,)) for i in range(K_GATOS)]
    hilos += [threading.Thread(target=raton, args=(i,)) for i in range(L_RATONES)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()