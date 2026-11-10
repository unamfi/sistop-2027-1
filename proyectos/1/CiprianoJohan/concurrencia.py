#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
concurrencia.py — Acceso multihilos a un volumen FiUnamFS

Proyecto 1 · Sistemas Operativos 2027-1 · Facultad de Ingeniería, UNAM
Autor: Cipriano Amador Johan Tadeo

Organización de los hilos
-------------------------
* Hilo de interfaz (el principal): atiende al usuario y *solicita*
  operaciones; nunca toca la imagen directamente.
* Hilo «disco»: es el único dueño del archivo de imagen. Toma las
  solicitudes de una cola, las ejecuta una por una y publica el nuevo
  estado del volumen.
* Hilo «bitácora»: espera a que el estado cambie y registra cada operación
  junto con el espacio libre resultante.

Mecanismos de sincronización
----------------------------
* `queue.Queue` (productor–consumidor): la interfaz deposita solicitudes y
  el hilo disco las consume. Como un solo hilo escribe en la imagen, las
  operaciones quedan serializadas y no pueden corromper el directorio.
* `threading.Event` por solicitud: la interfaz espera la respuesta sin
  sondear; el hilo disco la avisa al terminar.
* `threading.Condition` sobre el estado compartido: el hilo disco lo
  actualiza con el candado tomado y hace `notify_all()`; la bitácora
  despierta solo cuando hay una versión nueva.
"""

import queue
import threading
from datetime import datetime

from fiunamfs import FiUnamFS, ErrorFiUnamFS


class Solicitud:
    """Una operación pedida al hilo disco, con su respuesta y su aviso."""

    def __init__(self, operacion, *argumentos):
        self.operacion = operacion
        self.argumentos = argumentos
        self.resultado = None
        self.error = None
        self.terminada = threading.Event()


class EstadoVolumen:
    """Estado del volumen compartido entre hilos, protegido por una Condition."""

    def __init__(self):
        self.condicion = threading.Condition()
        self.version = 0
        self.archivos = []
        self.clusters_libres = 0
        self.ultima_operacion = ""
        self.cerrado = False

    def publicar(self, archivos, clusters_libres, descripcion):
        """Lo llama el hilo disco después de cada operación."""
        with self.condicion:
            self.archivos = archivos
            self.clusters_libres = clusters_libres
            self.ultima_operacion = descripcion
            self.version += 1
            self.condicion.notify_all()

    def cerrar(self):
        with self.condicion:
            self.cerrado = True
            self.condicion.notify_all()

    def esperar_cambio(self, version_vista):
        """Bloquea hasta que haya una versión posterior a `version_vista`.

        Devuelve una copia (versión, descripción, libres), o None si se cerró.
        """
        with self.condicion:
            self.condicion.wait_for(
                lambda: self.version > version_vista or self.cerrado)
            if self.version <= version_vista:
                return None
            return self.version, self.ultima_operacion, self.clusters_libres

    def instantanea(self):
        """Copia consistente del estado para quien solo quiere leerlo."""
        with self.condicion:
            return list(self.archivos), self.clusters_libres, self.version


class VolumenConcurrente:
    """Fachada que usa la interfaz: cada método encola una solicitud y espera."""

    def __init__(self, ruta_imagen):
        # Abrir aquí (y no en el hilo) permite reportar de inmediato si la
        # imagen no es válida; a partir de este punto solo el hilo disco la usa.
        self._volumen = FiUnamFS(ruta_imagen)
        self.superbloque = self._volumen.superbloque
        self.estado = EstadoVolumen()
        self.bitacora = []
        self._bitacora_candado = threading.Lock()
        self._cola = queue.Queue()
        self._publicar("volumen abierto")   # antes de arrancar los hilos

        self._hilo_disco = threading.Thread(
            target=self._atender_disco, name="disco", daemon=True)
        self._hilo_bitacora = threading.Thread(
            target=self._llevar_bitacora, name="bitácora", daemon=True)
        self._hilo_disco.start()
        self._hilo_bitacora.start()

    # -- Operaciones que solicita la interfaz --------------------------------
    def listar(self):
        return self._solicitar("listar")

    def extraer(self, nombre, destino="."):
        return self._solicitar("extraer", nombre, destino)

    def copiar_hacia(self, ruta_local, nombre=None):
        return self._solicitar("copiar_hacia", ruta_local, nombre)

    def eliminar(self, nombre):
        return self._solicitar("eliminar", nombre)

    def obtener_bitacora(self):
        with self._bitacora_candado:
            return list(self.bitacora)

    def cerrar(self):
        """Pide al hilo disco que termine y espera a ambos hilos."""
        self._cola.put(None)                # centinela: no hay más trabajo
        self._hilo_disco.join()
        self.estado.cerrar()
        self._hilo_bitacora.join()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cerrar()

    # -- Lado de la interfaz: encolar y esperar ------------------------------
    def _solicitar(self, operacion, *argumentos):
        solicitud = Solicitud(operacion, *argumentos)
        self._cola.put(solicitud)
        solicitud.terminada.wait()
        if solicitud.error is not None:
            raise solicitud.error
        return solicitud.resultado

    # -- Hilo disco ----------------------------------------------------------
    def _atender_disco(self):
        while True:
            solicitud = self._cola.get()
            if solicitud is None:
                self._volumen.cerrar()
                break
            try:
                metodo = getattr(self._volumen, solicitud.operacion)
                solicitud.resultado = metodo(*solicitud.argumentos)
                if solicitud.operacion != "listar":
                    self._publicar(describir(solicitud))
            except (OSError, ErrorFiUnamFS) as error:
                solicitud.error = error
            finally:
                # Siempre avisar, aunque haya fallado, para no dejar a la
                # interfaz esperando para siempre.
                solicitud.terminada.set()

    def _publicar(self, descripcion):
        """Recalcula el estado (solo desde el hilo disco o antes de iniciar)."""
        archivos = self._volumen.listar()
        self.estado.publicar(archivos, self._volumen.clusters_libres(), descripcion)

    # -- Hilo bitácora -------------------------------------------------------
    def _llevar_bitacora(self):
        version_vista = 0
        while True:
            cambio = self.estado.esperar_cambio(version_vista)
            if cambio is None:
                break
            version_vista, descripcion, libres = cambio
            hora = datetime.now().strftime("%H:%M:%S")
            with self._bitacora_candado:
                self.bitacora.append(
                    f"[{hora}] {descripcion} — {libres} clusters libres")


def describir(solicitud):
    """Texto breve de una operación para la bitácora."""
    args = solicitud.argumentos
    if solicitud.operacion == "extraer":
        return f"extraído '{args[0]}'"
    if solicitud.operacion == "copiar_hacia":
        return f"copiado '{solicitud.resultado.nombre}' al volumen"
    if solicitud.operacion == "eliminar":
        return f"eliminado '{args[0]}'"
    return solicitud.operacion
