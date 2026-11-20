# fiunamfs_fuse.py
# monta una imagen de FiUnamFS en una carpeta usando FUSE (python-fuse),
# para poder usarla con ls, cp, rm, etc. como si fuera una carpeta normal
#
# uso: python3 fiunamfs_fuse.py <imagen.img> <carpeta_de_montaje>
#
# hilos que hay:
#  - los de FUSE: python-fuse atiende cada operacion en un hilo distinto
#  - el principal: monta la imagen y arranca a los demas
#  - el de la bitacora: imprime lo que van haciendo los hilos de FUSE
# los hilos de FUSE se sincronizan con un Lock (self.candado) y le avisan
# a la bitacora lo que hacen por medio de una Queue

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

# las funciones que leen y escriben la imagen
import fiunamfs

# python-fuse pide decir que version de su API se usa, la 0.2 es la actual
fuse.fuse_python_api = (0, 2)


# convierte '20261105163124' a segundos desde 1970, que es lo que pide FUSE
# para las fechas (las que muestra ls -l)
def fecha_a_segundos(fecha):
    try:
        return datetime.strptime(fecha, "%Y%m%d%H%M%S").timestamp()
    except ValueError:
        # si la fecha viene mal se pone 0 en lugar de tronar
        return 0


# lo que hace el hilo de la bitacora
def hilo_bitacora(cola):
    # este hilo saca los mensajes de la cola y los imprime
    # (los hilos de FUSE son los que meten los mensajes)
    while True:
        # get() se queda esperando hasta que alguien meta un mensaje
        mensaje = cola.get()
        # None es la señal para terminar (la manda el main al desmontar)
        if mensaje == None:
            break
        print("[bitácora]", mensaje)


# la clase hereda de Fuse; cada metodo es una operacion que Linux le
# puede pedir al sistema de archivos (listar, leer, escribir, borrar...)
# los errores se regresan como -errno.ALGO, asi lo pide python-fuse
class FiUnamFS_FUSE(Fuse):

    def __init__(self, ruta_imagen, cola_bitacora, *args, **kw):
        # primero se inicializa la parte de Fuse con sus parametros
        Fuse.__init__(self, *args, **kw)

        self.ruta = ruta_imagen
        # el superbloque se lee una sola vez al principio
        self.sb = fiunamfs.leer_superbloque(ruta_imagen)
        self.cola = cola_bitacora

        # FUSE usa un hilo por cada peticion, sin el candado dos cp al mismo
        # tiempo podrian agarrar el mismo hueco y uno pisaria al otro
        self.candado = threading.Lock()

        # aqui se guardan los archivos que se estan escribiendo. FUSE los manda
        # en pedazos y como tiene que ser contiguo no se pueden guardar hasta
        # saber cuanto miden, entonces se juntan aqui y se guardan al cerrarlos
        # es un diccionario: nombre -> contenido (bytes)
        self.pendientes = {}

    # manda un mensaje a la bitacora con la hora y el hilo que lo hizo
    def registrar(self, mensaje):
        hora = datetime.now().strftime("%H:%M:%S")
        # el id que le da Linux al hilo, asi se ve que son hilos distintos
        hilo = str(threading.get_native_id())
        # put() mete el mensaje en la cola, el hilo bitacora lo saca
        self.cola.put(hora + " (hilo " + hilo + ") " + mensaje)

    # FUSE manda rutas como '/logo.png', se le quita la diagonal
    # (no hay subdirectorios, asi que el nombre es todo lo demas)
    def nombre_de(self, path):
        return path[1:]

    # getattr: Linux pregunta "que es esto y cuanto mide" (lo usan ls -l, cp, etc.)
    def getattr(self, path):
        st = fuse.Stat()
        ahora = time.time()

        # "/" es la carpeta montada, se dice que es un directorio
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

        # S_IFREG = archivo normal; 0o644 son los permisos (rw-r--r--)
        # FiUnamFS no guarda permisos, se ponen fijos
        st.st_mode = stat.S_IFREG | 0o644
        st.st_nlink = 1
        st.st_size = entrada['tamano']
        st.st_ctime = fecha_a_segundos(entrada['fecha_creacion'])
        st.st_mtime = fecha_a_segundos(entrada['fecha_modificacion'])
        st.st_atime = st.st_mtime
        return st

    # readdir: Linux pide la lista de archivos (ls) - operacion 1 del proyecto
    def readdir(self, path, offset):
        with self.candado:
            archivos = fiunamfs.leer_directorio(self.ruta, self.sb)
            nombres_pendientes = list(self.pendientes.keys())

        # '.' y '..' siempre van en cualquier directorio
        lista = ['.', '..']
        for entrada in archivos:
            lista.append(entrada['nombre'])
        # tambien los que se estan copiando en este momento
        for nombre in nombres_pendientes:
            if nombre not in lista:
                lista.append(nombre)

        self.registrar("listar directorio (" + str(len(archivos)) + " archivos)")

        # python-fuse pide regresar los nombres uno por uno con yield
        for nombre in lista:
            yield fuse.Direntry(nombre)

    # open: se llama antes de leer o escribir, solo se revisa que exista
    def open(self, path, flags):
        nombre = self.nombre_de(path)
        with self.candado:
            if nombre in self.pendientes:
                return 0
            if fiunamfs.buscar_archivo(self.ruta, self.sb, nombre) == None:
                return -errno.ENOENT
        return 0

    # read: Linux pide 'size' bytes desde 'offset' - operacion 2 del proyecto
    # (cp desde la carpeta montada hacia la computadora)
    def read(self, path, size, offset):
        nombre = self.nombre_de(path)

        with self.candado:
            if nombre in self.pendientes:
                contenido = self.pendientes[nombre]
            else:
                contenido = fiunamfs.leer_archivo(self.ruta, self.sb, nombre)

        if contenido == None:
            return -errno.ENOENT

        # cp lee en varios pedazos, solo se registra el primero para no llenar la bitacora
        if offset == 0:
            self.registrar("leer " + nombre + " (" + str(len(contenido)) + " bytes)")

        # se regresa solo el pedazo que se pidio
        return contenido[offset:offset + size]

    # create: se llama cuando se crea un archivo nuevo (cp hacia la carpeta)
    # todavia no se escribe nada en la imagen, solo se aparta en pendientes
    def create(self, path, flags, mode):
        nombre = self.nombre_de(path)

        if len(nombre) > 15:
            return -errno.ENAMETOOLONG
        if not fiunamfs.validar_nombre(nombre):
            return -errno.EINVAL

        with self.candado:
            # si el directorio esta lleno se avisa desde ahorita
            if fiunamfs.buscar_entrada_libre(self.ruta, self.sb) == -1:
                return -errno.ENOSPC
            self.pendientes[nombre] = b''

        self.registrar("crear " + nombre)
        return 0

    # no es de FUSE, es una ayuda para write y truncate
    def cargar_pendiente(self, nombre):
        # si se escribe en un archivo que ya existe primero se carga lo que tenia
        # (hay que llamarla con el candado ya tomado)
        if nombre not in self.pendientes:
            contenido = fiunamfs.leer_archivo(self.ruta, self.sb, nombre)
            if contenido == None:
                return False
            self.pendientes[nombre] = contenido
        return True

    # write: llega un pedazo 'buf' que va en la posicion 'offset' del archivo
    # (operacion 3 del proyecto: cp hacia la carpeta montada)
    def write(self, path, buf, offset):
        nombre = self.nombre_de(path)

        with self.candado:
            if not self.cargar_pendiente(nombre):
                return -errno.ENOENT
            contenido = self.pendientes[nombre]
            # si el pedazo empieza mas adelante del final, se rellena con ceros
            if offset > len(contenido):
                contenido = contenido + b'\x00' * (offset - len(contenido))
            # se pone el pedazo nuevo en su lugar
            # (lo de antes + el pedazo + lo que hubiera despues)
            contenido = contenido[:offset] + buf + contenido[offset + len(buf):]
            self.pendientes[nombre] = contenido

        # FUSE necesita saber cuantos bytes se escribieron
        return len(buf)

    # truncate: cambia el tamaño de un archivo
    # (por ejemplo cuando se sobrescribe un archivo, primero lo deja en 0)
    def truncate(self, path, size):
        nombre = self.nombre_de(path)

        with self.candado:
            if not self.cargar_pendiente(nombre):
                return -errno.ENOENT
            contenido = self.pendientes[nombre]
            if size < len(contenido):
                # se corta
                contenido = contenido[:size]
            else:
                # se alarga con ceros
                contenido = contenido + b'\x00' * (size - len(contenido))
            self.pendientes[nombre] = contenido

        return 0

    # flush: se llama al cerrar el archivo; aqui es donde de verdad se guarda
    # en la imagen todo lo que se junto en pendientes
    def flush(self, path):
        nombre = self.nombre_de(path)

        with self.candado:
            # si no hay nada pendiente (por ejemplo solo se leyo) no se hace nada
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
            # asi cp muestra "No space left on device"
            return -errno.ENOSPC

        self.registrar("guardar " + nombre + " (" + str(len(contenido)) + " bytes)")
        return 0

    # release: ultimo aviso de que se cerro el archivo; ya se guardo en flush
    def release(self, path, flags):
        return 0

    # unlink: borrar un archivo (rm) - operacion 4 del proyecto
    def unlink(self, path):
        nombre = self.nombre_de(path)

        with self.candado:
            borrado = fiunamfs.eliminar_archivo(self.ruta, self.sb, nombre)

        if not borrado:
            return -errno.ENOENT

        self.registrar("eliminar " + nombre)
        return 0

    # statfs: espacio total, usado y libre (lo que muestra df)
    def statfs(self):
        tamano_cluster = self.sb['tamano_cluster']
        # clusters de datos = todos - superbloque (1) - directorio (4)
        clusters_datos = self.sb['clusters_totales'] - 1 - self.sb['clusters_directorio']

        with self.candado:
            archivos = fiunamfs.leer_directorio(self.ruta, self.sb)

        # se suman los clusters que usa cada archivo
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

    # FiUnamFS no guarda permisos, dueños ni fechas de acceso, pero cp a veces
    # intenta cambiarlos; se regresa 0 (todo bien) para que no marque error
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

    # antes de montar se revisa que la imagen sea valida
    sb = fiunamfs.leer_superbloque(ruta_imagen)
    if not fiunamfs.validar_superbloque(sb):
        print("No se montó la imagen para no dañarla")
        sys.exit(1)

    # la cola por donde los hilos de FUSE le mandan mensajes a la bitacora
    cola = queue.Queue()
    bitacora = threading.Thread(target=hilo_bitacora, args=(cola,), name="bitacora")
    bitacora.start()

    print("Montando", ruta_imagen, "en", punto_montaje)
    print("Para desmontar: fusermount -u", punto_montaje, "(o Ctrl+C aquí)")

    # version, usage y dash_s_do son parametros de python-fuse
    # (dash_s_do='setsingle' es lo que trae su ejemplo)
    servidor = FiUnamFS_FUSE(ruta_imagen, cola,
                             version="%prog " + fuse.__version__,
                             usage="python3 fiunamfs_fuse.py <imagen.img> <carpeta_de_montaje>",
                             dash_s_do='setsingle')
    # parse lee los argumentos que quedan (la carpeta y el -f)
    servidor.parse(errex=1)

    # sin esto Ctrl+C no desmontaba porque python se quedaba con la señal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # aqui se queda el programa mientras la imagen esta montada,
    # main() regresa hasta que se desmonta
    servidor.main()

    # ya se desmonto: se le avisa a la bitacora que termine y se espera a que acabe
    cola.put(None)
    bitacora.join()
    print("Imagen desmontada")
