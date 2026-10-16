#!/usr/bin/env python3
"""
El problema de Santa Claus — Sistemas Operativos 2027-1
Johan Cipriano Amador

Santa duerme en su taller del Polo Norte. Lo despiertan sólo:
  * los 9 renos, cuando regresan todos de vacaciones (¡hay que repartir!), o
  * un grupo de exactamente 3 elfos que necesitan ayuda.
Si llegan ambos al mismo tiempo, los renos tienen prioridad.

Sincronización: semáforos de threading (ver README.md).
"""

import random
import sys
import threading
import time

# ─── Parámetros de la simulación ──────────────────────────────────────────
NUM_RENOS = 9
NUM_ELFOS = 10
ELFOS_POR_GRUPO = 3
NAVIDADES = 3            # cuántos repartos hace Santa antes de terminar

# ─── Estética: colores ANSI (funcionan en Git Bash / mintty y Linux) ──────
RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
ROJO, VERDE, AMARILLO, AZUL, CYAN = (
    "\033[91m", "\033[92m", "\033[93m", "\033[94m", "\033[96m")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# ─── Estado compartido (protegido por `mutex`) ────────────────────────────
renos_esperando = 0
elfos_esperando = 0

mutex = threading.Semaphore(1)              # protege los contadores
santa_sem = threading.Semaphore(0)          # despierta a Santa (señalización)
reno_sem = threading.Semaphore(0)           # renos esperan a ser enganchados
elfo_sem = threading.Semaphore(0)           # elfos esperan a ser atendidos
torniquete_elfos = threading.Semaphore(ELFOS_POR_GRUPO)  # máx. 3 elfos en fila
renos_listos = threading.Semaphore(0)       # barrera: los 9 ya enganchados
elfos_atendidos = threading.Semaphore(0)    # los 3 elfos ya recibieron ayuda
pantalla = threading.Lock()                 # para que no se mezclen líneas

inicio = time.monotonic()


def barra(n, total, color):
    return color + "■" * n + DIM + "□" * (total - n) + RESET


def log(quien, color, msg):
    """Imprime una línea con marca de tiempo y el estado de las filas."""
    t = time.monotonic() - inicio
    estado = (f"🦌 {barra(renos_esperando, NUM_RENOS, AMARILLO)} "
              f"🧝 {barra(elfos_esperando, ELFOS_POR_GRUPO, VERDE)}")
    with pantalla:
        print(f"{DIM}{t:6.2f}s{RESET} │ {estado} │ "
              f"{color}{BOLD}{quien:<9}{RESET} {msg}", flush=True)


# ─── Actores ──────────────────────────────────────────────────────────────
def santa():
    global renos_esperando, elfos_esperando
    navidad = 0
    log("Santa", ROJO, "💤 Se va a dormir...")
    while navidad < NAVIDADES:
        santa_sem.acquire()          # duerme hasta que alguien lo despierte
        mutex.acquire()
        if renos_esperando == NUM_RENOS:          # prioridad a los renos
            navidad += 1
            log("Santa", ROJO,
                f"🎅 ¡Jo, jo, jo! Llegaron los renos. Navidad #{navidad}")
            renos_esperando = 0
            mutex.release()
            for _ in range(NUM_RENOS):
                reno_sem.release()   # deja pasar a los 9 renos
            for _ in range(NUM_RENOS):
                renos_listos.acquire()  # barrera: espera a los 9 enganchados
            log("Santa", ROJO, f"{BOLD}🛷 ¡A volar! Repartiendo regalos...{RESET}")
            time.sleep(1.5)
            log("Santa", ROJO, "🏠 Regresó del reparto")
        elif elfos_esperando == ELFOS_POR_GRUPO:
            mutex.release()
            log("Santa", ROJO, "😩 Lo despertaron tres elfos. Va a ayudarles")
            for _ in range(ELFOS_POR_GRUPO):
                elfo_sem.release()
            for _ in range(ELFOS_POR_GRUPO):
                elfos_atendidos.acquire()
        else:
            mutex.release()          # (no debería ocurrir; despertar espurio)
        log("Santa", ROJO, "💤 Vuelve a dormir")
    log("Santa", ROJO, f"{BOLD}🎄 Fin de la temporada. ¡Feliz Navidad!{RESET}")


def reno(i):
    global renos_esperando
    nombre = f"Reno {i}"
    while True:
        time.sleep(random.uniform(3, 7))          # vacaciones en el trópico
        mutex.acquire()
        renos_esperando += 1
        log(nombre, AMARILLO, "🏝️  Regresó de vacaciones")
        if renos_esperando == NUM_RENOS:
            log(nombre, AMARILLO, "🔔 Soy el último: ¡despierto a Santa!")
            santa_sem.release()
        mutex.release()
        reno_sem.acquire()                        # espera a ser enganchado
        log(nombre, AMARILLO, "🪢 Enganchado al trineo")
        renos_listos.release()


def elfo(i):
    global elfos_esperando
    nombre = f"Elfo {i}"
    while True:
        time.sleep(random.uniform(1, 6))          # fabricando juguetes
        torniquete_elfos.acquire()                # sólo 3 pueden formarse
        mutex.acquire()
        elfos_esperando += 1
        log(nombre, VERDE, "🔧 Tiene un problema, se forma")
        if elfos_esperando == ELFOS_POR_GRUPO:
            log(nombre, VERDE, "🔔 Ya somos tres: ¡despierto a Santa!")
            santa_sem.release()
        mutex.release()

        elfo_sem.acquire()                        # espera la ayuda de Santa
        log(nombre, CYAN, "💡 Recibió ayuda de Santa")
        time.sleep(0.2)

        mutex.acquire()
        elfos_esperando -= 1
        if elfos_esperando == 0:                  # el último abre paso
            for _ in range(ELFOS_POR_GRUPO):
                torniquete_elfos.release()
        mutex.release()
        elfos_atendidos.release()


def main():
    print(f"\n{BOLD}{ROJO}🎅  El problema de Santa Claus  🎄{RESET}  "
          f"{DIM}({NUM_RENOS} renos, {NUM_ELFOS} elfos, "
          f"{NAVIDADES} navidades){RESET}\n")
    for i in range(1, NUM_RENOS + 1):
        threading.Thread(target=reno, args=(i,), daemon=True).start()
    for i in range(1, NUM_ELFOS + 1):
        threading.Thread(target=elfo, args=(i,), daemon=True).start()
    hilo_santa = threading.Thread(target=santa)
    hilo_santa.start()
    hilo_santa.join()
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{DIM}Interrumpido por el usuario.{RESET}")
