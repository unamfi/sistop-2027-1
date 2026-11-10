"""Tarea 1: Santa Claus. Simulación concurrente con semáforos. Rivera Velazquez Brandon Kevin """
#python3 santa_claus.py --elfos 12 --escala 0.5

import argparse
from collections import deque
from dataclasses import dataclass, field
import random
import sys
import threading
import time


@dataclass
class Solicitud:
    """Cada elfo espera su propia respuesta, sin consultar estados en bucle."""

    elfo: int
    permiso: threading.Semaphore = field(
        default_factory=lambda: threading.Semaphore(0)
    )
    atendida: bool = False


class TallerSanta:
    def __init__(self, num_elfos=12, escala=1.0, semilla=42,
                 mostrar=True, color=True):
        if num_elfos < 0:
            raise ValueError("El número de elfos no puede ser negativo")
        if escala <= 0:
            raise ValueError("La escala debe ser mayor que cero")

        self.num_elfos = num_elfos
        self.escala = escala
        self.mostrar = mostrar
        self.color = color and sys.stdout.isatty()
        self.aleatorio = random.Random(semilla)

        # SINCRONIZACIÓN: los hilos no hacen espera activa (busy waiting).
        self.mutex = threading.Lock()                  # Protege datos compartidos
        self.despertar_santa = threading.Semaphore(0)  # Santa espera aquí
        self.fin_ayuda = threading.Semaphore(0)        # 3 elfos confirman atención
        self.iniciar = threading.Event()               # Inicio conjunto de hilos
        self.viaje = threading.Event()                 # Cancelación ordenada
        self.renos_listos = threading.Semaphore(0)     # 9 renos confirman abordaje
        self.permisos_renos = [threading.Semaphore(0) for _ in range(9)]
        self.impresion = threading.Lock()

        # Variables compartidas; siempre se modifican con mutex.
        self.cola_elfos = deque()
        self.renos_regresados = 0
        self.solicitudes = []
        self.grupos = []
        self.cancelados = []
        self.abordados = []
        self.comienzo = None

    def mensaje(self, tipo, detalle):
        if not self.mostrar:
            return
        paleta = {"SANTA": "\033[1;33m", "ELFO": "\033[36m",
                   "RENO": "\033[35m", "INFO": "\033[1;32m"}
        etiqueta = f"{tipo:<9}"
        if self.color:
            etiqueta = f"{paleta[tipo]}{etiqueta}\033[0m"
        with self.impresion:
            instante = time.monotonic() - self.comienzo if self.comienzo else 0.0
            print(f"[{instante:5.2f}s] {etiqueta} | {detalle}", flush=True)

    def elfo(self, identificador, retraso):
        self.iniciar.wait()

        if self.viaje.wait(retraso):
            return

        solicitud = Solicitud(identificador)
        with self.mutex:
            if self.viaje.is_set():
                return
            self.cola_elfos.append(solicitud)
            self.solicitudes.append(identificador)
            en_cola = len(self.cola_elfos)
            self.mensaje("ELFO", f"Elfo {identificador:02d} tiene una duda; "
                                 f"en espera: {en_cola}")
            if en_cola % 3 == 0:
                self.mensaje("ELFO", "Se juntaron otros 3 elfos: ¡despertar a Santa!")
                self.despertar_santa.release()

        # Bloqueo real: sólo Santa puede activar el permiso de este elfo.
        solicitud.permiso.acquire()
        if solicitud.atendida:
            self.mensaje("ELFO", f"Elfo {identificador:02d} recibió ayuda y vuelve al trabajo")
            self.fin_ayuda.release()  # Confirma que terminó este turno de atención.
        else:
            self.mensaje("ELFO", f"Elfo {identificador:02d} se retira: Santa ya va de viaje")

    def reno(self, identificador, retraso):
        self.iniciar.wait()
        time.sleep(retraso)  # Simulación de vacaciones, no espera de sincronización.
        with self.mutex:
            self.renos_regresados += 1
            cantidad = self.renos_regresados
            self.mensaje("RENO", f"Reno {identificador:02d} regresó ({cantidad}/9)")
            if cantidad == 9:
                self.despertar_santa.release()

        # Los renos no suben al trineo hasta recibir orden de Santa.
        self.permisos_renos[identificador - 1].acquire()
        with self.mutex:
            self.abordados.append(identificador)
            self.mensaje("RENO", f"Reno {identificador:02d} está listo en el trineo")
        self.renos_listos.release()

    def santa(self):
        self.iniciar.wait()
        while True:
            self.despertar_santa.acquire()  # Santa duerme sin consumir CPU.
            with self.mutex:
                # Refinamiento: los nueve renos tienen prioridad al decidir.
                if self.renos_regresados == 9:
                    self.viaje.set()
                    pendientes = list(self.cola_elfos)
                    self.cola_elfos.clear()
                    self.cancelados.extend(s.elfo for s in pendientes)
                    accion = "viajar"
                elif len(self.cola_elfos) >= 3:
                    grupo = [self.cola_elfos.popleft() for _ in range(3)]
                    for solicitud in grupo:
                        solicitud.atendida = True
                    accion = "ayudar"
                else:
                    # Una señal anterior puede quedar pendiente al preparar viaje.
                    continue

            if accion == "viajar":
                self.mensaje("SANTA", "¡Los 9 renos están aquí! El viaje tiene prioridad")
                for solicitud in pendientes:
                    solicitud.permiso.release()  # Desbloquea elfos no atendidos.
                for permiso in self.permisos_renos:
                    permiso.release()
                for _ in range(9):
                    self.renos_listos.acquire()  # Espera a todos los renos.
                self.mensaje("SANTA", "¡Trineo completo! Despegue hacia la Navidad")
                return

            ids = tuple(s.elfo for s in grupo)
            self.mensaje("SANTA", f"Ayudando al grupo de elfos {ids}")
            time.sleep(0.35 * self.escala)
            for solicitud in grupo:
                solicitud.permiso.release()
            for _ in range(3):
                self.fin_ayuda.acquire()  # Evita superponer grupos de ayuda.
            with self.mutex:
                self.grupos.append(ids)
            self.mensaje("SANTA", "Los tres elfos fueron atendidos. Volveré a dormir")

    def ejecutar(self):
        """Inicia todos los hilos, espera su salida y devuelve un resumen."""
        self.comienzo = time.monotonic()
        self.mensaje("INFO", "TALLER DEL POLO NORTE: simulación concurrente")
        self.mensaje("SANTA", "Santa está durmiendo...")

        hilos = [threading.Thread(target=self.santa, name="Santa")]
        for i in range(1, self.num_elfos + 1):
            retraso = self.aleatorio.uniform(0.25, 4.0) * self.escala
            hilos.append(threading.Thread(target=self.elfo,
                                          args=(i, retraso), name=f"Elfo-{i}"))
        for i in range(1, 10):
            retraso = self.aleatorio.uniform(4.0, 6.0) * self.escala
            hilos.append(threading.Thread(target=self.reno,
                                          args=(i, retraso), name=f"Reno-{i}"))

        for hilo in hilos:
            hilo.start()
        self.iniciar.set()  # Todos comienzan tras crearse los hilos.
        for hilo in hilos:
            hilo.join()     # No deja hilos bloqueados al finalizar.

        return {
            "grupos": list(self.grupos),
            "solicitudes": list(self.solicitudes),
            "cancelados": list(self.cancelados),
            "abordados": list(self.abordados),
            "viaje": self.viaje.is_set(),
        }


def main():
    parser = argparse.ArgumentParser(
        description="Simulación de Santa Claus con hilos, locks y semáforos")
    parser.add_argument("--elfos", type=int, default=12,
                        help="cantidad de elfos (por defecto: 12)")
    parser.add_argument("--escala", type=float, default=1.0,
                        help="multiplicador de tiempos; 0.2 es cinco veces más rápido")
    parser.add_argument("--semilla", type=int, default=42,
                        help="semilla para tiempos simulados (por defecto: 42)")
    parser.add_argument("--sin-color", action="store_true", help="desactivar colores ANSI")
    parser.add_argument("--silencio", action="store_true", help="ocultar eventos detallados")
    args = parser.parse_args()

    if args.elfos < 0 or args.escala <= 0:
        parser.error("--elfos debe ser >= 0 y --escala debe ser > 0")
    taller = TallerSanta(args.elfos, args.escala, args.semilla,
                        mostrar=not args.silencio, color=not args.sin_color)
    resultado = taller.ejecutar()
    print("\n" + "=" * 48)
    print("                RESUMEN DE LA SIMULACIÓN")
    print("=" * 48)
    print(f"  Elfos atendidos  : {len(resultado['grupos']) * 3}")
    print(f"  Grupos de 3      : {len(resultado['grupos'])}")
    print(f"  Dudas pendientes : {len(resultado['cancelados'])}")
    print(f"  Renos en trineo  : {len(resultado['abordados'])}/9")
    print(f"  Santa despegó    : {'Sí' if resultado['viaje'] else 'No'}")
    print("=" * 48)


if __name__ == "__main__":
    main()
