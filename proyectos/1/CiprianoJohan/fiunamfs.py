#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fiunamfs.py — Núcleo del micro sistema de archivos FiUnamFS (versión 27-1)

Proyecto 1 · Sistemas Operativos 2027-1 · Facultad de Ingeniería, UNAM
Autor: Cipriano Amador Johan Tadeo

Este módulo concentra todo lo que depende de la especificación de FiUnamFS:
la geometría del «diskette», la disposición del superbloque y del
directorio, y las conversiones de enteros de 32 bits little endian.
"""

import os
import struct
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# Geometría del dispositivo
# ---------------------------------------------------------------------------
TAM_SECTOR = 512
SECTORES_POR_CLUSTER = 4
TAM_CLUSTER = TAM_SECTOR * SECTORES_POR_CLUSTER        # 2048 bytes
TAM_DISCO = 1440 * 1024                                # un diskette de 1440 KB
TOTAL_CLUSTERS = TAM_DISCO // TAM_CLUSTER              # 720 clusters

# ---------------------------------------------------------------------------
# Superbloque (cluster #0): (inicio, fin) de cada campo, fin exclusivo
# ---------------------------------------------------------------------------
SB_NOMBRE = (0, 8)            # "FiUnamFS"
SB_VERSION = (10, 14)         # "27-1" (cadena, no número)
SB_ETIQUETA = (20, 36)        # etiqueta del volumen
SB_TAM_CLUSTER = (40, 44)     # tamaño del cluster en bytes
SB_CLUSTERS_DIR = (44, 48)    # clusters que ocupa el directorio
SB_CLUSTERS_TOTAL = (48, 52)  # clusters de la unidad completa

NOMBRE_FS = b"FiUnamFS"
VERSION_FS = b"27-1"

# ---------------------------------------------------------------------------
# Directorio: clusters 1 a 4, entradas de 64 bytes
# ---------------------------------------------------------------------------
CLUSTER_INICIO_DIR = 1
CLUSTERS_DIR = 4
TAM_ENTRADA = 64
ENTRADAS_DIR = CLUSTERS_DIR * TAM_CLUSTER // TAM_ENTRADA   # 128 entradas

ENT_TIPO = (0, 1)             # 'F' archivo, '-' entrada vacía
ENT_NOMBRE = (1, 16)          # 15 caracteres ASCII
ENT_TAMANO = (16, 20)         # tamaño en bytes
ENT_CLUSTER = (20, 24)        # cluster inicial (asignación contigua)
ENT_CREACION = (24, 38)       # AAAAMMDDHHMMSS
ENT_MODIFICACION = (38, 52)   # AAAAMMDDHHMMSS
# bytes 52–63: sin uso

TIPO_ARCHIVO = b"F"
TIPO_VACIO = b"-"
NOMBRE_VACIO = b"#" + b"." * 14          # "#.............." (15 bytes)
LONG_MAX_NOMBRE = ENT_NOMBRE[1] - ENT_NOMBRE[0]
FORMATO_FECHA = "%Y%m%d%H%M%S"

# Primer cluster disponible para datos: justo después del directorio
CLUSTER_INICIO_DATOS = CLUSTER_INICIO_DIR + CLUSTERS_DIR    # cluster 5


# ---------------------------------------------------------------------------
# Conversión de enteros (32 bits, little endian)
# ---------------------------------------------------------------------------
def a_entero(datos):
    """Convierte 4 bytes little endian a entero sin signo."""
    return struct.unpack("<I", datos)[0]


def de_entero(valor):
    """Convierte un entero sin signo a 4 bytes little endian."""
    return struct.pack("<I", valor)


def campo(bloque, rango):
    """Extrae del bloque los bytes indicados por un rango (inicio, fin)."""
    return bloque[rango[0]:rango[1]]


def a_texto(datos):
    """Decodifica una cadena ASCII de disco, sin el relleno de nulos ni espacios."""
    return datos.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip()


class ErrorFiUnamFS(Exception):
    """Error al operar sobre una imagen que no es FiUnamFS válida."""


# ---------------------------------------------------------------------------
# Superbloque
# ---------------------------------------------------------------------------
class Superbloque:
    """Información del volumen almacenada en el cluster #0."""

    def __init__(self, bloque):
        self.nombre = campo(bloque, SB_NOMBRE)
        self.version = campo(bloque, SB_VERSION)
        self.etiqueta = a_texto(campo(bloque, SB_ETIQUETA))
        self.tam_cluster = a_entero(campo(bloque, SB_TAM_CLUSTER))
        self.clusters_dir = a_entero(campo(bloque, SB_CLUSTERS_DIR))
        self.clusters_total = a_entero(campo(bloque, SB_CLUSTERS_TOTAL))

    def validar(self):
        """Rechaza cualquier imagen que no sea FiUnamFS 27-1, para no corromperla."""
        if self.nombre != NOMBRE_FS:
            raise ErrorFiUnamFS(
                f"no es un sistema FiUnamFS (identificador: {self.nombre!r})")
        if self.version != VERSION_FS:
            raise ErrorFiUnamFS(
                f"versión {self.version!r} no soportada; se requiere 27-1")
        if self.tam_cluster == 0 or self.clusters_dir == 0:
            raise ErrorFiUnamFS("superbloque con geometría inválida")

    def __str__(self):
        return (f"Volumen '{self.etiqueta}' · FiUnamFS {VERSION_FS.decode()} · "
                f"cluster de {self.tam_cluster} B · "
                f"directorio de {self.clusters_dir} clusters · "
                f"{self.clusters_total} clusters en total")


# ---------------------------------------------------------------------------
# Entradas del directorio
# ---------------------------------------------------------------------------
class EntradaDirectorio:
    """Una entrada de 64 bytes del directorio plano.

    `indice` es su posición dentro del directorio; se necesita después para
    reescribir la entrada al copiar o eliminar archivos.
    """

    def __init__(self, indice, datos):
        self.indice = indice
        self.tipo = campo(datos, ENT_TIPO)
        self.nombre_crudo = campo(datos, ENT_NOMBRE)
        self.nombre = a_texto(self.nombre_crudo)
        self.tamano = a_entero(campo(datos, ENT_TAMANO))
        self.cluster = a_entero(campo(datos, ENT_CLUSTER))
        self.creacion = a_texto(campo(datos, ENT_CREACION))
        self.modificacion = a_texto(campo(datos, ENT_MODIFICACION))

    @property
    def vacia(self):
        """Una entrada está libre si no es tipo 'F' o lleva el nombre reservado."""
        return self.tipo != TIPO_ARCHIVO or self.nombre_crudo == NOMBRE_VACIO

    def clusters_ocupados(self, tam_cluster):
        """Número de clusters que usa el archivo (al menos 1, aunque esté vacío)."""
        return max(1, -(-self.tamano // tam_cluster))   # división hacia arriba


def nombre_local(nombre):
    """Adapta un nombre de FiUnamFS para el sistema local: reemplaza los
    caracteres que Windows no admite en nombres de archivo."""
    return "".join("_" if c in '<>:"/\\|?*' else c for c in nombre) or "sin_nombre"


def formatear_fecha(fecha):
    """Convierte AAAAMMDDHHMMSS a 'AAAA-MM-DD HH:MM:SS'; si no es válida, la deja tal cual."""
    try:
        return datetime.strptime(fecha, FORMATO_FECHA).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return fecha or "-"


# ---------------------------------------------------------------------------
# Acceso a la imagen
# ---------------------------------------------------------------------------
class FiUnamFS:
    """Imagen de FiUnamFS abierta para lectura y escritura.

    La geometría se toma del superbloque y no de las constantes, para
    respetar lo que diga cada volumen.
    """

    def __init__(self, ruta):
        self.ruta = ruta
        self.archivo = open(ruta, "r+b")
        try:
            self.superbloque = Superbloque(self.archivo.read(TAM_CLUSTER))
            self.superbloque.validar()
        except Exception:
            self.archivo.close()
            raise
        self.tam_cluster = self.superbloque.tam_cluster

    def leer_clusters(self, inicio, cantidad=1):
        """Lee `cantidad` clusters consecutivos a partir de `inicio`."""
        self.archivo.seek(inicio * self.tam_cluster)
        return self.archivo.read(cantidad * self.tam_cluster)

    def leer_directorio(self):
        """Devuelve todas las entradas del directorio, libres u ocupadas."""
        datos = self.leer_clusters(CLUSTER_INICIO_DIR, self.superbloque.clusters_dir)
        return [EntradaDirectorio(i, datos[i * TAM_ENTRADA:(i + 1) * TAM_ENTRADA])
                for i in range(len(datos) // TAM_ENTRADA)]

    def listar(self):
        """Archivos presentes en el volumen, ordenados por nombre."""
        archivos = [e for e in self.leer_directorio() if not e.vacia]
        return sorted(archivos, key=lambda e: e.nombre)

    def buscar(self, nombre):
        """Devuelve la entrada del archivo con ese nombre, o None si no existe."""
        for entrada in self.listar():
            if entrada.nombre == nombre:
                return entrada
        return None

    def leer_archivo(self, entrada):
        """Contenido de un archivo: al ser asignación contigua, basta con leer
        `tamano` bytes a partir de su cluster inicial."""
        fin = entrada.cluster * self.tam_cluster + entrada.tamano
        if entrada.cluster < CLUSTER_INICIO_DATOS or fin > self.superbloque.clusters_total * self.tam_cluster:
            raise ErrorFiUnamFS(f"'{entrada.nombre}' apunta fuera del área de datos")
        self.archivo.seek(entrada.cluster * self.tam_cluster)
        return self.archivo.read(entrada.tamano)

    def extraer(self, nombre, destino="."):
        """Copia un archivo de FiUnamFS al sistema local y devuelve la ruta creada.

        Si `destino` es un directorio, el archivo se guarda ahí con su mismo nombre.
        """
        entrada = self.buscar(nombre)
        if entrada is None:
            raise ErrorFiUnamFS(f"no existe '{nombre}' en el volumen")
        if os.path.isdir(destino):
            destino = os.path.join(destino, nombre_local(entrada.nombre))
        with open(destino, "wb") as salida:
            salida.write(self.leer_archivo(entrada))
        return destino

    def cerrar(self):
        self.archivo.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cerrar()


def formatear(ruta, etiqueta="Johan FiUnamFS"):
    """Crea una imagen vacía de FiUnamFS 27-1 (útil para pruebas)."""
    superbloque = bytearray(TAM_CLUSTER)
    superbloque[SB_NOMBRE[0]:SB_NOMBRE[1]] = NOMBRE_FS
    superbloque[SB_VERSION[0]:SB_VERSION[1]] = VERSION_FS
    etiqueta_bytes = etiqueta.encode("ascii")[:SB_ETIQUETA[1] - SB_ETIQUETA[0]]
    superbloque[SB_ETIQUETA[0]:SB_ETIQUETA[0] + len(etiqueta_bytes)] = etiqueta_bytes
    superbloque[SB_TAM_CLUSTER[0]:SB_TAM_CLUSTER[1]] = de_entero(TAM_CLUSTER)
    superbloque[SB_CLUSTERS_DIR[0]:SB_CLUSTERS_DIR[1]] = de_entero(CLUSTERS_DIR)
    superbloque[SB_CLUSTERS_TOTAL[0]:SB_CLUSTERS_TOTAL[1]] = de_entero(TOTAL_CLUSTERS)

    # Toda entrada del directorio arranca marcada como vacía
    entrada_vacia = bytearray(TAM_ENTRADA)
    entrada_vacia[ENT_TIPO[0]:ENT_TIPO[1]] = TIPO_VACIO
    entrada_vacia[ENT_NOMBRE[0]:ENT_NOMBRE[1]] = NOMBRE_VACIO
    directorio = bytes(entrada_vacia) * ENTRADAS_DIR

    with open(ruta, "wb") as imagen:
        imagen.write(superbloque)
        imagen.write(directorio)
        imagen.write(bytes(TAM_DISCO - len(superbloque) - len(directorio)))


def imprimir_listado(fs):
    """Muestra el contenido del volumen en forma de tabla."""
    print(fs.superbloque)
    archivos = fs.listar()
    print(f"\n{'Nombre':<16} {'Tamaño':>9} {'Cluster':>7}  {'Creación':<19}  Modificación")
    print("=" * 78)
    for e in archivos:
        print(f"{e.nombre:<16} {e.tamano:>9} {e.cluster:>7}  "
              f"{formatear_fecha(e.creacion):<19}  {formatear_fecha(e.modificacion)}")
    print(f"\n{len(archivos)} archivo(s)")


if __name__ == "__main__":
    # Modo de prueba mientras se construye la interfaz:
    #   fiunamfs.py <imagen>                       lista el volumen
    #   fiunamfs.py <imagen> extraer <nombre> [destino]
    if len(sys.argv) < 2:
        print(f"Uso: {sys.argv[0]} <imagen.img> [extraer <nombre> [destino]]",
              file=sys.stderr)
        sys.exit(1)
    try:
        with FiUnamFS(sys.argv[1]) as volumen:
            if len(sys.argv) >= 4 and sys.argv[2] == "extraer":
                destino = sys.argv[4] if len(sys.argv) > 4 else "."
                print(f"Copiado a {volumen.extraer(sys.argv[3], destino)}")
            else:
                imprimir_listado(volumen)
    except (OSError, ErrorFiUnamFS) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(2)
