import queue
import threading

class Tarea:
    """Una operación pendiente, con su estado compartido entre los dos hilos."""

    def __init__(self, descripcion, funcion):
        self.descripcion = descripcion
        self._funcion = funcion
        self.terminada = threading.Event()   # se activa al finalizar 
        self.resultado = None
        self.error = None

    def ejecutar(self):
        """Corre la función guardando resultado o error; avisa al terminar."""
        try:
            self.resultado = self._funcion()
        except Exception as e:           # el error se relanza en el hilo de la UI
            self.error = e
        finally:
            self.terminada.set()

    def esperar(self):
        self.terminada.wait()
        if self.error is not None:
            raise self.error
        return self.resultado


class Trabajador(threading.Thread):
    """Hilo que ejecuta, una por una, las tareas que van llegando a su cola."""

    def __init__(self):
        super().__init__(name="trabajador-fiunamfs", daemon=True)
        self._cola = queue.Queue()

    def enviar(self, tarea):
        """Encola una tarea (lo llama el hilo de la interfaz)."""
        self._cola.put(tarea)
        return tarea

    def detener(self):
        """Pide al trabajador que termine tras acabar lo pendiente y espera."""
        self._cola.put(None)              # centinela de fin
        self.join()

    def run(self):
        while True:
            tarea = self._cola.get()      # bloquea hasta que haya trabajo
            if tarea is None:
                break
            tarea.ejecutar()