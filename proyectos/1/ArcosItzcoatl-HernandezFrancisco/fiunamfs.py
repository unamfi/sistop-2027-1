"""Administración de archivos del sistema FiUnamFS 27-1."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import struct
import os
import tempfile


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
    """Permite consultar y modificar imágenes FiUnamFS."""

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


    def exportar_archivo(self, nombre: str, destino: str | Path) -> Path:
        """Copia un archivo de FiUnamFS hacia la computadora."""

        archivos = self.listar_archivos()
        archivo = next((a for a in archivos if a.nombre == nombre), None)

        if archivo is None:
            raise ErrorFiUnamFS(f"No existe el archivo: {nombre}")

        ruta_salida = Path(destino)

        with self.ruta.open("rb") as imagen:
            imagen.seek(archivo.cluster_inicial * TAMANIO_CLUSTER)
            contenido = imagen.read(archivo.tamanio)

        if len(contenido) != archivo.tamanio:
            raise ErrorFiUnamFS("No se pudo leer el contenido completo")

        with ruta_salida.open("xb") as salida:
            salida.write(contenido)

        return ruta_salida

    def importar_archivo(self, origen: str | Path) -> Archivo:
        """Incorpora un archivo local en una imagen FiUnamFS."""

        fuente = Path(origen)

        if not fuente.is_file():
            raise ErrorFiUnamFS(f"No existe el archivo: {fuente}")

        if fuente.resolve() == self.ruta.resolve():
            raise ErrorFiUnamFS("No se puede importar la propia imagen")

        # Verificar que el nombre sea compatible con FiUnamFS.
        nombre = fuente.name
        try:
            nombre_bytes = nombre.encode("ascii")
        except UnicodeEncodeError as error:
            raise ErrorFiUnamFS("El nombre debe ser ASCII") from error

        if (not 1 <= len(nombre_bytes) <= 15
                or nombre_bytes == MARCA_LIBRE
                or any(b < 32 or b > 126 for b in nombre_bytes)
                or b"\\" in nombre_bytes
                or nombre.endswith(" ")):
            raise ErrorFiUnamFS("Nombre inválido para FiUnamFS")

        archivos = self.listar_archivos()

        if any(a.nombre == nombre for a in archivos):
            raise ErrorFiUnamFS(f"Ya existe el archivo: {nombre}")

        # Buscar una entrada disponible en el directorio.
        imagen = bytearray(self.ruta.read_bytes())
        base = TAMANIO_CLUSTER
        total_entradas = CLUSTERS_DIRECTORIO * TAMANIO_CLUSTER // TAMANIO_ENTRADA

        indice_libre = next(
            (i for i in range(total_entradas)
             if imagen[base + i * TAMANIO_ENTRADA] == ord("-")
             or imagen[base + i * TAMANIO_ENTRADA + 1:
                       base + i * TAMANIO_ENTRADA + 16] == MARCA_LIBRE),
            None
        )

        if indice_libre is None:
            raise ErrorFiUnamFS("El directorio está lleno")

        # Calcular los clusters necesarios.
        contenido = fuente.read_bytes()
        tamanio = len(contenido)
        cantidad = (tamanio + TAMANIO_CLUSTER - 1) // TAMANIO_CLUSTER

        ocupados = set()
        for archivo in archivos:
            bloques = (archivo.tamanio + TAMANIO_CLUSTER - 1) // TAMANIO_CLUSTER
            ocupados.update(
                range(archivo.cluster_inicial, archivo.cluster_inicial + bloques)
            )

        # Buscar una secuencia de clusters contiguos.
        inicio = 0
        if cantidad:
            inicio = next(
                (c for c in range(
                    PRIMER_CLUSTER_DATOS,
                    CLUSTERS_TOTALES - cantidad + 1
                ) if all(k not in ocupados for k in range(c, c + cantidad))),
                None
            )

            if inicio is None:
                raise ErrorFiUnamFS("No hay espacio contiguo suficiente")

        # Construir el registro de 64 bytes del directorio.
        fecha = datetime.now().strftime("%Y%m%d%H%M%S").encode("ascii")

        registro = (
            b"F"
            + nombre_bytes.ljust(15, b"\x00")
            + struct.pack("<II", tamanio, inicio)
            + fecha + fecha
            + b"\x00" * 12
        )

        posicion = base + indice_libre * TAMANIO_ENTRADA

        # Incorporar datos y actualizar la entrada del directorio.
        if cantidad:
            offset = inicio * TAMANIO_CLUSTER
            imagen[offset:offset + cantidad * TAMANIO_CLUSTER] = (
                contenido.ljust(cantidad * TAMANIO_CLUSTER, b"\x00")
            )

        imagen[posicion:posicion + TAMANIO_ENTRADA] = registro

        # Validar una imagen temporal antes de reemplazar la anterior.
        descriptor, ruta_temp = tempfile.mkstemp(
            prefix=".fiunamfs_", suffix=".tmp", dir=self.ruta.parent
        )
        temporal = Path(ruta_temp)

        try:
            with os.fdopen(descriptor, "wb") as salida:
                salida.write(imagen)
                salida.flush()
                os.fsync(salida.fileno())

            FiUnamFS(temporal).listar_archivos()
            os.replace(temporal, self.ruta)
        finally:
            temporal.unlink(missing_ok=True)

        return Archivo(
            nombre, tamanio, inicio,
            fecha.decode(), fecha.decode(), indice_libre
        )

    def eliminar_archivo(self, nombre: str) -> Archivo:
        """Elimina un archivo y libera sus clusters."""

        archivos = self.listar_archivos()
        archivo = next(
            (a for a in archivos if a.nombre == nombre),
            None
        )

        if archivo is None:
            raise ErrorFiUnamFS(f"No existe el archivo: {nombre}")

        # Localizar su entrada en el directorio.
        imagen = bytearray(self.ruta.read_bytes())
        posicion = (
            TAMANIO_CLUSTER
            + archivo.indice_directorio * TAMANIO_ENTRADA
        )

        # Marcar la entrada como libre.
        imagen[posicion:posicion + TAMANIO_ENTRADA] = (
            b"-" + MARCA_LIBRE + b"\x00" * 48
        )

        # Crear una imagen temporal para validar los cambios.
        descriptor, ruta_temp = tempfile.mkstemp(
            prefix=".fiunamfs_",
            suffix=".tmp",
            dir=self.ruta.parent
        )
        temporal = Path(ruta_temp)

        try:
            with os.fdopen(descriptor, "wb") as salida:
                salida.write(imagen)
                salida.flush()
                os.fsync(salida.fileno())

            FiUnamFS(temporal).listar_archivos()
            os.replace(temporal, self.ruta)

        finally:
            temporal.unlink(missing_ok=True)

        return archivo