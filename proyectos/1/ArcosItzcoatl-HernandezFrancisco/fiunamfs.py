"""Lectura y validación del formato FiUnamFS 27-1 (fase 1)."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import struct


TAMANIO_DISCO = 1440 * 1024
TAMANIO_CLUSTER = 512 * 4
CLUSTERS_DIRECTORIO = 4
CLUSTERS_TOTALES = TAMANIO_DISCO // TAMANIO_CLUSTER
TAMANIO_ENTRADA = 64
PRIMER_CLUSTER_DATOS = 1 + CLUSTERS_DIRECTORIO
MARCA_LIBRE = b"#.............."


class ErrorFiUnamFS(ValueError):
    """La imagen no cumple las reglas del formato FiUnamFS 27-1."""


@dataclass(frozen=True)
class Superbloque:
    etiqueta: str
    tamanio_cluster: int
    clusters_directorio: int
    clusters_totales: int


@dataclass(frozen=True)
class Archivo:
    nombre: str
    tamanio: int
    cluster_inicial: int
    creacion: str
    modificacion: str
    indice_directorio: int


class FiUnamFS:
    """Inspecciona una imagen de disco sin modificarla."""

    def __init__(self, ruta: str | Path):
        self.ruta = Path(ruta)

    def leer_superbloque(self) -> Superbloque:
        """Verifica identidad, versión, geometría y tamaño del disco."""
        if not self.ruta.is_file():
            raise ErrorFiUnamFS(f"No existe la imagen: {self.ruta}")
        if self.ruta.stat().st_size != TAMANIO_DISCO:
            raise ErrorFiUnamFS("La imagen debe medir exactamente 1,474,560 bytes")

        with self.ruta.open("rb") as imagen:
            bloque = imagen.read(TAMANIO_CLUSTER)

        if bloque[0:8] != b"FiUnamFS":
            raise ErrorFiUnamFS("Firma incorrecta: no es un disco FiUnamFS")
        if bloque[10:14] != b"27-1":
            raise ErrorFiUnamFS("Versión incompatible: se requiere 27-1")

        etiqueta = bloque[20:36].rstrip(b"\x00 ").decode("latin-1")
        cluster, directorio, total = struct.unpack_from("<III", bloque, 40)
        if (cluster, directorio, total) != (
            TAMANIO_CLUSTER, CLUSTERS_DIRECTORIO, CLUSTERS_TOTALES
        ):
            raise ErrorFiUnamFS("La geometría del disco no coincide con la especificación")

        return Superbloque(etiqueta, cluster, directorio, total)

    @staticmethod
    def _leer_fecha(datos: bytes, indice: int) -> str:
        """Una fecha mal formada se considera un directorio inconsistente."""
        if len(datos) != 14 or not datos.isdigit():
            raise ErrorFiUnamFS(f"Fecha inválida en la entrada {indice}")
        fecha = datos.decode("ascii")
        try:
            datetime.strptime(fecha, "%Y%m%d%H%M%S")
        except ValueError as error:
            raise ErrorFiUnamFS(f"Fecha imposible en la entrada {indice}") from error
        return fecha

    def listar_archivos(self) -> list[Archivo]:
        """Interpreta 128 entradas y rechaza archivos superpuestos o fuera del disco."""
        self.leer_superbloque()
        with self.ruta.open("rb") as imagen:
            imagen.seek(TAMANIO_CLUSTER)
            directorio = imagen.read(CLUSTERS_DIRECTORIO * TAMANIO_CLUSTER)

        archivos: list[Archivo] = []
        ocupados: set[int] = set()
        nombres: set[str] = set()

        for indice in range(len(directorio) // TAMANIO_ENTRADA):
            inicio = indice * TAMANIO_ENTRADA
            entrada = directorio[inicio:inicio + TAMANIO_ENTRADA]
            tipo, nombre_crudo = entrada[0:1], entrada[1:16]

            # Una entrada libre puede identificarse por el tipo o por su marca.
            if tipo == b"-" or nombre_crudo == MARCA_LIBRE:
                continue
            if tipo != b"F":
                raise ErrorFiUnamFS(f"Tipo de entrada desconocido en índice {indice}")

            try:
                nombre = nombre_crudo.rstrip(b"\x00 ").decode("ascii")
            except UnicodeDecodeError as error:
                raise ErrorFiUnamFS(f"Nombre no ASCII en entrada {indice}") from error
            if not nombre or nombre in nombres:
                raise ErrorFiUnamFS(f"Nombre vacío o repetido en entrada {indice}")

            tamanio, cluster = struct.unpack_from("<II", entrada, 16)
            creacion = self._leer_fecha(entrada[24:38], indice)
            modificacion = self._leer_fecha(entrada[38:52], indice)
            cantidad = (tamanio + TAMANIO_CLUSTER - 1) // TAMANIO_CLUSTER

            # Para un archivo vacío se admite cluster 0 (sin datos asignados).
            if cantidad and (cluster < PRIMER_CLUSTER_DATOS or
                             cluster + cantidad > CLUSTERS_TOTALES):
                raise ErrorFiUnamFS(f"Archivo fuera del área de datos: {nombre}")
            if cantidad == 0 and cluster != 0 and not (PRIMER_CLUSTER_DATOS <= cluster < CLUSTERS_TOTALES):
                raise ErrorFiUnamFS(f"Cluster inválido para archivo vacío: {nombre}")

            nuevos = set(range(cluster, cluster + cantidad))
            if nuevos & ocupados:
                raise ErrorFiUnamFS(f"Clusters superpuestos: {nombre}")
            ocupados.update(nuevos)
            nombres.add(nombre)
            archivos.append(Archivo(nombre, tamanio, cluster, creacion,
                                    modificacion, indice))

        return archivos
