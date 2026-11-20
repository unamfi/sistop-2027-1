from dataclasses import dataclass, field
from pathlib import Path
import queue
import sys
import threading
import time

from fiunamfs import ErrorFiUnamFS, SistemaFiUnamFS
from interfaz import iniciar


@dataclass
class Solicitud:
    """Operación enviada por la interfaz al hilo que accede al disco."""
    operacion: str
    argumentos: tuple
    terminada: threading.Event = field(default_factory=threading.Event)
    resultado: object = None
    error: Exception | None = None


def atender_solicitudes(sistema, cola_solicitudes):
    """Consume y ejecuta solicitudes de FiUnamFS en el hilo trabajador."""
    while True:
        solicitud = cola_solicitudes.get()
        try:
            if solicitud is None:
                print("[hilo-disco] Cerrando el trabajador.")
                return

            try:
                print(
                    f"[{threading.current_thread().name}] "
                    f"Ejecutando {solicitud.operacion}."
                )
                time.sleep(1)  # Pausa didáctica para distinguir el trabajo del hilo.
                metodo = getattr(sistema, solicitud.operacion)
                solicitud.resultado = metodo(*solicitud.argumentos)
            except Exception as error:
                solicitud.error = error
            finally:
                print(
                    f"[{threading.current_thread().name}] "
                    "Operación terminada; notificando al menú."
                )
                solicitud.terminada.set()
        finally:
            cola_solicitudes.task_done()


def crear_solicitante(cola_solicitudes):
    """Crea la función que la interfaz usa para pedir operaciones al hilo."""
    def solicitar(operacion, *argumentos):
        solicitud = Solicitud(operacion, argumentos)
        cola_solicitudes.put(solicitud)
        print(
            f"[{threading.current_thread().name}] "
            f"Solicitud enviada: {operacion}."
        )

        # Event espera hasta que el hilo trabajador publique el resultado.
        solicitud.terminada.wait()
        print(
            f"[{threading.current_thread().name}] "
            "Respuesta recibida."
        )

        if solicitud.error is not None:
            raise solicitud.error

        return solicitud.resultado

    return solicitar


def main():
    if len(sys.argv) > 1:
        ruta_imagen = Path(sys.argv[1]).resolve()
    else:
        ruta_imagen = Path(__file__).resolve().parent.parent / "fiunamfs.img"

    try:
        sistema = SistemaFiUnamFS(ruta_imagen)
    except (ErrorFiUnamFS, OSError) as error:
        print("Error:", error)
        return

    cola_solicitudes = queue.Queue()
    hilo_disco = threading.Thread(
        target=atender_solicitudes,
        args=(sistema, cola_solicitudes),
        name="hilo-disco",
    )
    hilo_disco.start()

    try:
        iniciar(crear_solicitante(cola_solicitudes))
    finally:
        # None funciona como señal para que el trabajador termine.
        cola_solicitudes.put(None)
        cola_solicitudes.join()
        hilo_disco.join()


if __name__ == "__main__":
    main()
