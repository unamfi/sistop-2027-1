
import threading
import queue


class AdministradorHilos:
    """Administra el hilo trabajador y el hilo supervisor."""

    def __init__(self, operaciones):

        self.operaciones = operaciones

        # Cola de solicitudes para el trabajador.
        self.cola = queue.Queue()

        # Cola de estados que procesa el supervisor.
        self.cola_estados = queue.Queue()

        # Cola de mensajes para mostrar desde el menu.
        self.cola_mensajes = queue.Queue()

        # Bloqueo para controlar el ciclo de vida de los hilos.
        self.lock = threading.Lock()

        self.iniciado = False
        self.finalizando = False
        self.finalizado = False

        # Hilo trabajador.
        self.hilo_trabajador = threading.Thread(
            target=self.procesar_solicitudes,
            name="Hilo-Trabajador"
        )

        # Hilo supervisor.
        self.hilo_supervisor = threading.Thread(
            target=self.supervisar,
            name="Hilo-Supervisor"
        )

    def iniciar(self):
        """Inicia los dos hilos."""

        with self.lock:

            if self.iniciado:
                raise RuntimeError(
                    "Los hilos ya fueron iniciados"
                )

            if self.finalizado:
                raise RuntimeError(
                    "No se pueden reiniciar los hilos finalizados"
                )

            self.hilo_trabajador.start()
            self.hilo_supervisor.start()

            self.iniciado = True

        print("Los dos hilos se iniciaron correctamente")

    def enviar_solicitud(self, operacion, nombre, ruta=None):
        """Envía una solicitud al trabajador y espera su resultado."""

        solicitud = {
            "operacion": operacion,
            "nombre": nombre,
            "ruta": ruta,
            "evento": threading.Event(),
            "resultado": None,
            "error": None
        }

        with self.lock:

            if not self.iniciado:
                raise RuntimeError(
                    "Los hilos no han sido iniciados"
                )

            if self.finalizando or self.finalizado:
                raise RuntimeError(
                    "El administrador de hilos esta finalizando"
                )

            # Enviar la solicitud al trabajador.
            self.cola.put(solicitud)

        # Esperar a que termine la operación.
        solicitud["evento"].wait()

        if solicitud["error"] is not None:
            raise RuntimeError(solicitud["error"])

        return solicitud["resultado"]

    def procesar_solicitudes(self):
        """Procesa las solicitudes recibidas en la cola."""

        while True:

            solicitud = self.cola.get()

            try:

                # None indica que el trabajador debe terminar.
                if solicitud is None:
                    break

                operacion = solicitud["operacion"]
                nombre = solicitud["nombre"]
                ruta = solicitud["ruta"]

                self.cola_estados.put(
                    f"Iniciando operacion: {operacion}"
                )

                try:

                    if operacion == "copiar_desde":

                        resultado = (
                            self.operaciones.copiar_desde_fiunamfs(
                                nombre
                            )
                        )

                    elif operacion == "copiar_hacia":

                        resultado = (
                            self.operaciones.copiar_a_fiunamfs(
                                ruta
                            )
                        )

                    elif operacion == "eliminar":

                        resultado = (
                            self.operaciones.eliminar_archivo(
                                nombre
                            )
                        )

                    else:

                        raise ValueError(
                            f"Operacion no reconocida: {operacion}"
                        )

                    solicitud["resultado"] = resultado

                    self.cola_estados.put(
                        f"Operacion completada: {operacion}"
                    )

                except Exception as error:

                    solicitud["error"] = (
                        f"{type(error).__name__}: {error}"
                    )

                    self.cola_estados.put(
                        f"Error en operacion: {operacion}"
                    )

                finally:

                    # Avisar al menú que la solicitud terminó.
                    solicitud["evento"].set()

            finally:

                # Marcar la solicitud como procesada.
                self.cola.task_done()

    def supervisar(self):
        """Recibe y almacena los cambios de estado."""

        while True:

            estado = self.cola_estados.get()

            try:

                # None indica que el supervisor debe terminar.
                if estado is None:
                    break

                # Guardar el mensaje para mostrarlo desde main.py.
                self.cola_mensajes.put(estado)

            finally:

                self.cola_estados.task_done()

    def obtener_mensajes(self):
        """Obtiene los mensajes procesados por el supervisor."""

        # Esperar a que todos los estados pendientes sean procesados.
        self.cola_estados.join()

        mensajes = []

        while True:

            try:

                mensaje = self.cola_mensajes.get_nowait()
                mensajes.append(mensaje)

            except queue.Empty:
                break

        return mensajes

    def finalizar(self):
        """Finaliza los dos hilos de manera ordenada."""

        with self.lock:

            if not self.iniciado:
                return

            if self.finalizando or self.finalizado:
                return

            self.finalizando = True

        print("\nFinalizando los hilos...")

        # Esperar a que se procesen todas las solicitudes pendientes.
        self.cola.join()

        # Enviar señal de terminación al trabajador.
        self.cola.put(None)

        # Esperar a que termine el trabajador.
        self.hilo_trabajador.join()

        # Esperar a que el supervisor procese todos los estados.
        self.cola_estados.join()

        # Enviar señal de terminación al supervisor.
        self.cola_estados.put(None)

        # Esperar a que termine el supervisor.
        self.hilo_supervisor.join()

        with self.lock:
            self.finalizado = True

        print("Los hilos finalizaron correctamente")

