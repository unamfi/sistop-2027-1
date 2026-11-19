from dataclasses import dataclass
from pathlib import Path
import struct


TAM_DISCO = 1440 * 1024
TAM_ENTRADA = 64
FIRMA = b"FiUnamFS"
VERSION = b"27-1"


class ErrorFiUnamFS(Exception):
    """Error al abrir o interpretar una imagen FiUnamFS."""


@dataclass
class Archivo:
    nombre: str
    tamano: int
    cluster_inicial: int
    fecha_creacion: str
    fecha_modificacion: str


class SistemaFiUnamFS:
    def __init__(self, ruta_imagen):
        self.ruta_imagen = Path(ruta_imagen)

        if not self.ruta_imagen.is_file():
            raise ErrorFiUnamFS(
                f"No se encontró la imagen: {self.ruta_imagen}"
            )

        if self.ruta_imagen.stat().st_size != TAM_DISCO:
            raise ErrorFiUnamFS(
                "La imagen debe medir exactamente 1440 KiB."
            )

        self._leer_superbloque()

    def _leer_superbloque(self):
        with self.ruta_imagen.open("rb") as imagen:
            superbloque = imagen.read(2048)

        if superbloque[0:8] != FIRMA:
            raise ErrorFiUnamFS("La imagen no tiene la firma FiUnamFS.")

        if superbloque[10:14] != VERSION:
            raise ErrorFiUnamFS("La imagen no corresponde a la versión 27-1.")

        self.etiqueta = (
            superbloque[20:36]
            .split(b"\0", 1)[0]
            .decode("ascii", errors="replace")
            .strip()
        )

        self.tamano_cluster = struct.unpack_from(
            "<I", superbloque, 40
        )[0]
        self.clusters_directorio = struct.unpack_from(
            "<I", superbloque, 44
        )[0]
        self.clusters_totales = struct.unpack_from(
            "<I", superbloque, 48
        )[0]

        if self.tamano_cluster == 0 or self.tamano_cluster % 512 != 0:
            raise ErrorFiUnamFS("El tamaño de cluster no es válido.")

        if self.clusters_directorio == 0:
            raise ErrorFiUnamFS("El directorio debe ocupar al menos un cluster.")

        self.inicio_directorio = self.tamano_cluster
        self.tamano_directorio = (
            self.clusters_directorio * self.tamano_cluster
        )
        self.primer_cluster_datos = 1 + self.clusters_directorio

        if self.inicio_directorio + self.tamano_directorio > TAM_DISCO:
            raise ErrorFiUnamFS("El directorio excede el tamaño de la imagen.")

        if self.clusters_totales * self.tamano_cluster > TAM_DISCO:
            raise ErrorFiUnamFS("El volumen excede el tamaño de la imagen.")

    def listar_archivos(self):
        archivos = []

        with self.ruta_imagen.open("rb") as imagen:
            imagen.seek(self.inicio_directorio)
            directorio = imagen.read(self.tamano_directorio)

        cantidad_entradas = len(directorio) // TAM_ENTRADA

        for numero_entrada in range(cantidad_entradas):
            inicio = numero_entrada * TAM_ENTRADA
            entrada = directorio[inicio:inicio + TAM_ENTRADA]

            # Solo las entradas de tipo F representan archivos.
            if entrada[0:1] != b"F":
                continue

            nombre_bytes = entrada[1:16].split(b"\0", 1)[0].rstrip(b" ")
            if not nombre_bytes:
                continue

            nombre = nombre_bytes.decode("ascii")

            # Los nombres que empiezan con # indican entradas libres.
            if nombre.startswith("#"):
                continue

            tamano = struct.unpack_from("<I", entrada, 16)[0]
            cluster_inicial = struct.unpack_from("<I", entrada, 20)[0]

            fecha_creacion = entrada[24:38].decode(
                "ascii", errors="replace"
            ).strip("\0 ")
            fecha_modificacion = entrada[38:52].decode(
                "ascii", errors="replace"
            ).strip("\0 ")

            archivos.append(
                Archivo(
                    nombre=nombre,
                    tamano=tamano,
                    cluster_inicial=cluster_inicial,
                    fecha_creacion=fecha_creacion,
                    fecha_modificacion=fecha_modificacion,
                )
            )

        return archivos

    def extraer_archivo(self, nombre, ruta_destino):
        """Copia un archivo de FiUnamFS a una ruta local."""
        archivo_encontrado = next(
            (archivo for archivo in self.listar_archivos()
             if archivo.nombre == nombre),
            None,
        )

        if archivo_encontrado is None:
            raise ErrorFiUnamFS(
                f"No existe '{nombre}' en el directorio de FiUnamFS."
            )

        inicio_datos = (
            archivo_encontrado.cluster_inicial * self.tamano_cluster
        )
        fin_datos = inicio_datos + archivo_encontrado.tamano

        if archivo_encontrado.cluster_inicial < self.primer_cluster_datos:
            raise ErrorFiUnamFS(
                f"La entrada de '{nombre}' apunta al área reservada."
            )

        if fin_datos > TAM_DISCO:
            raise ErrorFiUnamFS(
                f"Los datos de '{nombre}' exceden el tamaño de la imagen."
            )

        ruta_destino = Path(ruta_destino)
        if ruta_destino.resolve() == self.ruta_imagen.resolve():
            raise ErrorFiUnamFS(
                "El destino no puede ser la propia imagen FiUnamFS."
            )

        if ruta_destino.exists():
            raise ErrorFiUnamFS(
                f"Ya existe el archivo destino: {ruta_destino}"
            )

        ruta_destino.parent.mkdir(parents=True, exist_ok=True)

        with self.ruta_imagen.open("rb") as imagen:
            imagen.seek(inicio_datos)
            contenido = imagen.read(archivo_encontrado.tamano)

        if len(contenido) != archivo_encontrado.tamano:
            raise ErrorFiUnamFS(
                f"No se pudieron leer todos los datos de '{nombre}'."
            )

        with ruta_destino.open("wb") as archivo_local:
            archivo_local.write(contenido)

        return ruta_destino
