"""
Estructuras del micro sistema de archivos FiUnamFS, proyecto de Sistemas
Operativos (sistop-2027-1)
Sebastián Ladrón de Guevara Castro

Este módulo sabe leer el superbloque (cluster 0) y el directorio
(clusters 1 a 4) del disco. La interfaz está en main.py.
"""

import math
import struct
from dataclasses import dataclass
from datetime import datetime

NOMBRE_FS = b'FiUnamFS'
VERSION_FS = b'27-1'

# El directorio empieza justo después del superbloque
CLUSTER_DIRECTORIO = 1

TAM_ENTRADA = 64
LARGO_NOMBRE = 15
TIPO_ARCHIVO = b'F'
# La especificación dice que las entradas vacías llevan '#..............' en
# el nombre, pero la imagen del profe usa '##############', se aceptan las dos
NOMBRE_VACIO = '#' * (LARGO_NOMBRE - 1)
NOMBRE_VACIO_ESPECIFICACION = '#' + '.' * (LARGO_NOMBRE - 1)
NOMBRES_RESERVADOS = (NOMBRE_VACIO, NOMBRE_VACIO_ESPECIFICACION)
FORMATO_FECHA = '%Y%m%d%H%M%S'

# Una entrada completa del directorio. Los enteros van en little endian (<)
# y los 12 bytes del final (12x) son el espacio reservado
FORMATO_ENTRADA = '<c15sII14s14s12x'


class ErrorFiUnamFS(Exception):
    """Problema con la imagen o con alguna operación sobre ella."""


@dataclass
class Entrada:
    """Un archivo del directorio, junto con la posición que ocupa en él."""
    indice: int
    nombre: str
    tamano: int
    cluster: int
    creado: str
    modificado: str


def formatear_fecha(fecha):
    """Convierte 'AAAAMMDDHHMMSS' a 'AAAA-MM-DD HH:MM:SS' si es válida."""
    try:
        return datetime.strptime(fecha, FORMATO_FECHA).strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return fecha


class FiUnamFS:
    def __init__(self, ruta):
        # Por ahora el programa no modifica la imagen, así que basta con abrirla
        # para lectura
        try:
            self.imagen = open(ruta, 'rb')
        except OSError as e:
            raise ErrorFiUnamFS(f'No se pudo abrir "{ruta}": {e.strerror}')
        try:
            self._leer_superbloque()
        except Exception:
            self.imagen.close()
            raise

    def cerrar(self):
        self.imagen.close()

    def _leer_superbloque(self):
        superbloque = self.imagen.read(64)

        # Antes de cualquier otra cosa se valida que sea un FiUnamFS de la
        # versión correcta, así nunca se escribe sobre un archivo ajeno
        if superbloque[0:8] != NOMBRE_FS:
            raise ErrorFiUnamFS('La imagen no es un sistema de archivos FiUnamFS')
        if superbloque[10:14] != VERSION_FS:
            version = superbloque[10:14].decode('ascii', 'replace')
            raise ErrorFiUnamFS(f'La imagen es de la versión "{version}", este programa solo maneja la 27-1')

        self.etiqueta = superbloque[20:36].decode('ascii', 'replace').strip('\x00 ')
        (self.tam_cluster,
         self.clusters_directorio,
         self.clusters_totales) = struct.unpack_from('<III', superbloque, 40)

        if self.tam_cluster == 0 or self.tam_cluster % TAM_ENTRADA != 0:
            raise ErrorFiUnamFS(f'Tamaño de cluster inválido en el superbloque ({self.tam_cluster})')

        self.primer_cluster_datos = CLUSTER_DIRECTORIO + self.clusters_directorio
        self.total_entradas = self.clusters_directorio * self.tam_cluster // TAM_ENTRADA

    # ---- Directorio ----

    def _posicion_entrada(self, indice):
        return CLUSTER_DIRECTORIO * self.tam_cluster + indice * TAM_ENTRADA

    def _leer_directorio(self):
        """Regresa todas las entradas del directorio, ocupadas o no, en crudo."""
        self.imagen.seek(self._posicion_entrada(0))
        crudo = self.imagen.read(self.total_entradas * TAM_ENTRADA)
        return [crudo[i:i + TAM_ENTRADA] for i in range(0, len(crudo), TAM_ENTRADA)]

    @staticmethod
    def _leer_nombre(campo):
        # En la imagen del profe los nombres vienen rellenos de espacios y
        # terminan con un byte nulo, se quitan los dos para quedarse con el nombre
        return campo.decode('ascii', 'replace').strip('\x00 ')

    def _entrada_libre(self, crudo):
        # Una entrada vacía se marca con '-' en el tipo y con un nombre
        # reservado, cualquiera de las dos señales basta para ignorarla
        return crudo[0:1] != TIPO_ARCHIVO or self._leer_nombre(crudo[1:16]) in NOMBRES_RESERVADOS

    def listar(self):
        """Regresa los archivos del directorio en el orden en que aparecen."""
        entradas = []
        for indice, crudo in enumerate(self._leer_directorio()):
            if self._entrada_libre(crudo):
                continue
            _, nombre, tamano, cluster, creado, modificado = struct.unpack(FORMATO_ENTRADA, crudo)
            entradas.append(Entrada(
                indice=indice,
                nombre=self._leer_nombre(nombre),
                tamano=tamano,
                cluster=cluster,
                creado=creado.decode('ascii', 'replace'),
                modificado=modificado.decode('ascii', 'replace'),
            ))
        return entradas

    # ---- Espacio ----

    def clusters_de(self, tamano):
        return math.ceil(tamano / self.tam_cluster)

    def espacio_libre(self):
        """Bytes libres en el área de datos, sin importar si están contiguos."""
        ocupados = sum(self.clusters_de(e.tamano) for e in self.listar())
        libres = self.clusters_totales - self.primer_cluster_datos - ocupados
        return max(libres, 0) * self.tam_cluster
