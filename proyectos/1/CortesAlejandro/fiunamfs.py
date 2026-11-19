import os
import struct
import threading
from dataclasses import dataclass
from datetime import datetime

# --------------------------------------------------------------------------
# Constantes
# --------------------------------------------------------------------------
TAM_SECTOR = 512
TAM_CLUSTER = 4 * TAM_SECTOR
TAM_DISCO = 1440 * 1024              

NOMBRE_FS = b"FiUnamFS"               
VERSION_FS = b"27-1"                  

CLUSTER_DIRECTORIO = 1                
TAM_ENTRADA = 64                      
LONG_NOMBRE = 15                       

TIPO_ARCHIVO = b"F"                    
TIPO_VACIA = b"-"                      
NOMBRE_VACIO = "#" + "." * 14          
FECHA_VACIA = "0" * 14


class ErrorFiUnamFS(Exception):
    """Error esperable (imagen inválida, archivo inexistente, sin espacio)"""


def _div_techo(a, b):
    return -(-a // b)


def _ahora():
    return datetime.now().strftime("%Y%m%d%H%M%S")


# --------------------------------------------------------------------------
# Entrada del directorio
# --------------------------------------------------------------------------
@dataclass
class Entrada:
    """Representa una de las entradas de 64 bytes del directorio"""
    indice: int                  
    usada: bool                  
    nombre: str = ""
    tamano: int = 0              
    cluster_inicial: int = 0
    creacion: str = ""           
    modificacion: str = ""       

    def num_clusters(self, tam_cluster=TAM_CLUSTER):
        """Cuántos clusters ocupa el archivo en el espacio de datos"""
        return _div_techo(self.tamano, tam_cluster)


# --------------------------------------------------------------------------
# Sistema de archivos
# --------------------------------------------------------------------------
class FiUnamFS:
    """
    Todas las operaciones públicas toman un candado, de modo que varios
    hilos pueden compartir la misma instancia sin corromper la imagen, las
    operaciones se ejecutan una a la vez
    """

    def __init__(self, ruta):
        self.ruta = ruta
        self._candado = threading.RLock()
        try:
            self._archivo = open(ruta, "r+b")
        except OSError as e:
            raise ErrorFiUnamFS(f"No se pudo abrir '{ruta}': {e.strerror}") from e
        try:
            self._leer_superbloque()
        except Exception:
            self._archivo.close()
            raise

    # -- ciclo de vida -----------------------------------------------------
    def cerrar(self):
        with self._candado:
            if not self._archivo.closed:
                self._archivo.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cerrar()

    # -- superbloque -------------------------------------------------------
    def _leer_superbloque(self):
        """Lee y valida el superbloque"""
        self._archivo.seek(0, os.SEEK_END)
        tam_archivo = self._archivo.tell()
        if tam_archivo != TAM_DISCO:
            raise ErrorFiUnamFS(
                f"La imagen mide {tam_archivo} bytes; se esperaban {TAM_DISCO}")

        self._archivo.seek(0)
        sb = self._archivo.read(52)
        if sb[0:8] != NOMBRE_FS:
            raise ErrorFiUnamFS("No es un sistema de archivos FiUnamFS")
        if sb[10:14] != VERSION_FS:
            version = sb[10:14].decode("ascii", errors="replace")
            raise ErrorFiUnamFS(
                f"Versión no soportada: '{version}' "
                f"(se requiere '{VERSION_FS.decode()}').")

        self.etiqueta = sb[20:36].decode("ascii", errors="replace").rstrip(" \x00")
        self.tam_cluster = struct.unpack_from("<I", sb, 40)[0]
        self.clusters_directorio = struct.unpack_from("<I", sb, 44)[0]
        self.clusters_totales = struct.unpack_from("<I", sb, 48)[0]

        # Comprobaciones para no operar con datos absurdos
        if (self.tam_cluster == 0
                or self.clusters_directorio == 0
                or self.clusters_totales <= CLUSTER_DIRECTORIO + self.clusters_directorio
                or self.clusters_totales * self.tam_cluster > tam_archivo):
            raise ErrorFiUnamFS("El superbloque tiene valores inconsistentes")

        self.cluster_datos = CLUSTER_DIRECTORIO + self.clusters_directorio
        self.num_entradas = (self.clusters_directorio * self.tam_cluster) // TAM_ENTRADA

    # -- directorio --------------------------------------------------------
    def _leer_entradas(self):
        """Devuelve todas las entradas del directorio (usadas y libres)"""
        self._archivo.seek(CLUSTER_DIRECTORIO * self.tam_cluster)
        datos = self._archivo.read(self.num_entradas * TAM_ENTRADA)
        entradas = []
        for i in range(self.num_entradas):
            crudo = datos[i * TAM_ENTRADA:(i + 1) * TAM_ENTRADA]
            if crudo[0:1] != TIPO_ARCHIVO:
                entradas.append(Entrada(indice=i, usada=False))
                continue
            entradas.append(Entrada(
                indice=i,
                usada=True,
                nombre=crudo[1:16].decode("ascii", errors="replace").rstrip(" \x00"),
                tamano=struct.unpack_from("<I", crudo, 16)[0],
                cluster_inicial=struct.unpack_from("<I", crudo, 20)[0],
                creacion=crudo[24:38].decode("ascii", errors="replace"),
                modificacion=crudo[38:52].decode("ascii", errors="replace"),
            ))
        return entradas

    def _escribir_entrada(self, indice, crudo):
        assert len(crudo) == TAM_ENTRADA
        self._archivo.seek(CLUSTER_DIRECTORIO * self.tam_cluster + indice * TAM_ENTRADA)
        self._archivo.write(crudo)
        self._archivo.flush()

    @staticmethod
    def _construir_entrada(nombre, tamano, cluster, creacion, modificacion):
        """Arma los 64 bytes de una entrada ocupada"""
        return (TIPO_ARCHIVO
                + nombre.encode("ascii").ljust(LONG_NOMBRE, b" ")
                + struct.pack("<I", tamano)
                + struct.pack("<I", cluster)
                + creacion.encode("ascii")
                + modificacion.encode("ascii")
                + b"\x00" * 12)

    @staticmethod
    def _construir_entrada_vacia():
        """Arma los 64 bytes de una entrada libre"""
        return (TIPO_VACIA
                + NOMBRE_VACIO.encode("ascii")
                + struct.pack("<I", 0)
                + struct.pack("<I", 0)
                + FECHA_VACIA.encode("ascii")
                + FECHA_VACIA.encode("ascii")
                + b"\x00" * 12)

    @staticmethod
    def validar_nombre(nombre):
        if not nombre:
            raise ErrorFiUnamFS("El nombre del archivo está vacío")
        if len(nombre) > LONG_NOMBRE:
            raise ErrorFiUnamFS(
                f"El nombre '{nombre}' mide {len(nombre)} caracteres; "
                f"el máximo es {LONG_NOMBRE}.")
        if any(not (32 <= ord(c) <= 126) for c in nombre):
            raise ErrorFiUnamFS(
                f"El nombre '{nombre}' tiene caracteres que no son ASCII de 7 bits")
        if nombre != nombre.strip(" ") or nombre.startswith("#"):
            raise ErrorFiUnamFS(
                "El nombre no puede empezar con '#' ni tener espacios en los extremos")

    def _buscar(self, entradas, nombre):
        for e in entradas:
            if e.usada and e.nombre == nombre:
                return e
        raise ErrorFiUnamFS(f"No existe el archivo '{nombre}' en FiUnamFS")

    # -- asignación contigua ----------------------------------------------
    def _buscar_hueco(self, entradas, clusters_necesarios):
        """
        Primer ajuste: devuelve el cluster inicial del primer hueco
        contiguo con espacio suficiente, o None si no hay
        """
        ocupados = sorted(
            (e.cluster_inicial, e.cluster_inicial + e.num_clusters(self.tam_cluster))
            for e in entradas if e.usada and e.tamano > 0)
        cursor = self.cluster_datos
        for inicio, fin in ocupados:
            if inicio - cursor >= clusters_necesarios:
                return cursor
            cursor = max(cursor, fin)
        if self.clusters_totales - cursor >= clusters_necesarios:
            return cursor
        return None

    # ======================================================================
    # Operaciones públicas
    # ======================================================================
    def listar(self):
        """Lista de entradas ocupadas, en el orden del directorio"""
        with self._candado:
            return [e for e in self._leer_entradas() if e.usada]

    def espacio_libre(self):
        """Bytes libres totales (suma de huecos no implica que sean contiguos)"""
        with self._candado:
            usados = sum(e.num_clusters(self.tam_cluster)
                         for e in self._leer_entradas() if e.usada)
            return (self.clusters_totales - self.cluster_datos - usados) * self.tam_cluster

    def extraer(self, nombre, destino):
        """
        Copia el archivo nombre de FiUnamFS al archivo local destino
        """
        with self._candado:
            e = self._buscar(self._leer_entradas(), nombre)
            fin = e.cluster_inicial + e.num_clusters(self.tam_cluster)
            if e.cluster_inicial < self.cluster_datos or fin > self.clusters_totales:
                raise ErrorFiUnamFS(
                    f"La entrada de '{nombre}' apunta fuera del espacio de datos.")

            try:
                with open(destino, "wb") as salida:
                    self._archivo.seek(e.cluster_inicial * self.tam_cluster)
                    pendiente = e.tamano
                    while pendiente > 0:
                        bloque = self._archivo.read(min(self.tam_cluster, pendiente))
                        salida.write(bloque)
                        pendiente -= len(bloque)
            except OSError as err:
                raise ErrorFiUnamFS(f"No se pudo escribir '{destino}': {err.strerror}") from err
            return e.tamano

    def importar(self, origen):
        """
        Copia el archivo local origen hacia FiUnamFS
        Si ocurre un error a la mitad, el directorio no se modifica, por lo que
        la imagen sigue consistente
        """
        nombre = os.path.basename(origen)
        self.validar_nombre(nombre)
        try:
            tamano = os.path.getsize(origen)
            entrada_origen = open(origen, "rb")
        except OSError as err:
            raise ErrorFiUnamFS(f"No se pudo leer '{origen}': {err.strerror}") from err

        with entrada_origen, self._candado:
            entradas = self._leer_entradas()
            if any(e.usada and e.nombre == nombre for e in entradas):
                raise ErrorFiUnamFS(f"Ya existe un archivo llamado '{nombre}'.")

            libre = next((e for e in entradas if not e.usada), None)
            if libre is None:
                raise ErrorFiUnamFS("El directorio está lleno")

            clusters = _div_techo(tamano, self.tam_cluster)
            inicio = self._buscar_hueco(entradas, clusters)
            if inicio is None:
                raise ErrorFiUnamFS(
                    f"No hay {clusters} clusters contiguos libres para '{nombre}' "
                    f"({tamano} bytes). Elimina archivos para liberar espacio")

            #Primero los datos
            self._archivo.seek(inicio * self.tam_cluster)
            pendiente = tamano
            while pendiente > 0:
                bloque = entrada_origen.read(min(self.tam_cluster, pendiente))
                if not bloque:
                    raise ErrorFiUnamFS(f"'{origen}' cambió de tamaño durante la copia")
                self._archivo.write(bloque.ljust(self.tam_cluster, b"\x00"))
                pendiente -= len(bloque)
            self._archivo.flush()

            #y hasta el final la entrada del directorio.
            ahora = _ahora()
            self._escribir_entrada(
                libre.indice,
                self._construir_entrada(nombre, tamano, inicio, ahora, ahora))
            return nombre, tamano

    def eliminar(self, nombre):
        """Marca como libre la entrada del archivo (los datos no se borran)"""
        with self._candado:
            e = self._buscar(self._leer_entradas(), nombre)
            self._escribir_entrada(e.indice, self._construir_entrada_vacia())