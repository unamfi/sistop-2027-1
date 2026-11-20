"""Un consumidor exclusivo del disco y colas de solicitudes y estados."""

from dataclasses import dataclass, field
from queue import Queue
from threading import Lock, Thread, current_thread
from typing import Callable


# Mensaje que el trabajador coloca en la cola de la solicitud para reportar avance, resultado o fallo.
@dataclass(frozen=True)
class Estado:
    nombre: str
    resultado: object = None
    error: Exception | None = None


# Petición encapsulada con su propia cola de estados para devolver la respuesta al hilo solicitante.
@dataclass
class Solicitud:
    funcion: Callable
    argumentos: tuple
    estados: Queue = field(default_factory=Queue)

    def esperar(self):
        """Consume los estados hasta recibir el resultado o el error; usar una vez."""
        # Se bloquea en Queue.get() (sin espera activa) hasta recibir 'terminado' o relanzar el error.
        while True:
            estado = self.estados.get()
            if estado.nombre == "error":
                raise estado.error
            if estado.nombre == "terminado":
                return estado.resultado


# Comunicación entre hilos: el principal envía solicitudes y espera respuestas;
# el trabajador realiza las operaciones del disco una por una.
class TrabajadorDisco:
    """Serializa operaciones enviadas por otros hilos sin espera activa.

    Todas las operaciones sobre una imagen deben pasar por esta misma instancia.
    Las colas sincronizan los datos; el lock protege envío y cierre simultáneos.
    """

    def __init__(self):
        # Inicializa la cola FIFO de solicitudes, el candado de cierre y el único hilo consumidor del disco.
        self._solicitudes = Queue()
        self._cierre = Lock()
        self._cerrado = False
        self.hilo = Thread(target=self._trabajar, name="FiUnamFS-disco", daemon=False)
        self.hilo.start()

    def enviar(self, funcion: Callable, *argumentos) -> Solicitud:
        solicitud = Solicitud(funcion, argumentos)
        # El candado impide aceptar nuevas solicitudes mientras se ejecuta el cierre del trabajador.
        with self._cierre:
            if self._cerrado:
                raise RuntimeError("El trabajador del disco está cerrado.")
            self._solicitudes.put(solicitud)
        return solicitud

    def ejecutar(self, funcion: Callable, *argumentos):
        # Evita un interbloqueo (deadlock) si el propio hilo trabajador intentara esperarse a sí mismo.
        if current_thread() is self.hilo:
            raise RuntimeError("El trabajador no puede esperar una tarea de sí mismo.")
        return self.enviar(funcion, *argumentos).esperar()

    def _trabajar(self):
        # Bucle consumidor: procesa solicitudes de la cola, garantizando
        # exclusión mutua sobre la imagen y reportando inicio
        while True:
            solicitud = self._solicitudes.get()
            try:
                if solicitud is None:
                    return
                solicitud.estados.put(Estado("iniciado"))
                try:
                    resultado = solicitud.funcion(*solicitud.argumentos)
                except Exception as exc:
                    # Un error de una operación ,  impide procesar las siguientes solicitudes.
                    solicitud.estados.put(Estado("error", error=exc))
                else:
                    solicitud.estados.put(Estado("terminado", resultado=resultado))
            finally:
                self._solicitudes.task_done()

    def cerrar(self):
        if current_thread() is self.hilo:
            raise RuntimeError("El trabajador no puede esperar su propia terminación.")
        # inserta el centinela None al final de la cola y espera con join
        # a que terminen todas las operaciones previamente aceptadas.
        with self._cierre:
            if not self._cerrado:
                self._cerrado = True
                self._solicitudes.put(None)
        self.hilo.join()

    def __enter__(self):
        return self

    def __exit__(self, tipo, valor, traceback):
        self.cerrar()
