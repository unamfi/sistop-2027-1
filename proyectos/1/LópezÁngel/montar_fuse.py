"""Montaje Linux FUSE: ls, cp y rm sobre una imagen FiUnamFS 27-1."""

import sys

# Evita crear archivos .pyc y carpetas __pycache__ al ejecutar el proyecto.
sys.dont_write_bytecode = True

import argparse
from dataclasses import replace
from datetime import datetime
import errno
import os
from pathlib import Path
import stat

from concurrencia import TrabajadorDisco
from fiunamfs import (ErrorFormato, FORMATO_FECHA, TAMANO_ENTRADA,
                     analizar_volumen, buscar_entrada_libre, buscar_espacio_libre,
                     clusters_necesarios, crear_entrada, eliminar_archivo,
                     guardar_volumen, recorrer_directorio, texto, validar_nombre)

MASCARA_ACCESO = os.O_RDONLY | os.O_WRONLY | os.O_RDWR


# Traduce las solicitudes del sistema operativo sobre la carpeta montada
# a lecturas y modificaciones de los archivos contenidos en la imagen.
class DiscoFUSE:
    """Callbacks serializados por un único trabajador, incluidos los descriptores."""

    def __init__(self, imagen):
        self.imagen = Path(imagen).resolve(strict=True)
        self._cargar()
        self.descriptores = {}
        self.siguiente = 0
        self.trabajador = TrabajadorDisco()

    def cerrar(self):
        self.trabajador.cerrar()

    def ejecutar(self, operacion, *args):
        funcion = getattr(self, operacion, None)
        if operacion.startswith('_') or funcion is None:
            raise OSError(errno.EOPNOTSUPP, "Operación no soportada")
        # Enruta cada callback FUSE al hilo trabajador y traduce errores internos a códigos errno POSIX.
        try:
            return self.trabajador.ejecutar(funcion, *args)
        except ErrorFormato as exc:
            raise OSError(errno.EIO, str(exc)) from exc
        except ValueError as exc:
            raise OSError(errno.EINVAL, str(exc)) from exc

    def _cargar(self):
        datos = bytearray(self.imagen.read_bytes())
        volumen = analizar_volumen(datos)
        # Los nombres especiales de POSIX no se pueden exponer como archivos.
        if any('/' in a.nombre or '\x00' in a.nombre or a.nombre in ('.', '..')
               for a in volumen.archivos):
            raise ValueError("La imagen contiene nombres incompatibles con rutas POSIX.")
        return datos, volumen

    def _nombre(self, ruta):
        # Valida que la ruta pertenezca a la raíz plana de FiUnamFS y cumpla las reglas de nombre ASCII.
        if ruta == '/':
            raise OSError(errno.EISDIR, "Es el directorio raíz")
        if not ruta.startswith('/') or '/' in ruta[1:]:
            raise OSError(errno.ENOENT, "FiUnamFS no tiene subdirectorios")
        nombre = ruta[1:]
        if len(nombre.encode('utf-8')) > 15:
            raise OSError(errno.ENAMETOOLONG, "Máximo 15 caracteres ASCII")
        validar_nombre(nombre)
        if nombre in ('.', '..'):
            raise OSError(errno.EINVAL, "Nombre reservado por POSIX")
        return nombre

    def _archivo(self, volumen, nombre):
        for archivo in volumen.archivos:
            if archivo.nombre == nombre:
                return archivo
        raise OSError(errno.ENOENT, "Archivo inexistente")

    def _contenido(self, datos, volumen, archivo):
        inicio = archivo.cluster_inicial * volumen.tamano_cluster
        return bytes(datos[inicio:inicio + archivo.tamano])

    def _guardar(self, datos, volumen, nombre, contenido, nuevo=False):
        archivo = None if nuevo else self._archivo(volumen, nombre)
        try:
            # Localiza una entrada libre (creación) o la entrada actual del archivo (actualización).
            if nuevo:
                posicion = buscar_entrada_libre(datos, volumen)
            else:
                posicion = next(p for p, e in recorrer_directorio(datos, volumen.tamano_cluster,
                                 volumen.clusters_directorio) if e[:1] == b'F' and texto(e[1:16]) == nombre)
            # Excluye temporalmente el propio archivo para liberar sus clusters y buscar espacio contiguo (first fit).
            disponibles = replace(volumen, archivos=tuple(a for a in volumen.archivos if a.nombre != nombre))
            cantidad = clusters_necesarios(len(contenido), volumen.tamano_cluster)
            inicio = buscar_espacio_libre(disponibles, cantidad)
        except ValueError as exc:
            raise OSError(errno.ENOSPC, str(exc)) from exc
        entrada = crear_entrada(validar_nombre(nombre), len(contenido), inicio)
        # Conserva la fecha de creación original al sobrescribir y escribe los datos rellenando el último cluster.
        if archivo is not None:
            entrada[24:38] = datos[posicion + 24:posicion + 38]
        datos[posicion:posicion + TAMANO_ENTRADA] = entrada
        desde = inicio * volumen.tamano_cluster
        reservado = cantidad * volumen.tamano_cluster
        datos[desde:desde + reservado] = contenido.ljust(reservado, b'\x00')
        guardar_volumen(self.imagen, datos)

    def _limite(self, volumen, tamano):
        if tamano < 0:
            raise OSError(errno.EINVAL, "Tamaño o desplazamiento negativo")
        capacidad = (volumen.clusters_totales - 1 - volumen.clusters_directorio) * volumen.tamano_cluster
        if tamano > capacidad:
            raise OSError(errno.ENOSPC, "El archivo supera la capacidad del disco")

    # Tabla en memoria de descriptores abiertos (fh -> nombre y banderas POSIX) para validar accesos.
    def _descriptor(self, nombre, flags):
        self.siguiente += 1
        self.descriptores[self.siguiente] = (nombre, flags)
        return self.siguiente

    def _comprobar_descriptor(self, fh, nombre, escritura=False):
        if fh not in self.descriptores or self.descriptores[fh][0] != nombre:
            raise OSError(errno.EBADF, "Descriptor inválido")
        acceso = self.descriptores[fh][1] & MASCARA_ACCESO
        if (escritura and acceso == os.O_RDONLY) or (not escritura and acceso == os.O_WRONLY):
            raise OSError(errno.EBADF, "Modo de acceso inválido")

    # Metadatos y listado: permiten que ls y el explorador reconozcan
    # la carpeta raíz y los archivos que contiene el disco.
    def getattr(self, ruta, fh=None):
        datos, volumen = self._cargar()
        atributos = dict(st_uid=os.getuid() if hasattr(os, 'getuid') else 0,
                         st_gid=os.getgid() if hasattr(os, 'getgid') else 0,
                         st_blksize=volumen.tamano_cluster)
        # Construye metadatos tipo stat(): directorio raíz (0755) o archivo regular (0644) con fechas y bloques.
        if ruta == '/':
            atributos.update(st_mode=stat.S_IFDIR | 0o755, st_nlink=2, st_size=0)
        else:
            archivo = self._archivo(volumen, self._nombre(ruta))
            modificado = datetime.strptime(archivo.modificacion, '%Y-%m-%d %H:%M:%S').timestamp()
            creado = datetime.strptime(archivo.creacion, '%Y-%m-%d %H:%M:%S').timestamp()
            atributos.update(st_mode=stat.S_IFREG | 0o644, st_nlink=1, st_size=archivo.tamano,
                             st_mtime=modificado, st_ctime=creado, st_atime=modificado,
                             st_blocks=clusters_necesarios(archivo.tamano, volumen.tamano_cluster)
                             * (volumen.tamano_cluster // 512))
        return atributos

    def readdir(self, ruta, fh):
        # Expone las entradas virtuales '.' y '..' junto con todos los archivos activos del directorio único.
        if ruta != '/':
            raise OSError(errno.ENOTDIR, "No es un directorio")
        return ['.', '..'] + [a.nombre for a in self._cargar()[1].archivos]

    def opendir(self, ruta):
        if ruta != '/':
            raise OSError(errno.ENOTDIR, "No es un directorio")
        return 0

    def releasedir(self, ruta, fh):
        return 0

    def access(self, ruta, mode):
        self.getattr(ruta)
        if ruta != '/' and mode & os.X_OK:
            raise OSError(errno.EACCES, "Los archivos no son ejecutables")
        return 0

    def listxattr(self, ruta):
        return []

    # Apertura y acceso al contenido: estas operaciones permiten usar cp
    # y otros programas con los archivos de la carpeta montada.
    def open(self, ruta, flags):
        nombre = self._nombre(ruta)
        self._archivo(self._cargar()[1], nombre)
        # Si se abre con O_TRUNC, comprueba permiso de escritura y vacía el archivo antes de emitir el descriptor.
        if flags & os.O_TRUNC:
            if flags & MASCARA_ACCESO == os.O_RDONLY:
                raise OSError(errno.EACCES, "Se requiere permiso de escritura")
            self.truncate(ruta, 0)
        return self._descriptor(nombre, flags)

    def create(self, ruta, mode, fi=None):
        nombre = self._nombre(ruta)
        datos, volumen = self._cargar()
        if any(a.nombre == nombre for a in volumen.archivos):
            raise OSError(errno.EEXIST, "El archivo ya existe")
        # Crea un archivo vacío en el volumen y devuelve un descriptor abierto en modo lectura/escritura.
        self._guardar(datos, volumen, nombre, b'', nuevo=True)
        return self._descriptor(nombre, os.O_RDWR)

    def read(self, ruta, size, offset, fh):
        nombre = self._nombre(ruta)
        self._comprobar_descriptor(fh, nombre)
        if offset < 0 or size < 0:
            raise OSError(errno.EINVAL, "Lectura inválida")
        # Lee el archivo desde la imagen y devuelve únicamente el rango solicitado [offset : offset + size].
        datos, volumen = self._cargar()
        contenido = self._contenido(datos, volumen, self._archivo(volumen, nombre))
        return contenido[offset:offset + size]

    def write(self, ruta, contenido, offset, fh):
        nombre = self._nombre(ruta)
        self._comprobar_descriptor(fh, nombre, escritura=True)
        datos, volumen = self._cargar()
        anterior = self._contenido(datos, volumen, self._archivo(volumen, nombre))
        # Reconstruye el contenido respetando O_APPEND y rellenando huecos con ceros si offset supera el tamaño actual.
        if self.descriptores[fh][1] & os.O_APPEND:
            offset = len(anterior)
        self._limite(volumen, offset)
        self._limite(volumen, offset + len(contenido))
        if not contenido:
            return 0
        nuevo = anterior[:offset].ljust(offset, b'\x00') + contenido + anterior[offset + len(contenido):]
        self._guardar(datos, volumen, nombre, nuevo)
        return len(contenido)

    def truncate(self, ruta, length, fh=None):
        nombre = self._nombre(ruta)
        if fh is not None:
            self._comprobar_descriptor(fh, nombre, escritura=True)
        datos, volumen = self._cargar()
        self._limite(volumen, length)
        anterior = self._contenido(datos, volumen, self._archivo(volumen, nombre))
        # Recorta el archivo o lo extiende con bytes nulos hasta la nueva longitud y reasigna su espacio en disco.
        self._guardar(datos, volumen, nombre, anterior[:length].ljust(length, b'\x00'))
        return 0

    def unlink(self, ruta):
        nombre = self._nombre(ruta)
        # Impide eliminar un archivo mientras tenga algún descriptor abierto antes de liberar su entrada.
        if any(n == nombre for n, flags in self.descriptores.values()):
            raise OSError(errno.EBUSY, "Cierra el archivo antes de eliminarlo")
        self._archivo(self._cargar()[1], nombre)
        eliminar_archivo(self.imagen, nombre)
        return 0

    def flush(self, ruta, fh):
        return 0  # Cada escritura ya se guarda y sincroniza antes de responder.

    def fsync(self, ruta, datasync, fh):
        return 0

    def release(self, ruta, fh):
        self.descriptores.pop(fh, None)
        return 0

    def statfs(self, ruta):
        datos, volumen = self._cargar()
        # Calcula capacidad y espacio libre del área de datos (clusters 5..719) y entradas de directorio disponibles.
        total = volumen.clusters_totales - 1 - volumen.clusters_directorio
        usados = sum(clusters_necesarios(a.tamano, volumen.tamano_cluster) for a in volumen.archivos)
        entradas = volumen.clusters_directorio * volumen.tamano_cluster // TAMANO_ENTRADA
        return dict(f_bsize=volumen.tamano_cluster, f_frsize=volumen.tamano_cluster,
                    f_blocks=total, f_bfree=total - usados, f_bavail=total - usados,
                    f_files=entradas, f_ffree=entradas - len(volumen.archivos), f_namemax=15)

    def utimens(self, ruta, times=None):
        if ruta == '/':
            return 0
        nombre = self._nombre(ruta)
        datos, volumen = self._cargar()
        self._archivo(volumen, nombre)
        modificado = datetime.now() if times is None else datetime.fromtimestamp(times[1])
        # Actualiza únicamente el sello de fecha de modificación (bytes 38..51) en la entrada del directorio.
        for posicion, entrada in recorrer_directorio(datos, volumen.tamano_cluster, volumen.clusters_directorio):
            if entrada[:1] == b'F' and texto(entrada[1:16]) == nombre:
                datos[posicion + 38:posicion + 52] = modificado.strftime(FORMATO_FECHA).encode('ascii')
                break
        guardar_volumen(self.imagen, datos)
        return 0


# Antes de montar, comprueba Linux, las dependencias y la carpeta de destino;
# al finalizar el montaje, cierra el hilo que atiende las operaciones del disco.
def main():
    parser = argparse.ArgumentParser(description='Monta FiUnamFS 27-1 con FUSE en Linux.')
    parser.add_argument('imagen', type=Path)
    parser.add_argument('montaje', type=Path, help='Carpeta vacía existente')
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('Ejecuta este comando dentro de Ubuntu/WSL2 o Linux, no desde Python de Windows.')
    try:
        from fuse import FUSE, Operations, FuseOSError
    except (ImportError, OSError) as exc:
        parser.error(f'Faltan fusepy o libfuse: {exc}. Consulta README.md.')
    montaje = args.montaje.resolve()
    if not montaje.is_dir() or any(montaje.iterdir()):
        parser.error('El punto de montaje debe ser una carpeta vacía existente.')
    try:
        disco = DiscoFUSE(args.imagen)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    # Puente entre fusepy y DiscoFUSE: delega cada operación al trabajador y convierte OSError en FuseOSError.
    class Adaptador(Operations):
        def __call__(self, operacion, *argumentos):
            if operacion in ('init', 'destroy'):
                return None
            try:
                return disco.ejecutar(operacion, *argumentos)
            except OSError as exc:
                raise FuseOSError(exc.errno or errno.EIO) from exc

    try:
        print(f'Montando {disco.imagen} en {montaje}. Desmonta con fusermount -u "{montaje}".', flush=True)
        # Monta el volumen en primer plano, con un solo hilo receptor FUSE y sin cachés de kernel
        # para reflejar siempre el estado real procesado por el hilo trabajador.
        FUSE(Adaptador(), str(montaje), foreground=True, nothreads=True,
             default_permissions=True, attr_timeout=0, entry_timeout=0, negative_timeout=0)
    finally:
        disco.cerrar()


if __name__ == '__main__':
    main()
