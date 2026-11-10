"""Cruce del rio. Rodrigo Imanol Casas Perez y Paris Samantha Malfavon Lemus.
Ejecutar: python3 T1.py --hackers 8 --serfs 8 --semilla 42
"""
import argparse
from collections import deque
import random
import threading
import time


class Persona:
    def __init__(self, numero, tipo):
        self.numero = numero
        self.tipo = tipo
        self.permiso = threading.Semaphore(0)


class CruceRio:
    def __init__(self, demora=0.08):
        self.mutex = threading.Lock()
        self.imprimir_mutex = threading.Lock()
        self.esperando = {"H": deque(), "S": deque()}
        self.balsa_ocupada = False
        self.viaje_num = 0
        self.grupo_actual = []
        self.abordados = []
        self.historial = []
        self.demora = demora
        self.barrera = threading.Barrier(4, action=self.zarpar)

    def imprimir(self, mensaje):
        with self.imprimir_mutex:
            print(mensaje, flush=True)

    def formar_grupo(self):
        """Llamar con self.mutex tomado. Solo admite un viaje a la vez."""
        if self.balsa_ocupada:
            return
        h = len(self.esperando["H"])
        s = len(self.esperando["S"])
        if h >= 2 and s >= 2:
            tipos = ["H", "H", "S", "S"]
        elif h >= 4:
            tipos = ["H"] * 4
        elif s >= 4:
            tipos = ["S"] * 4
        else:
            return

        self.grupo_actual = [self.esperando[t].popleft() for t in tipos]
        self.abordados = []
        self.balsa_ocupada = True
        self.viaje_num += 1
        for persona in self.grupo_actual:
            persona.permiso.release()

    def llegar(self, persona):
        with self.mutex:
            self.imprimir(f"[{persona.tipo} {persona.numero:02d}] llega a la orilla")
            self.esperando[persona.tipo].append(persona)
            self.formar_grupo()

        # Esperar sin retener el mutex que necesitan los demas.
        persona.permiso.acquire()
        with self.mutex:
            assert persona in self.grupo_actual
            assert persona not in self.abordados
            self.abordados.append(persona)
            self.imprimir(f"  -> {persona.tipo} {persona.numero:02d} aborda viaje {self.viaje_num}")
        self.barrera.wait()

    def zarpar(self):
        # La accion se ejecuta una sola vez por grupo, al llegar el cuarto hilo.
        with self.mutex:
            assert len(self.abordados) == 4
            assert set(self.abordados) == set(self.grupo_actual)
            hackers = sum(p.tipo == "H" for p in self.abordados)
            assert hackers in (0, 2, 4)
            numero = self.viaje_num
            grupo = tuple(self.abordados)
            self.imprimir(f"[ZARPE] Viaje {numero}: {hackers}H + {4 - hackers}S")

        # La balsa sigue ocupada durante todo el viaje.
        time.sleep(self.demora)

        with self.mutex:
            self.imprimir(f"[LLEGADA] Viaje {numero}: llegaron los cuatro pasajeros\n")
            self.historial.append(grupo)
            self.balsa_ocupada = False
            self.grupo_actual = []
            self.abordados = []
            self.formar_grupo()


def simular(hackers=8, serfs=8, semilla=None, demora=0.08, intervalo=0.02):
    # Estas cantidades garantizan una particion completa en grupos validos.
    if hackers < 0 or serfs < 0 or hackers + serfs == 0:
        raise ValueError("Las cantidades deben ser no negativas y sumar al menos 4.")
    if hackers % 2 or serfs % 2 or (hackers + serfs) % 4:
        raise ValueError("Cada cantidad debe ser par y el total multiplo de 4.")
    rng = random.Random(semilla)
    personas = [Persona(i + 1, t) for i, t in enumerate(["H"] * hackers + ["S"] * serfs)]
    rng.shuffle(personas)
    juego = CruceRio(demora)
    hilos = []
    for persona in personas:
        hilo = threading.Thread(target=juego.llegar, args=(persona,))
        hilos.append(hilo)
        hilo.start()
        time.sleep(rng.uniform(0, intervalo))
    for hilo in hilos:
        hilo.join()

    transportados = [p for grupo in juego.historial for p in grupo]
    assert len(transportados) == len(personas)
    assert len(set(transportados)) == len(personas)
    assert not juego.balsa_ocupada
    assert not any(juego.esperando.values())
    juego.imprimir(f"Fin: {len(transportados)} personas cruzaron en {juego.viaje_num} viajes.")
    return juego


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cruce del rio con hilos y sincronizacion")
    parser.add_argument("--hackers", type=int, default=8)
    parser.add_argument("--serfs", type=int, default=8)
    parser.add_argument("--semilla", type=int, default=None)
    args = parser.parse_args()
    try:
        simular(args.hackers, args.serfs, args.semilla)
    except ValueError as error:
        parser.error(str(error))
