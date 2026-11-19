#!/usr/bin/python3
'''
Proyecto 1: Micro-Sistema de archivos multihilos
Programa que pueda obtener, crear y modificar información en el micro-sistema
de archivos FIUnamFS desarrollado por el profesor Gunnar Eyal Wolf Iszaevich.

--------------------------------------------------------------------------------------

Datos:
Universidad Nacional Autónoma de México
Facultad de Ingeniería
Sistemas Operativos -> Grupo 7
Profesor: Gunnar Eyal Wolf Iszaevich
Hecho por: 
- Hernández Andrade Miguel Ángel
- Santos Cruz Lair Abraham

--------------------------------------------------------------------------------------

El programa debe ser capaz de:
- Listar los contenidos del directorio
- Copiar uno de los archivos de dentro del FiUnamFS hacia tu sistema
- Copiar un archivo de tu computadora hacia tu FiUnamFS
- Eliminar un archivo del FiUnamFS
- Ejecutar al menos dos hilos de ejecución, operando concurrentemente, 
y que se comuniquen su estado mediante mecanismos de sincronización.

--------------------------------------------------------------------------------------

Especificación de FIUnamFS:
- El sistema de archivos cabe en un diskette tradicional, será simulado en 
un archivo de 1440 KB.
- Por simplicidad, en todas las estructuras de FIUnamFS, las cadenas de texto deben ser 
ASCII 8-bit (no requerimos que sean Unicode UTF-8).
- En las estructuras del disco, todos los enteros serán representados como valores de 
32 bits, en formato little endian.
- La superficie del disco se divide en sectores de 512 bytes. Cada cluster mide cuatro sectores.
- El pseudodispositivo no maneja tabla de particiones, sino que hospeda directamente un volumen 
en la totalidad de su espacio.
- FiUnamFS maneja únicamente un directorio plano, no considera subdirectorios.
- El primer cluster (#0) del pseudodispositivo es el superbloque. Este contiene información en los siguientes bytes:
0-7
Para identificación, el nombre del sistema de archivos. ¡Debes validar nunca modificar un sistema de archivos 
que no sea el correcto! Debe ser la cadena FiUnamFS.
10-13
Versión de la implementación. Estamos implementando la versión 27-1 (ojo, es una cadena, no un número). Deben validar 
que el sistema de archivos a utilizar sea de esta versión, para evitar la corrupción de datos.
20-35
Etiqueta del volumen
40-43
Tamaño del cluster en bytes
44-47
Número de clusters que mide el directorio
48-51
Número de clusters que mide la unidad completa
El resto del superbloque puede quedar vacío (o puedes sobrecargarlo con otros datos — No es importante para la implementación.
- El sistema de archivos es de asignación contigua. Toda la información de los archivos está en el directorio.
- El directorio está ubicado en los clusters 1 a 4. Cada entrada del directorio mide 64 bytes, consistentes en:
0
Tipo de archivo. Dado que el sistema de archivos actual no tien soporte para directorios, dispositivos, pipes, ni otros 
archivos especiales, siempre será el caracter F (0x46, 70). Cuando la entrada está vacía, se indica con el caracter - (0x2d, 45).
1-15
Nombre del archivo
16-19
Tamaño del archivo, en bytes
20-23
Cluster inicial
24-37
Hora y fecha de creación del archivo, especificando AAAAMMDDHHMMSS
38-51
Hora y fecha de última modificación del archivo, especificando AAAAMMDDHHMMSS
52-63
Espacio no utilizado (¿reservado para expansión futura?)
Las entradas no utilizadas del directorio se identifican porque en el campo de nombre llevan la cadena #...............
- Es un sistema de archivos plano — No maneja subdirectorios.
- Después del directorio, todo el espacio restante es espacio de datos.

--------------------------------------------------------------------------------------

'''

import os
import sys
import stat
import errno
import struct
import threading
from datetime import datetime
import fuse
from collections import deque

#Version de la API de FUSE que se está utilizando
fuse.fuse_python_api = (0, 2)

# Constantes de FiUnamFS (1440 KB = 720 clusters de 2048 bytes)
CLUSTER_SIZE = 2048
TOTAL_CLUSTERS = 720
DIR_INICIO = 1
ENTRADA_SIZE = 64
MAX_ENTRADAS = 128
DATOS_INICIO = 5


class FiUnamFS(fuse.Fuse):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        ruta = "fiunamfs.img" if os.path.exists("fiunamfs.img") else "../fiunamfs.img"
        self.disco = open(os.path.abspath(ruta), "rb+")

        # Validación de identidad y versión en el superbloque 
        sb = self.disco.read(CLUSTER_SIZE)
        if sb[0:8] != b"FiUnamFS" or sb[10:14] != b"27-1":
            raise ValueError("Imagen inválida: debe ser FiUnamFS versión 27-1.")

        # Mecanismos de sincronización (Patrón Jefe-Trabajador con semáforos)
        self.mutex = threading.Semaphore(1)       # Protege acceso a la cola y al archivo .img
        self.peticiones = threading.Semaphore(0)  # Cuenta operaciones pendientes por bajar a disco
        self.cola_cambios = deque()               # Equivalente a la 'cinta' de solicitudes
        self.activo = True
        self.hilo_trabajador = threading.Thread(target=self._trabajador_disco, daemon=True)


    def fsinit(self):
        self.hilo_trabajador.start()

    def fsdestroy(self):
        with self.mutex:
            self.activo = False
        self.peticiones.release() 
        self.hilo_trabajador.join(timeout=2)
        self.disco.close()

    def _encolar_operacion(self, mensaje: str):
        """Mete la operación a la cola y libera un permiso."""
        with self.mutex:
            self.cola_cambios.append(mensaje)
        self.peticiones.release()

    def _trabajador_disco(self):
        """Espera peticiones en el semáforo y sincroniza el disco."""
        while True:
            self.peticiones.acquire()

            with self.mutex:
                if not self.activo and not self.cola_cambios:
                    break
                tarea = self.cola_cambios.popleft()
                self.disco.flush()
                os.fsync(self.disco.fileno())

            print(f"[Trabajador Disco] Sincronizado -> {tarea}")

    # ------------------------------------------------------------------
    # Operaciones sobre directorio y asignación contigua
    # ------------------------------------------------------------------

    def enlistar_archivos(self):
        """Recorre las 128 entradas del directorio y devuelve los archivos válidos ordenados."""
        archivos = []
        self.disco.seek(DIR_INICIO * CLUSTER_SIZE)

        for i in range(MAX_ENTRADAS):
            entrada = self.disco.read(ENTRADA_SIZE)
            tipo = chr(entrada[0])
            nombre = entrada[1:16].decode("ascii", errors="ignore").strip("\x00 ")

            # Validamos que sea un archivo activo ('F') y no una entrada vacía ('#...')
            if tipo == "F" and nombre != "" and not nombre.startswith("#"):
                tamano, cluster_ini = struct.unpack("<II", entrada[16:24])
                archivos.append({
                    "indice": i,
                    "nombre": nombre,
                    "tamano": tamano,
                    "cluster_ini": cluster_ini,
                    "creacion": entrada[24:38].decode("ascii", errors="ignore"),
                    "modif": entrada[38:52].decode("ascii", errors="ignore"),
                })

        # Ordenamiento por nombre 
        archivos.sort(key=lambda archivo: archivo["nombre"])
        return archivos

    def escribir_entrada_directorio(self, indice: int, nombre: str, tamano: int,
                                    cluster_ini: int, creacion: str, modif: str):
        """Empaqueta una ficha de 64 bytes en ASCII/Little-Endian y la guarda en el directorio."""
        nombre_bytes = nombre.encode("ascii")[:15].ljust(15, b"\x00")
        datos_numericos = struct.pack("<II", tamano, cluster_ini)
        fecha_creacion = creacion.encode("ascii")[:14].ljust(14, b"0")
        fecha_modif = modif.encode("ascii")[:14].ljust(14, b"0")
        relleno = b"\x00" * 12

        entrada = b"F" + nombre_bytes + datos_numericos + fecha_creacion + fecha_modif + relleno
        posicion_bytes = (DIR_INICIO * CLUSTER_SIZE) + (indice * ENTRADA_SIZE)

        self.disco.seek(posicion_bytes)
        self.disco.write(entrada)

    def buscar_clusters_contiguos(self, archivos: list, clusters_necesarios: int,
                                  indice_ignorar: int = -1):
        """Busca un bloque continuo de clusters libres y devuelve el cluster inicial (o -1)."""
        # Mapa del disco: False = libre, True = ocupado
        clusters_ocupados = [False] * TOTAL_CLUSTERS

        # Los clusters 0 al 4 están reservados (Superbloque y Directorio)
        for c in range(DATOS_INICIO):
            clusters_ocupados[c] = True

        # Marcamos los clusters que ya pertenecen a otros archivos
        for arch in archivos:
            if arch["indice"] == indice_ignorar:
                continue
            clusters_usados = max(1, (arch["tamano"] + CLUSTER_SIZE - 1) // CLUSTER_SIZE)
            fin = min(TOTAL_CLUSTERS, arch["cluster_ini"] + clusters_usados)
            for c in range(arch["cluster_ini"], fin):
                clusters_ocupados[c] = True

        # Buscamos N clusters libres seguidos en la zona de datos
        contador_libres = 0
        for c in range(DATOS_INICIO, TOTAL_CLUSTERS):
            if not clusters_ocupados[c]:
                contador_libres += 1
                if contador_libres == clusters_necesarios:
                    return c - clusters_necesarios + 1
            else:
                contador_libres = 0

        return -1 

    # ------------------------------------------------------------------
    # Interfaz FUSE (ls, cp, rm)
    # ------------------------------------------------------------------

    def getattr(self, path: str):
        st = fuse.Stat()
        if path == "/":
            st.st_mode = stat.S_IFDIR | 0o755
            st.st_nlink = 2
            return st

        with self.mutex:
            arch = next((a for a in self.enlistar_archivos() if a["nombre"] == path[1:]), None)
        if not arch:
            return -errno.ENOENT

        st.st_mode = stat.S_IFREG | 0o644
        st.st_nlink = 1
        st.st_size = arch["tamano"]
        try:
            st.st_ctime = datetime.strptime(arch["creacion"], "%Y%m%d%H%M%S").timestamp()
            st.st_mtime = datetime.strptime(arch["modif"], "%Y%m%d%H%M%S").timestamp()
        except ValueError:
            pass
        st.st_atime = st.st_mtime
        return st

    def readdir(self, path: str, offset: int):
        if path != "/":
            return -errno.ENOENT
        with self.mutex:
            archivos = self.enlistar_archivos()
        yield fuse.Direntry(".")
        yield fuse.Direntry("..")
        for a in archivos:
            yield fuse.Direntry(a["nombre"])

    def read(self, path: str, size: int, offset: int) -> bytes:
        with self.mutex:
            arch = next((a for a in self.enlistar_archivos() if a["nombre"] == path[1:]), None)
            if not arch:
                return -errno.ENOENT
            if offset >= arch["tamano"]:
                return b""
            size = min(size, arch["tamano"] - offset)
            self.disco.seek((arch["cluster_ini"] * CLUSTER_SIZE) + offset)
            return self.disco.read(size)

    def create(self, path: str, flags: int, mode: int):
        nombre = path[1:]
        if "/" in nombre or not (1 <= len(nombre) <= 15):
            return -errno.EINVAL
        try:
            nombre.encode("ascii")
        except UnicodeEncodeError:
            return -errno.EINVAL

        with self.mutex:
            archivos = self.enlistar_archivos()
            if any(a["nombre"] == nombre for a in archivos):
                return -errno.EEXIST

            usados = {a["indice"] for a in archivos}
            slot = next((i for i in range(MAX_ENTRADAS) if i not in usados), -1)
            cluster_ini = self.buscar_clusters_contiguos(archivos, 1)
            if slot == -1 or cluster_ini == -1:
                return -errno.ENOSPC

            ahora = datetime.now().strftime("%Y%m%d%H%M%S")
            self.escribir_entrada_directorio(slot, nombre, 0, cluster_ini, ahora, ahora)

        self._encolar_operacion(f"Creado: {nombre}")
        return 0

    def write(self, path: str, body: bytes, offset: int) -> int:
        with self.mutex:
            archivos = self.enlistar_archivos()
            arch = next((a for a in archivos if a["nombre"] == path[1:]), None)
            if not arch:
                return -errno.ENOENT

            nuevo_tam = max(arch["tamano"], offset + len(body))
            req_clusters = max(1, (nuevo_tam + CLUSTER_SIZE - 1) // CLUSTER_SIZE)
            act_clusters = max(1, (arch["tamano"] + CLUSTER_SIZE - 1) // CLUSTER_SIZE)
            cluster_ini = arch["cluster_ini"]

            if req_clusters > act_clusters:
                nuevo_ini = self.buscar_clusters_contiguos(archivos, req_clusters, arch["indice"])
                if nuevo_ini == -1:
                    return -errno.ENOSPC
                if nuevo_ini != cluster_ini and arch["tamano"] > 0:
                    self.disco.seek(cluster_ini * CLUSTER_SIZE)
                    previo = self.disco.read(arch["tamano"])
                    self.disco.seek(nuevo_ini * CLUSTER_SIZE)
                    self.disco.write(previo)
                cluster_ini = nuevo_ini

            self.disco.seek((cluster_ini * CLUSTER_SIZE) + offset)
            self.disco.write(body)

            ahora = datetime.now().strftime("%Y%m%d%H%M%S")
            self.escribir_entrada_directorio(arch["indice"], arch["nombre"], nuevo_tam, cluster_ini, arch["creacion"], ahora)
            nombre_arch = arch["nombre"]

        self._encolar_operacion(f"Escrito: {nombre_arch} ({nuevo_tam} B)")
        return len(body)

    def unlink(self, path: str):
        with self.mutex:
            arch = next((a for a in self.enlistar_archivos() if a["nombre"] == path[1:]), None)
            if not arch:
                return -errno.ENOENT

            nombre_arch = arch["nombre"]
            self.disco.seek((DIR_INICIO * CLUSTER_SIZE) + (arch["indice"] * ENTRADA_SIZE))
            self.disco.write(b"-" + b"#.............." + (b"\x00" * 48))

        # Afuera de self.mutex: se encola la tarea y se despierta al trabajador
        self._encolar_operacion(f"Eliminado: {nombre_arch}")
        return 0

if __name__ == "__main__":
    server = FiUnamFS(version="%prog " + fuse.__version__, usage=fuse.Fuse.fusage)
    server.parse(errex=1)
    server.main()