import random
import threading
import time

NUM_RENOS = 9
NUM_ELFOS = 10
NAVIDADES = 3

mutex = threading.Semaphore(1)
santa_sem = threading.Semaphore(0)
renos_sem = threading.Semaphore(0)
reparto_sem = threading.Semaphore(0)
torniquete_elfos = threading.Semaphore(1)
ayuda_sem = threading.Semaphore(0)
listos_sem = threading.Semaphore(0)

renos = 0
elfos = 0

print_lock = threading.Lock()


def log(msg):
    with print_lock:
        print(msg, flush=True)


def santa():
    global renos
    navidad = 0
    while navidad < NAVIDADES:
        log("🎅💤 Santa se va a dormir")
        santa_sem.acquire()
        mutex.acquire()
        # los renos tienen prioridad sobre los elfos
        if renos == NUM_RENOS:
            navidad += 1
            log(f"🎅🛷 Santa: llegaron los renos, a repartir regalos (navidad {navidad})")
            renos = 0
            mutex.release()
            for _ in range(NUM_RENOS):
                renos_sem.release()
            time.sleep(1)
            log("🎅🎁 Santa: regalos entregados")
            for _ in range(NUM_RENOS):
                reparto_sem.release()
        elif elfos == 3:
            mutex.release()
            log("🎅🔧 Santa: ayudando a tres elfos")
            for _ in range(3):
                ayuda_sem.release()
            for _ in range(3):
                listos_sem.acquire()
        else:
            mutex.release()


def reno(i):
    global renos
    while True:
        time.sleep(random.uniform(1, 4))
        mutex.acquire()
        renos += 1
        log(f"🦌 Reno {i} regresa de vacaciones ({renos}/{NUM_RENOS})")
        if renos == NUM_RENOS:
            santa_sem.release()
        mutex.release()
        renos_sem.acquire()
        reparto_sem.acquire()


def elfo(i):
    global elfos
    while True:
        time.sleep(random.uniform(0.5, 3))
        torniquete_elfos.acquire()
        mutex.acquire()
        elfos += 1
        log(f"🧝 Elfo {i} tiene un problema ({elfos}/3)")
        # el tercero no suelta el torniquete hasta que el grupo termine
        if elfos == 3:
            santa_sem.release()
        else:
            torniquete_elfos.release()
        mutex.release()

        ayuda_sem.acquire()
        log(f"🧝✅ Elfo {i} recibe ayuda")

        mutex.acquire()
        elfos -= 1
        if elfos == 0:
            torniquete_elfos.release()
        mutex.release()
        listos_sem.release()


if __name__ == "__main__":
    for i in range(NUM_RENOS):
        threading.Thread(target=reno, args=(i,), daemon=True).start()
    for i in range(NUM_ELFOS):
        threading.Thread(target=elfo, args=(i,), daemon=True).start()
    santa()
    log("🎄 Fin")
