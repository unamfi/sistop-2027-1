import sys
import signal
import stat
import errno
import time
import threading
import queue
from datetime import datetime

# ojo: fusepy tambien se llama fuse pero no tiene Fuse, por eso truena aqui
try:
    import fuse
    from fuse import Fuse
except ImportError:
    print("Error: no se encontró python-fuse.")
    print("Instálalo con:  sudo apt install python3-fuse")
    print("(ver la sección 'Entorno y dependencias' del README)")
    sys.exit(1)

import fiunamfs

fuse.fuse_python_api = (0, 2)


def fecha_a_segundos(fecha):
    try:
        return datetime.strptime(fecha, "%Y%m%d%H%M%S").timestamp()
    except ValueError:
        return 0


def hilo_bitacora(cola):
    # este hilo saca los mensajes de la cola y los imprime
    # (los hilos de FUSE son los que meten los mensajes)
    while True:
        mensaje = cola.get()
        # None es la señal para terminar (la manda el main al desmontar)
        if mensaje == None:
            break
        print("[bitácora]", mensaje)


class FiUnamFS_FUSE(Fuse):

    def __init__(self, ruta_imagen, cola_bitacora, *args, **kw):
        Fuse.__init__(self, *args, **kw)

        self.ruta = ruta_imagen
        self.sb = fiunamfs.leer_superbloque(ruta_imagen)
        self.cola = cola_bitacora

        # FUSE usa un hilo por cada peticion, sin el candado dos cp al mismo
        # tiempo podrian agarrar el mismo hueco y uno pisaria al otro
        self.candado = threading.Lock()

        # aqui se guardan los archivos que se estan escribiendo. FUSE los manda
        # en pedazos y como tiene que ser contiguo no se pueden guardar hasta
        # saber cuanto miden, entonces se juntan aqui y se guardan al cerrarlos
        self.pendientes = {}

    def registrar(self, mensaje):
        hora = datetime.now().strftime("%H:%M:%S")
        hilo = str(threading.get_native_id())
        self.cola.put(hora + " (hilo " + hilo + ") " + mensaje)

    def nombre_de(self, path):
        return path[1:]

    def getattr(self, path):
        st = fuse.Stat()
        ahora = time.time()

        if path == "/":
            st.st_mode = stat.S_IFDIR | 0o755
            st.st_nlink = 2
            st.st_ctime = ahora
            st.st_mtime = ahora
            st.st_atime = ahora
            return st

        nombre = self.nombre_de(path)

        with self.candado:
            # un archivo que se esta copiando todavia no esta en la imagen,
            # pero cp necesita verlo mientras lo escribe
            if nombre in self.pendientes:
                st.st_mode = stat.S_IFREG | 0o644
                st.st_nlink = 1
                st.st_size = len(self.pendientes[nombre])
                st.st_ctime = ahora
                st.st_mtime = ahora
                st.st_atime = ahora
                return st

            entrada = fiunamfs.buscar_archivo(self.ruta, self.sb, nombre)

        if entrada == None:
            return -errno.ENOENT

        st.st_mode = stat.S_IFREG | 0o644
        st.st_nlink = 1
        st.st_size = entrada['tamano']
        st.st_ctime = fecha_a_segundos(entrada['fecha_creacion'])
        st.st_mtime = fecha_a_segundos(entrada['fecha_modificacion'])
        st.st_atime = st.st_mtime
        return st

    def readdir(self, path, offset):
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

        for nombre in lista:
            yield fuse.Direntry(nombre)

    def open(self, path, flags):
        nombre = self.nombre_de(path)
        with self.candado:
            if nombre in self.pendientes:
                return 0
            if fiunamfs.buscar_archivo(self.ruta, self.sb, nombre) == None:
                return -errno.ENOENT
        return 0

    def read(self, path, size, offset):
        nombre = self.nombre_de(path)

        with self.candado:
            if nombre in self.pendientes:
                contenido = self.pendientes[nombre]
            else:
                contenido = fiunamfs.leer_archivo(self.ruta, self.sb, nombre)

        if contenido == None:
            return -errno.ENOENT

        if offset == 0:
            self.registrar("leer " + nombre + " (" + str(len(contenido)) + " bytes)")

        return contenido[offset:offset + size]

    def create(self, path, flags, mode):
        nombre = self.nombre_de(path)

        if len(nombre) > 15:
            return -errno.ENAMETOOLONG
        if not fiunamfs.validar_nombre(nombre):
            return -errno.EINVAL

        with self.candado:
            if fiunamfs.buscar_entrada_libre(self.ruta, self.sb) == -1:
                return -errno.ENOSPC
            self.pendientes[nombre] = b''

        self.registrar("crear " + nombre)
        return 0

    def cargar_pendiente(self, nombre):
        # si se escribe en un archivo que ya existe primero se carga lo que tenia
        # (hay que llamarla con el candado ya tomado)
        if nombre not in self.pendientes:
            contenido = fiunamfs.leer_archivo(self.ruta, self.sb, nombre)
            if contenido == None:
                return False
            self.pendientes[nombre] = contenido
        return True

    def write(self, path, buf, offset):
        nombre = self.nombre_de(path)

        with self.candado:
            if not self.cargar_pendiente(nombre):
                return -errno.ENOENT
            contenido = self.pendientes[nombre]
            if offset > len(contenido):
                contenido = contenido + b'\x00' * (offset - len(contenido))
            # se pone el pedazo nuevo en su lugar
            contenido = contenido[:offset] + buf + contenido[offset + len(buf):]
            self.pendientes[nombre] = contenido

        return len(buf)

    def truncate(self, path, size):
        nombre = self.nombre_de(path)

        with self.candado:
            if not self.cargar_pendiente(nombre):
                return -errno.ENOENT
            contenido = self.pendientes[nombre]
            if size < len(contenido):
                contenido = contenido[:size]
            else:
                contenido = contenido + b'\x00' * (size - len(contenido))
            self.pendientes[nombre] = contenido

        return 0

    def flush(self, path):
        nombre = self.nombre_de(path)

        with self.candado:
            if nombre not in self.pendientes:
                return 0

            contenido = self.pendientes[nombre]
            del self.pendientes[nombre]

            # si ya existia se borra y se vuelve a escribir completo porque
            # con el tamaño nuevo a lo mejor ya no cabe en el mismo lugar
            contenido_anterior = None
            if fiunamfs.buscar_archivo(self.ruta, self.sb, nombre) != None:
                contenido_anterior = fiunamfs.leer_archivo(self.ruta, self.sb, nombre)
                fiunamfs.eliminar_archivo(self.ruta, self.sb, nombre)

            guardado = fiunamfs.escribir_archivo(self.ruta, self.sb, nombre, contenido)

            # si no cupo se vuelve a poner el viejo para no perderlo
            if not guardado and contenido_anterior != None:
                fiunamfs.escribir_archivo(self.ruta, self.sb, nombre, contenido_anterior)

        if not guardado:
            self.registrar("ERROR: no cupo " + nombre)
            return -errno.ENOSPC

        self.registrar("guardar " + nombre + " (" + str(len(contenido)) + " bytes)")
        return 0

    def release(self, path, flags):
        return 0

    def unlink(self, path):
        nombre = self.nombre_de(path)

        with self.candado:
            borrado = fiunamfs.eliminar_archivo(self.ruta, self.sb, nombre)

        if not borrado:
            return -errno.ENOENT

        self.registrar("eliminar " + nombre)
        return 0

    def statfs(self):
        tamano_cluster = self.sb['tamano_cluster']
        clusters_datos = self.sb['clusters_totales'] - 1 - self.sb['clusters_directorio']

        with self.candado:
            archivos = fiunamfs.leer_directorio(self.ruta, self.sb)

        usados = 0
        for entrada in archivos:
            usados = usados + fiunamfs.clusters_que_ocupa(entrada['tamano'], tamano_cluster)

        sv = fuse.StatVfs()
        sv.f_bsize = tamano_cluster
        sv.f_frsize = tamano_cluster
        sv.f_blocks = clusters_datos
        sv.f_bfree = clusters_datos - usados
        sv.f_bavail = clusters_datos - usados
        sv.f_namemax = 15
        return sv

    def chmod(self, path, mode):
        return 0

    def chown(self, path, uid, gid):
        return 0

    def utimens(self, path, ts_acc, ts_mod):
        return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python3 fiunamfs_fuse.py <imagen.img> <carpeta_de_montaje>")
        sys.exit(1)

    ruta_imagen = sys.argv[1]
    punto_montaje = sys.argv[2]

    # se quita la imagen de los argumentos porque FUSE no la entiende,
    # lo demas (la carpeta) si lo procesa FUSE
    del sys.argv[1]

    # -f es para que corra en primer plano, si no el hilo de la bitacora se muere
    if '-f' not in sys.argv:
        sys.argv.append('-f')

    sb = fiunamfs.leer_superbloque(ruta_imagen)
    if not fiunamfs.validar_superbloque(sb):
        print("No se montó la imagen para no dañarla")
        sys.exit(1)

    cola = queue.Queue()
    bitacora = threading.Thread(target=hilo_bitacora, args=(cola,), name="bitacora")
    bitacora.start()

    print("Montando", ruta_imagen, "en", punto_montaje)
    print("Para desmontar: fusermount -u", punto_montaje, "(o Ctrl+C aquí)")

    servidor = FiUnamFS_FUSE(ruta_imagen, cola,
                             version="%prog " + fuse.__version__,
                             usage="python3 fiunamfs_fuse.py <imagen.img> <carpeta_de_montaje>",
                             dash_s_do='setsingle')
    servidor.parse(errex=1)

    # sin esto Ctrl+C no desmontaba porque python se quedaba con la señal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    servidor.main()

    cola.put(None)
    bitacora.join()
    print("Imagen desmontada")
