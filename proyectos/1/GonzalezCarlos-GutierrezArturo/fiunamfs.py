from dataclasses import dataclass
from datetime import datetime
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

    def copiar_archivo(self, ruta_origen, nombre_destino=None):
        """Copia un archivo local al volumen, usando clusters contiguos."""
        ruta_origen = Path(ruta_origen)

        if not ruta_origen.is_file():
            raise ErrorFiUnamFS(
                f"No se encontró el archivo local: {ruta_origen}"
            )

        if ruta_origen.resolve() == self.ruta_imagen.resolve():
            raise ErrorFiUnamFS(
                "El archivo de origen no puede ser la imagen FiUnamFS."
            )

        nombre_destino = nombre_destino or ruta_origen.name
        nombre_bytes = self._validar_nombre(nombre_destino)

        archivos = self.listar_archivos()
        if any(archivo.nombre == nombre_destino for archivo in archivos):
            raise ErrorFiUnamFS(
                f"Ya existe '{nombre_destino}' en FiUnamFS."
            )

        indice_libre = self._buscar_entrada_libre()
        if indice_libre is None:
            raise ErrorFiUnamFS("El directorio de FiUnamFS está lleno.")

        tamano = ruta_origen.stat().st_size
        clusters_necesarios = (
            tamano + self.tamano_cluster - 1
        ) // self.tamano_cluster

        clusters_ocupados = set()
        for archivo in archivos:
            if archivo.cluster_inicial < self.primer_cluster_datos:
                raise ErrorFiUnamFS(
                    f"La entrada de '{archivo.nombre}' apunta al área reservada."
                )

            cantidad_clusters = (
                archivo.tamano + self.tamano_cluster - 1
            ) // self.tamano_cluster
            ultimo_cluster = archivo.cluster_inicial + cantidad_clusters

            if ultimo_cluster > self.clusters_totales:
                raise ErrorFiUnamFS(
                    f"La entrada de '{archivo.nombre}' excede el volumen."
                )

            clusters_ocupados.update(
                range(archivo.cluster_inicial, ultimo_cluster)
            )

        # Un archivo vacío también recibe un cluster inicial válido.
        cluster_inicial = self._buscar_espacio_contiguo(
            clusters_ocupados,
            max(clusters_necesarios, 1),
        )
        if cluster_inicial is None:
            raise ErrorFiUnamFS(
                "No hay espacio contiguo suficiente para ese archivo."
            )

        contenido = ruta_origen.read_bytes()
        if len(contenido) != tamano:
            raise ErrorFiUnamFS(
                "El archivo local cambió mientras se estaba leyendo."
            )

        ahora = datetime.now().strftime("%Y%m%d%H%M%S").encode("ascii")
        entrada = bytearray(TAM_ENTRADA)
        entrada[0:1] = b"F"
        entrada[1:1 + len(nombre_bytes)] = nombre_bytes
        struct.pack_into("<I", entrada, 16, tamano)
        struct.pack_into("<I", entrada, 20, cluster_inicial)
        entrada[24:38] = ahora
        entrada[38:52] = ahora

        posicion_datos = cluster_inicial * self.tamano_cluster
        posicion_entrada = (
            self.inicio_directorio + indice_libre * TAM_ENTRADA
        )

        # Se escriben primero los bytes del archivo y al final su entrada.
        with self.ruta_imagen.open("r+b") as imagen:
            imagen.seek(posicion_datos)
            imagen.write(contenido)
            imagen.seek(posicion_entrada)
            imagen.write(entrada)

        return Archivo(
            nombre=nombre_destino,
            tamano=tamano,
            cluster_inicial=cluster_inicial,
            fecha_creacion=ahora.decode("ascii"),
            fecha_modificacion=ahora.decode("ascii"),
        )

    def _buscar_entrada_libre(self):
        with self.ruta_imagen.open("rb") as imagen:
            imagen.seek(self.inicio_directorio)
            directorio = imagen.read(self.tamano_directorio)

        cantidad_entradas = len(directorio) // TAM_ENTRADA
        for indice in range(cantidad_entradas):
            inicio = indice * TAM_ENTRADA
            entrada = directorio[inicio:inicio + TAM_ENTRADA]

            if entrada[0:1] == b"-" or entrada[1:2] == b"#":
                return indice

        return None

    def _buscar_espacio_contiguo(self, clusters_ocupados, cantidad):
        ultimo_inicio = self.clusters_totales - cantidad

        for cluster_inicial in range(
            self.primer_cluster_datos,
            ultimo_inicio + 1,
        ):
            tramo = range(cluster_inicial, cluster_inicial + cantidad)
            if all(cluster not in clusters_ocupados for cluster in tramo):
                return cluster_inicial

        return None

    @staticmethod
    def _validar_nombre(nombre):
        try:
            nombre_bytes = nombre.encode("ascii")
        except UnicodeEncodeError as error:
            raise ErrorFiUnamFS(
                "El nombre debe usar únicamente caracteres ASCII."
            ) from error

        if not nombre_bytes or len(nombre_bytes) > 15:
            raise ErrorFiUnamFS(
                "El nombre debe tener entre 1 y 15 caracteres ASCII."
            )

        if any(byte < 32 or byte > 126 for byte in nombre_bytes):
            raise ErrorFiUnamFS(
                "El nombre debe contener caracteres ASCII imprimibles."
            )

        if nombre.startswith("#"):
            raise ErrorFiUnamFS(
                "Los nombres que empiezan con # están reservados."
            )

        return nombre_bytes
