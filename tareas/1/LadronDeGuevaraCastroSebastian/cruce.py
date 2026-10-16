#!/usr/bin/env python3
"""
Intersección de caminos, tarea 1 de Sistemas Operativos (sistop-2027-1)
Sebastián Ladrón de Guevara Castro

Cada auto es un hilo. La intersección se divide en cuatro cuadrantes y cada
uno tiene su propio semáforo, así que dos autos nunca ocupan el mismo
cuadrante.

Se bloquea solo el cuadrante que se ocupa y no la intersección completa.
Los autos pueden girar a la derecha (un cuadrante), seguir de frente (dos)
o girar a la izquierda (tres).

Un multiplex deja entrar a lo más 3 autos a la vez para evitar bloqueos
mutuos. Además, todos los semáforos atienden en orden de llegada para
evitar la inanición.

Ejemplos de uso
      python3 cruce.py                                (se sale con Ctrl+C)
      python3 cruce.py --duracion 30
      python3 cruce.py --sin-interfaz --autos 2000    (prueba de estrés)
"""
import argparse
import random
import sys
import threading
import time
from collections import deque


# ─── Mecanismo de sincronización ────────────────────────────────────────────

class SemaforoJusto:
    """Semáforo contador que despierta a los hilos en orden de llegada.

    threading.Semaphore no garantiza el orden, por lo que un hilo recién
    llegado puede ganarle el permiso a otro que lleva más tiempo esperando.
    Aquí cada hilo que tiene que esperar se forma en una fila con su propio
    semáforo. Al hacer release() el permiso pasa directo al primero de la
    fila.
    """

    def __init__(self, valor=1):
        self._valor = valor
        self._mutex = threading.Lock()
        self._fila = deque()

    def acquire(self):
        with self._mutex:
            if self._valor > 0 and not self._fila:
                self._valor -= 1
                return
            mi_turno = threading.Semaphore(0)
            self._fila.append(mi_turno)
        mi_turno.acquire()

    def release(self):
        with self._mutex:
            if self._fila:
                self._fila.popleft().release()   # entrega directa del permiso
            else:
                self._valor += 1

    def __enter__(self):
        self.acquire()

    def __exit__(self, *_):
        self.release()


# ─── El modelo ──────────────────────────────────────────────────────────────
#
#  Cuadrantes (se circula por la derecha)       Orígenes
#
#         │ ↓  │    │                            N = viene del norte (baja)
#     ────┼────┼────┼────                        E = viene del este  (va al oeste)
#      ←  │ NO │ NE │  ←                         S = viene del sur   (sube)
#     ────┼────┼────┼────                        O = viene del oeste (va al este)
#      →  │ SO │ SE │  →
#     ────┼────┼────┼────
#         │    │ ↑  │
#
# Un auto entra por el cuadrante que tiene el mismo índice que su origen y
# avanza en sentido antihorario (NO → SO → SE → NE → NO).

ORIGENES = ['N', 'E', 'S', 'O']
CUADRANTES = ['NO', 'NE', 'SE', 'SO']
MANIOBRAS = {'derecha': 1, 'frente': 2, 'izquierda': 3}   # cuadrantes usados


def ruta(origen, maniobra):
    """Lista de cuadrantes (índices) que recorre un auto."""
    entrada = ORIGENES.index(origen)
    return [(entrada - paso) % 4 for paso in range(MANIOBRAS[maniobra])]


class Cruce:
    def __init__(self, pausa):
        self.pausa = pausa                                   # seg. por cuadrante
        self.cuadrantes = [SemaforoJusto(1) for _ in CUADRANTES]
        self.multiplex = SemaforoJusto(3)                    # evita el deadlock
        self.carriles = {o: SemaforoJusto(1) for o in ORIGENES}   # sin rebase

        # Estado compartido que solo sirve para mostrar y verificar, no sincroniza nada
        self.estado = threading.Lock()
        self.ocupante = [None] * 4
        self.filas = {o: deque() for o in ORIGENES}
        self.cruzaron = {o: 0 for o in ORIGENES}
        self.dentro = 0
        self.max_dentro = 0
        self.choques = 0
        self.espera_max = 0.0
        self.bitacora = deque(maxlen=9)

    def anota(self, texto):
        with self.estado:
            self.bitacora.append(f'{time.strftime("%H:%M:%S")}  {texto}')

    def ocupa(self, q, auto):
        with self.estado:
            if self.ocupante[q] is not None:   # nunca debería pasar
                self.choques += 1
            self.ocupante[q] = auto

    def libera(self, q):
        with self.estado:
            self.ocupante[q] = None


class Auto(threading.Thread):
    def __init__(self, num, cruce, origen, maniobra):
        super().__init__(daemon=True)
        self.num, self.cruce = num, cruce
        self.origen, self.maniobra = origen, maniobra
        self.ruta = ruta(origen, maniobra)

    def run(self):
        c = self.cruce
        llegada = time.monotonic()
        with c.estado:
            c.filas[self.origen].append(self)

        c.carriles[self.origen].acquire()   # 1. esperar a ser el primero del carril
        c.multiplex.acquire()               # 2. a lo más 3 autos en el cruce

        primero = self.ruta[0]
        c.cuadrantes[primero].acquire()     # 3. entrar al primer cuadrante
        c.ocupa(primero, self)
        with c.estado:
            c.filas[self.origen].remove(self)
            c.dentro += 1
            c.max_dentro = max(c.max_dentro, c.dentro)
            c.espera_max = max(c.espera_max, time.monotonic() - llegada)
        c.carriles[self.origen].release()   #    ya puede acercarse el siguiente
        c.anota(f'#{self.num:<3} de {self.origen} entra a {CUADRANTES[primero]}'
                f' ({self.maniobra})')
        time.sleep(c.pausa)

        # 4. Primero se toma el siguiente cuadrante y después se suelta el que
        #    queda atrás.
        actual = primero
        for siguiente in self.ruta[1:]:
            c.cuadrantes[siguiente].acquire()
            c.ocupa(siguiente, self)
            c.libera(actual)
            c.cuadrantes[actual].release()
            actual = siguiente
            time.sleep(c.pausa)

        c.libera(actual)                     # 5. salir
        c.cuadrantes[actual].release()
        with c.estado:
            c.dentro -= 1
            c.cruzaron[self.origen] += 1
        c.multiplex.release()
        c.anota(f'#{self.num:<3} de {self.origen} sale de {CUADRANTES[actual]} ✔')


def trafico(cruce, total, intervalo, hilos):
    """Genera autos al azar desde cualquier dirección."""
    for num in range(1, total + 1 if total else sys.maxsize):
        auto = Auto(num, cruce, random.choice(ORIGENES),
                    random.choice(list(MANIOBRAS)))
        hilos.append(auto)
        auto.start()
        time.sleep(random.uniform(0, intervalo))


# ─── Interfaz en la terminal ────────────────────────────────────────────────

RESET, NEGRITA, TENUE = '\033[0m', '\033[1m', '\033[2m'
COLOR = {'N': '\033[41;97m', 'E': '\033[44;97m',      # fondo rojo / azul
         'S': '\033[42;30m', 'O': '\033[43;30m'}      # fondo verde / amarillo
FLECHA = {'derecha': '↱', 'frente': '↑', 'izquierda': '↰'}
ASFALTO, PASTO, RAYA = '\033[100m', '\033[32m', '\033[100;93m'

LADO = 15             # la cuadrícula es de LADO × LADO celdas (2 caracteres)
C = LADO // 2 - 1     # fila/columna donde empieza la intersección (2×2)
POS_CUADRANTE = [(C, C), (C, C + 1), (C + 1, C + 1), (C + 1, C)]


def celda_fila(origen, i):
    """Posición en pantalla del i-ésimo auto formado en un carril."""
    return {'N': (C - 1 - i, C), 'S': (C + 2 + i, C + 1),
            'E': (C, C + 2 + i), 'O': (C + 1, C - 1 - i)}[origen]


def pinta_auto(auto):
    return f'{COLOR[auto.origen]}{auto.origen}{FLECHA[auto.maniobra]}{RESET}'


def dibuja(cruce):
    with cruce.estado:
        mapa = {}
        for origen, fila in cruce.filas.items():
            for i, auto in enumerate(fila):
                pos = celda_fila(origen, i)
                if min(pos) >= 0 and max(pos) < LADO:
                    mapa[pos] = pinta_auto(auto)
        for q, auto in enumerate(cruce.ocupante):
            if auto:
                mapa[POS_CUADRANTE[q]] = pinta_auto(auto)
        espera = {o: len(f) for o, f in cruce.filas.items()}
        cruzaron, dentro = dict(cruce.cruzaron), cruce.dentro
        choques, bitacora = cruce.choques, list(cruce.bitacora)
        espera_max, max_dentro = cruce.espera_max, cruce.max_dentro

    lineas = []
    for r in range(LADO):
        renglon = ''
        for k in range(LADO):
            en_vertical, en_horizontal = k in (C, C + 1), r in (C, C + 1)
            if (r, k) in mapa:
                renglon += mapa[(r, k)]
            elif en_vertical and en_horizontal:
                renglon += f'{ASFALTO}  {RESET}'
            elif en_vertical:
                renglon += f'{RAYA}▕ {RESET}' if k == C + 1 else f'{ASFALTO}  {RESET}'
            elif en_horizontal:
                renglon += f'{RAYA}▁▁{RESET}' if r == C else f'{ASFALTO}  {RESET}'
            else:
                renglon += f'{PASTO}··{RESET}'
        lineas.append(renglon)

    total = sum(cruzaron.values())
    color_choques = '\033[92m' if choques == 0 else '\033[91m'
    panel = [
        f'{NEGRITA}INTERSECCIÓN DE CAMINOS{RESET}',
        f'{TENUE}4 cuadrantes · multiplex de 3 · filas FIFO{RESET}',
        '',
        f'  Autos en el cruce:   {dentro}  {TENUE}(máx. {max_dentro}){RESET}',
        f'  Ya cruzaron:         {total}',
        '  Esperando:  ' + '  '.join(
            f'{COLOR[o]} {o} {RESET} {espera[o]:<2}' for o in ORIGENES),
        '  Cruzaron:   ' + '  '.join(
            f'{COLOR[o]} {o} {RESET} {cruzaron[o]:<2}' for o in ORIGENES),
        f'  Espera más larga:    {espera_max:4.1f} s',
        f'  Choques:             {color_choques}{NEGRITA}{choques}{RESET}',
        '',
        f'  {TENUE}↱ derecha (1 cuadrante)  ↑ frente (2)  ↰ izquierda (3){RESET}',
        '',
    ] + [f'  {TENUE}{linea}{RESET}' for linea in bitacora]

    alto = max(len(lineas), len(panel))
    lineas += [' ' * (2 * LADO)] * (alto - len(lineas))
    panel += [''] * (alto - len(panel))
    salida = '\n'.join(f'{a}   {b}\033[K' for a, b in zip(lineas, panel))
    sys.stdout.write('\033[H' + salida + '\n\033[J')
    sys.stdout.flush()


def resumen(cruce, inicio):
    total = sum(cruce.cruzaron.values())
    print(f'\nCruzaron {total} autos en {time.monotonic() - inicio:.1f} s  '
          f'({", ".join(f"{o}: {n}" for o, n in cruce.cruzaron.items())})')
    print(f'Máximo de autos dentro a la vez: {cruce.max_dentro}   '
          f'Espera más larga: {cruce.espera_max:.2f} s   '
          f'Choques: {cruce.choques}')


def main():
    p = argparse.ArgumentParser(description='Intersección de caminos con semáforos')
    p.add_argument('--duracion', type=float, default=0,
                   help='segundos de simulación (0 = hasta Ctrl+C)')
    p.add_argument('--pausa', type=float, default=0.5,
                   help='segundos que tarda un auto en cruzar un cuadrante')
    p.add_argument('--intervalo', type=float, default=0.6,
                   help='tiempo máximo entre la llegada de dos autos')
    p.add_argument('--autos', type=int, default=0,
                   help='cuántos autos generar (0 = sin límite)')
    p.add_argument('--sin-interfaz', action='store_true',
                   help='no muestra la animación, solo el resumen final')
    args = p.parse_args()

    cruce = Cruce(args.pausa)
    hilos = []
    inicio = time.monotonic()
    threading.Thread(target=trafico, daemon=True,
                     args=(cruce, args.autos, args.intervalo, hilos)).start()

    if not args.sin_interfaz:
        sys.stdout.write('\033[?25l\033[2J')        # oculta cursor, limpia
    try:
        while not args.duracion or time.monotonic() - inicio < args.duracion:
            if args.autos and len(hilos) == args.autos and \
               not any(h.is_alive() for h in hilos):
                break                                # todos cruzaron
            if not args.sin_interfaz:
                dibuja(cruce)
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        if not args.sin_interfaz:
            dibuja(cruce)
            sys.stdout.write('\033[?25h')           # regresa el cursor
        resumen(cruce, inicio)


if __name__ == '__main__':
    main()
