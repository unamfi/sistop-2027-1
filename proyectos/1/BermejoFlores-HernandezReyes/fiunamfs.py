#!/usr/bin/env python3
"""
FiUnamFS 27-1: cliente multihilos para el micro sistema de archivos.

Proyecto 1 de Sistemas Operativos (Facultad de Ingeniería, UNAM).
Autores:
- Bermejo Flores José Tristán — 321016719
- Hernández Reyes Rebeca Sarai — 321491864

Qué hace
--------
Opera sobre una imagen FiUnamFS (archivo de 1440 KB) y permite listar el
directorio, copiar un archivo del disco a tu equipo, copiar un archivo de tu
equipo al disco y eliminar archivos del disco.

Uso
---
  python3 fiunamfs.py fiunamfs.img            # menú guiado (no requiere ayuda)

También hay un modo de una sola orden, útil para guiones:
  python3 fiunamfs.py fiunamfs.img ls
  python3 fiunamfs.py fiunamfs.img get <nombre> [destino]
  python3 fiunamfs.py fiunamfs.img put <ruta> [nombre]
  python3 fiunamfs.py fiunamfs.img rm <nombre>
  python3 fiunamfs.py fiunamfs.img info

Requisitos
----------
Python 3.8 o superior. Solo biblioteca estándar (sin dependencias).

Estrategia de concurrencia
--------------------------
Hay dos hilos:
  * Hilo de interfaz (principal): atiende el menú, crea una
    Solicitud por cada operación y la deja en una cola.
  * Hilo del sistema de archivos ("hilo-fs"): es el único que toca la imagen;
    toma solicitudes de la cola, las ejecuta y avisa el resultado.

Mecanismos de sincronización:
  * queue.Queue  -> patrón productor/consumidor. El hilo-fs se bloquea en
                    cola.get() mientras no haya trabajo (sin espera activa).
  * threading.Event (Solicitud.terminada) -> el hilo-fs lo activa al terminar;
                    el hilo de interfaz espera en wait() y entonces lee el
                    resultado o el error. Así se comunica el estado.
  * threading.Lock (FiUnamFS.candado) -> exclusión mutua sobre la imagen;
                    hoy solo un hilo la usa, pero protege la lectura-
                    modificación-escritura del directorio si se agregan más.
"""

import os
import queue
import struct
import sys
import threading
from datetime import datetime

# --- Constantes de la especificación -------------------------------------
NOMBRE_FS = b"FiUnamFS"
VERSION_FS = b"27-1"
TAM_ENTRADA = 64
TIPO_ARCHIVO = b"F"
TIPO_VACIO = b"-"
# El disco de ejemplo del profesor difiere un poco del texto de la especificación:
# los nombres son de 14 caracteres rellenos con espacios más un byte nulo, y las
# entradas vacías llevan 14 '#' más el nulo. Al leer se aceptan ambas formas; al
# escribir se imita exactamente el disco de ejemplo.
MAX_NOMBRE = 14
NOMBRE_VACIO = b"#" * 14 + b"\x00"
NOMBRES_VACIOS = (b"#" * 14, b"#" + b"." * 14)    # sin nulo final
FECHA_VACIA = b"0" * 14


class ErrorFS(Exception):
    """Error esperable (entrada inválida, disco lleno, archivo inexistente...)."""


def validar_nombre(nombre):
    """Comprueba que 'nombre' sirva como nombre de archivo en FiUnamFS."""
    if not 1 <= len(nombre) <= MAX_NOMBRE:
        raise ErrorFS(f"El nombre debe tener de 1 a {MAX_NOMBRE} caracteres.")
    if any(not 32 <= ord(c) < 127 for c in nombre) or nombre != nombre.strip():
        raise ErrorFS("El nombre solo admite ASCII imprimible, sin espacios al inicio/final.")
    if set(nombre) <= {"#", "."}:
        raise ErrorFS("Ese nombre se confundiría con una entrada vacía.")


class Entrada:
    """Un archivo del directorio (ya interpretado)."""

    def __init__(self, indice, nombre, tamano, cluster, creacion, modificacion):
        self.indice = indice          # posición dentro del directorio
        self.nombre = nombre
        self.tamano = tamano          # bytes
        self.cluster = cluster        # cluster inicial
        self.creacion = creacion      # 'AAAAMMDDHHMMSS'
        self.modificacion = modificacion


class FiUnamFS:
    """Acceso de bajo nivel a la imagen. Todos los métodos públicos toman el candado."""

    def __init__(self, ruta):
        try:
            self.archivo = open(ruta, "r+b")
        except OSError as e:
            raise ErrorFS(f"No pude abrir la imagen '{ruta}': {e}")
        self.candado = threading.Lock()
        try:
            self._validar_superbloque()
        except Exception:
            self.archivo.close()
            raise

    # --- utilidades internas ---------------------------------------------
    def _leer(self, desplazamiento, cantidad):
        self.archivo.seek(desplazamiento)
        return self.archivo.read(cantidad)

    def _escribir(self, desplazamiento, datos):
        self.archivo.seek(desplazamiento)
        self.archivo.write(datos)
        self.archivo.flush()

    def _validar_superbloque(self):
        sb = self._leer(0, 64)
        if len(sb) < 52 or sb[0:8] != NOMBRE_FS:
            raise ErrorFS("La imagen no es un FiUnamFS (nombre incorrecto); no se modificará.")
        if sb[10:14] != VERSION_FS:
            version = sb[10:14].decode("ascii", "replace")
            raise ErrorFS(f"Versión no soportada ('{version}'); se requiere '27-1'.")
        self.etiqueta = sb[20:36].decode("ascii", "replace").rstrip(" \x00")
        self.tam_cluster, self.clusters_dir, self.clusters_total = struct.unpack("<III", sb[40:52])
        if self.tam_cluster == 0 or self.clusters_dir == 0 or self.clusters_total == 0:
            raise ErrorFS("Superbloque inconsistente (valores en cero).")
        self.archivo.seek(0, os.SEEK_END)
        if self.archivo.tell() < self.tam_cluster * self.clusters_total:
            raise ErrorFS("La imagen es más pequeña de lo que indica el superbloque.")
        self.inicio_datos = 1 + self.clusters_dir      # primer cluster de datos
        self.tam_directorio = self.clusters_dir * self.tam_cluster
        self.num_entradas = self.tam_directorio // TAM_ENTRADA

    def _clusters_de(self, tamano):
        # Un archivo vacío también ocupa un cluster, para tener inicio válido.
        return max(1, -(-tamano // self.tam_cluster))

    def _entradas_crudas(self):
        directorio = self._leer(self.tam_cluster, self.tam_directorio)
        return [directorio[i * TAM_ENTRADA:(i + 1) * TAM_ENTRADA] for i in range(self.num_entradas)]

    @staticmethod
    def _interpretar(indice, crudo):
        """Devuelve una Entrada, o None si la posición está libre."""
        if crudo[0:1] != TIPO_ARCHIVO or crudo[1:16].rstrip(b"\x00") in NOMBRES_VACIOS:
            return None
        tamano, cluster = struct.unpack("<II", crudo[16:24])
        return Entrada(
            indice,
            crudo[1:16].decode("ascii", "replace").rstrip(" \x00"),
            tamano,
            cluster,
            crudo[24:38].decode("ascii", "replace"),
            crudo[38:52].decode("ascii", "replace"),
        )

    def _archivos(self):
        crudas = self._entradas_crudas()
        usados = [self._interpretar(i, c) for i, c in enumerate(crudas)]
        return crudas, usados

    def _buscar(self, nombre, usados):
        for e in usados:
            if e is not None and e.nombre == nombre:
                return e
        raise ErrorFS(f"No existe el archivo '{nombre}' en FiUnamFS.")

    def _buscar_hueco(self, n_clusters, usados):
        """Primer hueco contiguo de n_clusters en el área de datos (first-fit)."""
        tramos = sorted((e.cluster, e.cluster + self._clusters_de(e.tamano))
                        for e in usados if e is not None)
        posicion = self.inicio_datos
        for inicio, fin in tramos:
            if inicio - posicion >= n_clusters:
                return posicion
            posicion = max(posicion, fin)
        if self.clusters_total - posicion >= n_clusters:
            return posicion
        return None

    # --- operaciones públicas (las ejecuta el hilo-fs) --------------------
    def info(self):
        with self.candado:
            _, usados = self._archivos()
            return {
                "etiqueta": self.etiqueta,
                "tam_cluster": self.tam_cluster,
                "clusters_dir": self.clusters_dir,
                "clusters_total": self.clusters_total,
                "archivos": sum(1 for e in usados if e is not None),
                "capacidad_entradas": self.num_entradas,
            }

    def listar(self):
        with self.candado:
            _, usados = self._archivos()
            return [e for e in usados if e is not None]

    def extraer(self, nombre, destino):
        """FiUnamFS -> equipo local. No sobrescribe archivos existentes."""
        with self.candado:
            _, usados = self._archivos()
            e = self._buscar(nombre, usados)
            inicio = e.cluster * self.tam_cluster
            if e.cluster < self.inicio_datos or inicio + e.tamano > self.clusters_total * self.tam_cluster:
                raise ErrorFS(f"La entrada de '{nombre}' apunta fuera del área de datos.")
            datos = self._leer(inicio, e.tamano)
        if os.path.isdir(destino):
            destino = os.path.join(destino, nombre)
        try:
            with open(destino, "xb") as salida:
                salida.write(datos)
        except FileExistsError:
            raise ErrorFS(f"'{destino}' ya existe; indica otro destino.")
        except OSError as err:
            raise ErrorFS(f"No pude escribir '{destino}': {err}")
        return len(datos), destino

    def copiar_dentro(self, ruta_local, nombre):
        """Equipo local -> FiUnamFS."""
        validar_nombre(nombre)
        try:
            tamano = os.path.getsize(ruta_local)
        except OSError as err:
            raise ErrorFS(f"No pude leer '{ruta_local}': {err}")
        if tamano > (self.clusters_total - self.inicio_datos) * self.tam_cluster:
            raise ErrorFS("El archivo es más grande que todo el espacio de datos.")
        with open(ruta_local, "rb") as entrada:
            datos = entrada.read()

        with self.candado:
            crudas, usados = self._archivos()
            if any(e is not None and e.nombre == nombre for e in usados):
                raise ErrorFS(f"Ya existe '{nombre}' en FiUnamFS.")
            libres = [i for i, e in enumerate(usados) if e is None]
            if not libres:
                raise ErrorFS("El directorio está lleno.")
            n = self._clusters_de(tamano)
            cluster = self._buscar_hueco(n, usados)
            if cluster is None:
                raise ErrorFS(f"No hay {n} clusters contiguos libres (disco lleno o fragmentado).")

            # Primero los datos (rellenos a cluster completo) y al final la entrada,
            # para que un fallo a medias no deje una entrada apuntando a basura.
            self._escribir(cluster * self.tam_cluster, datos.ljust(n * self.tam_cluster, b"\x00"))
            ahora = datetime.now().strftime("%Y%m%d%H%M%S").encode("ascii")
            nueva = (TIPO_ARCHIVO + nombre.encode("ascii").ljust(MAX_NOMBRE, b" ") + b"\x00"
                     + struct.pack("<II", tamano, cluster) + ahora + ahora + b"\x00" * 12)
            self._escribir(self.tam_cluster + libres[0] * TAM_ENTRADA, nueva)
        return tamano, cluster

    def eliminar(self, nombre):
        with self.candado:
            _, usados = self._archivos()
            e = self._buscar(nombre, usados)
            vacia = (TIPO_VACIO + NOMBRE_VACIO + struct.pack("<II", 0, 0)
                     + FECHA_VACIA + FECHA_VACIA + b"\x00" * 12)
            self._escribir(self.tam_cluster + e.indice * TAM_ENTRADA, vacia)

    def cerrar(self):
        self.archivo.close()


# --- Hilos y sincronización ----------------------------------------------
class Solicitud:
    """Trabajo que el hilo de interfaz le pide al hilo-fs."""

    def __init__(self, operacion, *args):
        self.operacion = operacion
        self.args = args
        self.terminada = threading.Event()   # se activa cuando el hilo-fs acaba
        self.resultado = None
        self.error = None


def hilo_fs(fs, cola):
    """Consumidor: único hilo que opera la imagen. Termina al recibir None."""
    while True:
        solicitud = cola.get()               # bloquea sin espera activa
        if solicitud is None:
            break
        try:
            solicitud.resultado = getattr(fs, solicitud.operacion)(*solicitud.args)
        except Exception as err:             # cualquier fallo se reporta, nunca cuelga la interfaz
            solicitud.error = str(err)
        finally:
            solicitud.terminada.set()        # avisa al hilo de interfaz


def pedir(cola, operacion, *args):
    """Productor: encola la solicitud y espera el aviso del hilo-fs."""
    solicitud = Solicitud(operacion, *args)
    cola.put(solicitud)
    solicitud.terminada.wait()
    if solicitud.error:
        raise ErrorFS(solicitud.error)
    return solicitud.resultado


# --- Interfaz de usuario ---------------------------------------------------
AYUDA = """Órdenes (modo de una sola orden):
  ls                       lista los archivos
  get <nombre> [destino]   copia de FiUnamFS a tu equipo
  put <ruta> [nombre]      copia de tu equipo a FiUnamFS
  rm  <nombre>             elimina un archivo de FiUnamFS
  info                     datos del volumen
Sin orden, el programa abre un menú guiado."""

MENU = """
==== FiUnamFS: {etiqueta} ====
  1. Ver los archivos del disco
  2. Copiar un archivo del disco a mi equipo
  3. Copiar un archivo de mi equipo al disco
  4. Eliminar un archivo del disco
  5. Información del disco
  0. Salir"""


def formatear_fecha(s):
    if len(s) == 14 and s.isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}:{s[12:14]}"
    return s


def mostrar_archivos(archivos, numerar=False, detalle=False):
    for i, e in enumerate(archivos, 1):
        numero = f"{i:>2}) " if numerar else ""
        linea = f"{numero}{e.nombre:<14} {e.tamano:>9} B"
        if detalle:
            linea += (f"  cluster {e.cluster:<4} creado {formatear_fecha(e.creacion)}"
                      f"  modif. {formatear_fecha(e.modificacion)}")
        else:
            linea += f"   modificado {formatear_fecha(e.modificacion)}"
        print(linea)


def elegir_archivo(cola, accion):
    """Muestra los archivos numerados y devuelve el elegido (None si se cancela)."""
    archivos = pedir(cola, "listar")
    if not archivos:
        print("El disco no tiene archivos.")
        return None
    mostrar_archivos(archivos, numerar=True)
    while True:
        respuesta = input(f"Número del archivo a {accion} (Enter para cancelar): ").strip()
        if respuesta == "":
            return None
        if respuesta.isdigit() and 1 <= int(respuesta) <= len(archivos):
            return archivos[int(respuesta) - 1]
        print(f"Escribe un número entre 1 y {len(archivos)}.")


def opcion_ver_archivos(cola):
    archivos = pedir(cola, "listar")
    if archivos:
        mostrar_archivos(archivos, detalle=True)
    else:
        print("El disco no tiene archivos.")


def opcion_copiar_a_equipo(cola):
    archivo = elegir_archivo(cola, "copiar a tu equipo")
    if archivo is None:
        return
    destino = input(f"Guardar como (archivo o carpeta) [{archivo.nombre}]: ").strip() or archivo.nombre
    n, ruta = pedir(cola, "extraer", archivo.nombre, destino)
    print(f"Listo: '{archivo.nombre}' se guardó en '{ruta}' ({n} bytes).")


def opcion_copiar_al_disco(cola):
    ruta = input("Ruta del archivo de tu equipo (Enter para cancelar): ").strip().strip("\"'")
    if not ruta:
        return
    ruta = os.path.expanduser(ruta)
    if not os.path.isfile(ruta):
        print(f"No encuentro el archivo '{ruta}'.")
        return
    base = os.path.basename(ruta)
    nombre = input(f"Nombre que tendrá en el disco, máx. {MAX_NOMBRE} caracteres [{base}]: ").strip() or base
    while True:                       # se insiste hasta tener un nombre válido
        try:
            validar_nombre(nombre)
            break
        except ErrorFS as err:
            print(f"El nombre '{nombre}' no sirve: {err}")
            nombre = input("Escribe otro nombre (Enter para cancelar): ").strip()
            if not nombre:
                return
    tamano, cluster = pedir(cola, "copiar_dentro", ruta, nombre)
    print(f"Listo: '{nombre}' se copió al disco ({tamano} bytes).")


def opcion_eliminar(cola):
    archivo = elegir_archivo(cola, "eliminar")
    if archivo is None:
        return
    if input(f"¿Seguro que quieres eliminar '{archivo.nombre}' del disco? (s/n): ").strip().lower() != "s":
        print("No se eliminó nada.")
        return
    pedir(cola, "eliminar", archivo.nombre)
    print(f"Listo: '{archivo.nombre}' se eliminó del disco.")


def opcion_info(cola):
    datos = pedir(cola, "info")
    print(f"Etiqueta del volumen: {datos['etiqueta']}")
    print(f"Tamaño de cluster:    {datos['tam_cluster']} bytes")
    print(f"Clusters en total:    {datos['clusters_total']} ({datos['clusters_dir']} del directorio)")
    print(f"Archivos:             {datos['archivos']} de {datos['capacidad_entradas']} posibles")


def menu(cola, etiqueta):
    """Menú guiado: pregunta lo que necesita, no hace falta conocer órdenes."""
    acciones = {"1": opcion_ver_archivos, "2": opcion_copiar_a_equipo,
                "3": opcion_copiar_al_disco, "4": opcion_eliminar, "5": opcion_info}
    while True:
        print(MENU.format(etiqueta=etiqueta))
        try:
            opcion = input("Elige una opción: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if opcion in ("0", "q", "salir"):
            return
        accion = acciones.get(opcion)
        if accion is None:
            print("Opción no válida: escribe un número del menú.")
            continue
        try:
            accion(cola)
        except ErrorFS as err:
            print(f"Error: {err}")
        except (EOFError, KeyboardInterrupt):
            print("\nOperación cancelada.")


def atender(cola, partes):
    """Modo de una sola orden (para guiones o uso rápido)."""
    orden, args = partes[0].lower(), partes[1:]
    try:
        if orden in ("ls", "dir", "listar") and not args:
            archivos = pedir(cola, "listar")
            mostrar_archivos(archivos, detalle=True) if archivos else print("(directorio vacío)")
        elif orden == "get" and 1 <= len(args) <= 2:
            destino = args[1] if len(args) == 2 else args[0]
            n, ruta = pedir(cola, "extraer", args[0], destino)
            print(f"Copiado '{args[0]}' -> '{ruta}' ({n} bytes).")
        elif orden == "put" and 1 <= len(args) <= 2:
            nombre = args[1] if len(args) == 2 else os.path.basename(args[0])
            tamano, cluster = pedir(cola, "copiar_dentro", args[0], nombre)
            print(f"Copiado '{args[0]}' -> FiUnamFS como '{nombre}' ({tamano} bytes, cluster {cluster}).")
        elif orden == "rm" and len(args) == 1:
            pedir(cola, "eliminar", args[0])
            print(f"Eliminado '{args[0]}'.")
        elif orden == "info" and not args:
            opcion_info(cola)
        else:
            print(AYUDA)
    except ErrorFS as err:
        print(f"Error: {err}")


def main(argv):
    if not argv:
        print("Uso: python3 fiunamfs.py <imagen> [orden [argumentos]]")
        return 1
    try:
        fs = FiUnamFS(argv[0])
    except ErrorFS as err:
        print(f"Error: {err}")
        return 1

    cola = queue.Queue()
    hilo = threading.Thread(target=hilo_fs, args=(fs, cola), name="hilo-fs")
    hilo.start()
    try:
        if len(argv) > 1:
            atender(cola, argv[1:])
        else:
            menu(cola, fs.etiqueta)
    finally:
        cola.put(None)       # señal de término para el hilo-fs
        hilo.join()
        fs.cerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
