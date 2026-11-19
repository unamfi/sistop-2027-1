import sys
import stat
import errno
import time
import threading
import queue
from datetime import datetime

from fuse import FUSE, Operations, FuseOSError

import fiunamfs


def fecha_a_segundos(fecha):
    try:
        return datetime.strptime(fecha, "%Y%m%d%H%M%S").timestamp()
    except ValueError:
        return 0


def hilo_bitacora(cola):
    # Hilo consumidor: recibe por la cola lo que hacen los hilos de FUSE y lo muestra
    while True:
        mensaje = cola.get()
        if mensaje == None:
            break
        print("[bitácora]", mensaje)


class FiUnamFS_FUSE(Operations):

    def __init__(self, ruta_imagen, cola_bitacora):
        self.ruta = ruta_imagen
        self.sb = fiunamfs.leer_superbloque(ruta_imagen)
        self.cola = cola_bitacora

        # fusepy atiende cada petición en un hilo distinto; el candado evita que
        # dos hilos modifiquen la imagen al mismo tiempo (por ejemplo, que dos
        # copias elijan el mismo hueco libre)
        self.candado = threading.Lock()

        # Archivos que se están escribiendo. FUSE los manda en pedazos, pero la
        # asignación es contigua, así que se juntan aquí y se guardan al cerrarlos
        self.pendientes = {}

    def registrar(self, mensaje):
        hora = datetime.now().strftime("%H:%M:%S")
        hilo = str(threading.get_native_id())
        self.cola.put(hora + " (hilo " + hilo + ") " + mensaje)

    def nombre_de(self, path):
        return path[1:]

    def getattr(self, path, fh=None):
        ahora = time.time()

        if path == "/":
            return {
                'st_mode': stat.S_IFDIR | 0o755,
                'st_nlink': 2,
                'st_size': 0,
                'st_ctime': ahora,
                'st_mtime': ahora,
                'st_atime': ahora,
            }

        nombre = self.nombre_de(path)

        with self.candado:
            if nombre in self.pendientes:
                return {
                    'st_mode': stat.S_IFREG | 0o644,
                    'st_nlink': 1,
                    'st_size': len(self.pendientes[nombre]),
                    'st_ctime': ahora,
                    'st_mtime': ahora,
                    'st_atime': ahora,
                }

            entrada = fiunamfs.buscar_archivo(self.ruta, self.sb, nombre)

        if entrada == None:
            raise FuseOSError(errno.ENOENT)

        return {
            'st_mode': stat.S_IFREG | 0o644,
            'st_nlink': 1,
            'st_size': entrada['tamano'],
            'st_ctime': fecha_a_segundos(entrada['fecha_creacion']),
            'st_mtime': fecha_a_segundos(entrada['fecha_modificacion']),
            'st_atime': fecha_a_segundos(entrada['fecha_modificacion']),
        }

    def readdir(self, path, fh):
        with self.candado:
            archivos = fiunamfs.leer_directorio(self.ruta, self.sb)
            nombres_pendientes = list(self.pendientes.keys())

        lista = ['.', '..']
        for entrada in archivos:
            lista.append(entrada['nombre'])
        for nombre in nombres_pendientes:
            if nombre not in lista:
                lista.append(nombre)

        self.registrar("listar directorio (" + str(len(archivos)) + " archivos)")
        return lista

    def read(self, path, size, offset, fh):
        nombre = self.nombre_de(path)

        with self.candado:
            if nombre in self.pendientes:
                contenido = bytes(self.pendientes[nombre])
            else:
                contenido = fiunamfs.leer_archivo(self.ruta, self.sb, nombre)

        if contenido == None:
            raise FuseOSError(errno.ENOENT)

        if offset == 0:
            self.registrar("leer " + nombre + " (" + str(len(contenido)) + " bytes)")

        return contenido[offset:offset + size]

    def create(self, path, mode, fi=None):
        nombre = self.nombre_de(path)

        if len(nombre) > 15:
            raise FuseOSError(errno.ENAMETOOLONG)
        if not fiunamfs.validar_nombre(nombre):
            raise FuseOSError(errno.EINVAL)

        with self.candado:
            if fiunamfs.buscar_entrada_libre(self.ruta, self.sb) == -1:
                raise FuseOSError(errno.ENOSPC)
            self.pendientes[nombre] = bytearray()

        self.registrar("crear " + nombre)
        return 0

    def cargar_pendiente(self, nombre):
        # Si se escribe sobre un archivo que ya existe, se carga su contenido
        # para modificarlo en memoria (debe llamarse con el candado tomado)
        if nombre not in self.pendientes:
            contenido = fiunamfs.leer_archivo(self.ruta, self.sb, nombre)
            if contenido == None:
                raise FuseOSError(errno.ENOENT)
            self.pendientes[nombre] = bytearray(contenido)

    def write(self, path, data, offset, fh):
        nombre = self.nombre_de(path)

        with self.candado:
            self.cargar_pendiente(nombre)
            buffer = self.pendientes[nombre]
            if offset > len(buffer):
                buffer.extend(b'\x00' * (offset - len(buffer)))
            buffer[offset:offset + len(data)] = data

        return len(data)

    def truncate(self, path, length, fh=None):
        nombre = self.nombre_de(path)

        with self.candado:
            self.cargar_pendiente(nombre)
            buffer = self.pendientes[nombre]
            if length < len(buffer):
                del buffer[length:]
            else:
                buffer.extend(b'\x00' * (length - len(buffer)))

    def flush(self, path, fh):
        nombre = self.nombre_de(path)

        with self.candado:
            if nombre not in self.pendientes:
                return 0

            contenido = bytes(self.pendientes[nombre])
            del self.pendientes[nombre]

            # Si el archivo ya existía se reemplaza completo, porque al cambiar
            # de tamaño podría ya no caber en su lugar
            if fiunamfs.buscar_archivo(self.ruta, self.sb, nombre) != None:
                fiunamfs.eliminar_archivo(self.ruta, self.sb, nombre)

            guardado = fiunamfs.escribir_archivo(self.ruta, self.sb, nombre, contenido)

        if not guardado:
            self.registrar("ERROR: no cupo " + nombre)
            raise FuseOSError(errno.ENOSPC)

        self.registrar("guardar " + nombre + " (" + str(len(contenido)) + " bytes)")
        return 0

    def unlink(self, path):
        nombre = self.nombre_de(path)

        with self.candado:
            borrado = fiunamfs.eliminar_archivo(self.ruta, self.sb, nombre)

        if not borrado:
            raise FuseOSError(errno.ENOENT)

        self.registrar("eliminar " + nombre)

    def statfs(self, path):
        tamano_cluster = self.sb['tamano_cluster']
        clusters_datos = self.sb['clusters_totales'] - 1 - self.sb['clusters_directorio']

        with self.candado:
            archivos = fiunamfs.leer_directorio(self.ruta, self.sb)

        usados = 0
        for entrada in archivos:
            clusters = (entrada['tamano'] + tamano_cluster - 1) // tamano_cluster
            if clusters == 0:
                clusters = 1
            usados = usados + clusters

        return {
            'f_bsize': tamano_cluster,
            'f_frsize': tamano_cluster,
            'f_blocks': clusters_datos,
            'f_bfree': clusters_datos - usados,
            'f_bavail': clusters_datos - usados,
            'f_namemax': 15,
        }

    def chmod(self, path, mode):
        return 0

    def chown(self, path, uid, gid):
        return 0

    def utimens(self, path, times=None):
        return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python3 fiunamfs_fuse.py <imagen.img> <carpeta_de_montaje>")
        sys.exit(1)

    ruta_imagen = sys.argv[1]
    punto_montaje = sys.argv[2]

    sb = fiunamfs.leer_superbloque(ruta_imagen)
    if not fiunamfs.validar_superbloque(sb):
        print("No se montó la imagen para no dañarla")
        sys.exit(1)

    cola = queue.Queue()
    bitacora = threading.Thread(target=hilo_bitacora, args=(cola,), name="bitacora")
    bitacora.start()

    print("Montando", ruta_imagen, "en", punto_montaje)
    print("Para desmontar: fusermount -u", punto_montaje, "(o Ctrl+C aquí)")

    sistema = FiUnamFS_FUSE(ruta_imagen, cola)
    FUSE(sistema, punto_montaje, foreground=True, nothreads=False)

    cola.put(None)
    bitacora.join()
    print("Imagen desmontada")
