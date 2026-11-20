"""Operaciones del micro sistema de archivos FiUnamFS, versión 27-1."""

import sys


sys.dont_write_bytecode = True

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import os
import struct
import tempfile
from concurrencia import TrabajadorDisco

FIRMA = b"FiUnamFS"
VERSION = b"27-1"
TAMANO_CLUSTER = 2048
CLUSTERS_DIRECTORIO = 4
CLUSTERS_TOTALES = 720
TAMANO_ENTRADA = 64
LONGITUD_NOMBRE = 15
NOMBRE_VACIO = "#.............."
TIPO_ARCHIVO = b"F"
TIPO_LIBRE = b"-"
ENTRADA_VACIA = (TIPO_LIBRE + NOMBRE_VACIO.encode("ascii")).ljust(TAMANO_ENTRADA, b"\x00")
FORMATO_FECHA = "%Y%m%d%H%M%S"


class ErrorFormato(ValueError):
    """La imagen no cumple el formato esperado."""



@dataclass(frozen=True)
class Archivo:
    nombre: str
    tamano: int
    cluster_inicial: int
    creacion: str
    modificacion: str


@dataclass(frozen=True)
class Volumen:
    etiqueta: str
    tamano_cluster: int
    clusters_directorio: int
    clusters_totales: int
    archivos: tuple[Archivo, ...]


def clusters_necesarios(tamano: int, tamano_cluster: int) -> int:
    """Redondea hacia arriba: el último cluster parcial también se reserva."""
    return (tamano + tamano_cluster - 1) // tamano_cluster


def recorrer_directorio(datos: bytes, tamano_cluster: int, clusters_directorio: int):
    """Entrega la posición y los bytes de cada entrada, incluidas las libres."""
    # El directorio inicia justo tras el cluster 0 (superbloque) en bloques fijos de 64 bytes.
    fin = (1 + clusters_directorio) * tamano_cluster
    for posicion in range(tamano_cluster, fin, TAMANO_ENTRADA):
        yield posicion, datos[posicion:posicion + TAMANO_ENTRADA]


def texto(datos: bytes) -> str:
    try:
        return datos.decode("ascii").rstrip("\x00 ")
    except UnicodeDecodeError as exc:
        raise ErrorFormato("Se encontró texto que no es ASCII.") from exc


def fecha(datos: bytes) -> str:
    cadena = texto(datos)
    if len(cadena) != 14 or not cadena.isdigit():
        raise ErrorFormato(f"Fecha inválida: {cadena!r}.")
    try:
        return datetime.strptime(cadena, FORMATO_FECHA).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise ErrorFormato(f"Fecha inválida: {cadena!r}.") from exc


# Lectura del disco. convierte los bytes de la imagen en datos de archivos

def leer_volumen(ruta: Path) -> Volumen:
    """Lee una imagen completa sin modificarla y valida sus entradas activas."""
    return analizar_volumen(ruta.read_bytes())


def analizar_volumen(datos: bytes) -> Volumen:
    """Valida una instantánea del disco para usar metadatos y contenido coherentes."""
    # 1. Validación del superbloque 
    if len(datos) < 52:
        raise ErrorFormato("El archivo está truncado: falta el superbloque.")
    if datos[:8] != FIRMA:
        raise ErrorFormato("La firma del disco no es FiUnamFS.")
    if datos[10:14] != VERSION:
        raise ErrorFormato("La versión del disco debe ser 27-1.")

    # interpreta tres enteros sin signo de 32 bits en little endian.
    cluster, directorio, total = struct.unpack_from("<III", datos, 40)
    if (cluster, directorio, total) != (TAMANO_CLUSTER, CLUSTERS_DIRECTORIO, CLUSTERS_TOTALES):
        raise ErrorFormato("Geometría inesperada: se requieren clusters de 2048 bytes, "
                           "4 clusters de directorio y 720 en total.")
    if len(datos) != cluster * total:
        raise ErrorFormato("El tamaño de la imagen no coincide con el superbloque.")

    # 2. Recorrido y verificación de las 128 entradas del directorio (clusters 1 a 4):
    # descarta entradas libres, valida nombres únicos y comprueba que los rangos
    # de clusters 
    archivos = []
    nombres = set()
    regiones = []
    inicio_datos = 1 + directorio
    for posicion, entrada in recorrer_directorio(datos, cluster, directorio):
        if entrada[:1] == TIPO_LIBRE:
            continue
        if entrada[:1] != TIPO_ARCHIVO:
            raise ErrorFormato(f"Tipo de entrada desconocido en el byte {posicion}.")
        nombre = texto(entrada[1:1 + LONGITUD_NOMBRE])
        if not nombre or nombre == NOMBRE_VACIO or nombre in nombres:
            raise ErrorFormato(f"Nombre vacío, reservado o duplicado: {nombre!r}.")
        nombres.add(nombre)
        # Extrae tamaño y cluster inicial (dos uint32 little-endian en los bytes 16..23)
        # y verifica que no salgan del área de datos ni colisionen con otras regiones.
        tamano, inicio = struct.unpack_from("<II", entrada, 16)
        cantidad = clusters_necesarios(tamano, cluster)
        if tamano and (inicio < inicio_datos or inicio + cantidad > total):
            raise ErrorFormato(f"El archivo {nombre!r} apunta fuera del área de datos.")
        if tamano:
            for desde, hasta in regiones:
                if inicio < hasta and desde < inicio + cantidad:
                    raise ErrorFormato(f"Los clusters de {nombre!r} se superponen con otro archivo.")
            regiones.append((inicio, inicio + cantidad))
        archivos.append(Archivo(nombre, tamano, inicio, fecha(entrada[24:38]),
                                fecha(entrada[38:52])))

    return Volumen(texto(datos[20:36]), cluster, directorio, total, tuple(archivos))


def extraer_archivo(ruta: Path, nombre: str, destino: Path) -> int:
    """Copia los bytes del archivo a una ruta nueva elegida explícitamente."""
    datos = ruta.read_bytes()
    volumen = analizar_volumen(datos)
    archivo = next((item for item in volumen.archivos if item.nombre == nombre), None)
    if archivo is None:
        raise FileNotFoundError(f"No existe el archivo {nombre!r} en FiUnamFS.")
    # Convierte el cluster inicial a desplazamiento en bytes y recorta al tamaño lógico exacto.
    inicio = archivo.cluster_inicial * volumen.tamano_cluster
    contenido = datos[inicio:inicio + archivo.tamano]
    # 'xb' crea exclusivamente: nunca reemplaza un archivo ni la imagen de origen.
    with destino.open("xb") as salida:
        salida.write(contenido)
    return archivo.tamano


def guardar_volumen(ruta: Path, datos: bytearray) -> None:
    """Valida y reemplaza la imagen completa desde un temporal en el mismo volumen."""
    # Escritura atómica: valida la imagen en memoria
    analizar_volumen(datos)
    ruta = ruta.resolve(strict=True)
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(dir=ruta.parent, prefix=".fiunamfs-",
                                         suffix=".tmp", delete=False) as salida:
            temporal = Path(salida.name)
            salida.write(datos)
            salida.flush()
            os.fsync(salida.fileno())
        os.replace(temporal, ruta)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)


def validar_nombre(nombre: str) -> bytes:
    """Valida un nombre nuevo y devuelve su representación ASCII."""
    try:
        nombre_bytes = nombre.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("El nombre debe usar solamente caracteres ASCII.") from exc
    if (not 1 <= len(nombre_bytes) <= LONGITUD_NOMBRE or "\x00" in nombre
            or nombre.endswith(" ") or nombre == NOMBRE_VACIO):
        raise ValueError("Nombre inválido: usa de 1 a 15 caracteres ASCII, sin NUL "
                         "ni espacios finales ni el nombre reservado '#..............'.")
    return nombre_bytes


# Para importar se necesitan dos espacios: una entrada en el directorio
# y un tramo de clusters consecutivos donde almacenar el contenido.
def buscar_entrada_libre(datos: bytes, volumen: Volumen) -> int:
    for posicion, entrada in recorrer_directorio(datos, volumen.tamano_cluster,
                                                  volumen.clusters_directorio):
        if entrada[:1] == TIPO_LIBRE:
            return posicion
    raise ValueError("El directorio está lleno.")


def buscar_espacio_libre(volumen: Volumen, necesarios: int) -> int:
    """Devuelve el primer cluster del primer tramo contiguo suficiente (first fit)."""
    primero = 1 + volumen.clusters_directorio
    if necesarios == 0:
        return primero
    # Construye un mapa de ocupación marcando todos los clusters usados por archivos activos.
    ocupados = [False] * volumen.clusters_totales
    for archivo in volumen.archivos:
        cantidad = clusters_necesarios(archivo.tamano, volumen.tamano_cluster)
        for numero in range(archivo.cluster_inicial, archivo.cluster_inicial + cantidad):
            ocupados[numero] = True
    # Escanea el área de datos (desde el cluster 5) buscando la primera secuencia contigua libre.
    libres = 0
    for numero in range(primero, volumen.clusters_totales):
        libres = 0 if ocupados[numero] else libres + 1
        if libres == necesarios:
            return numero - necesarios + 1
    raise ValueError("No hay espacio contiguo suficiente para el archivo.")


def crear_entrada(nombre_bytes: bytes, tamano: int, inicio: int) -> bytearray:
    """Construye una entrada a partir de un nombre previamente validado."""
    # Empaqueta los 64 bytes de la entrada: tipo (1 B), nombre rellenado con espacios (15 B),
    # tamaño y cluster inicial en little-endian 
    entrada = bytearray(TAMANO_ENTRADA)
    entrada[:1] = TIPO_ARCHIVO
    entrada[1:1 + LONGITUD_NOMBRE] = nombre_bytes.ljust(LONGITUD_NOMBRE, b" ")
    struct.pack_into("<II", entrada, 16, tamano, inicio)
    # Fechas de creación y modificación de la copia dentro de FiUnamFS.
    ahora = datetime.now().strftime(FORMATO_FECHA).encode("ascii")
    entrada[24:38] = ahora
    entrada[38:52] = ahora
    return entrada


def importar_archivo(ruta: Path, origen: Path, nombre: str | None = None) -> str:
    """Valida, reserva espacio y guarda una copia nueva dentro del disco."""
    datos = bytearray(ruta.read_bytes())
    volumen = analizar_volumen(datos)
    nombre = origen.name if nombre is None else nombre
    nombre_bytes = validar_nombre(nombre)
    if any(archivo.nombre == nombre for archivo in volumen.archivos):
        raise FileExistsError(f"Ya existe {nombre!r} en FiUnamFS.")
    if ruta.samefile(origen):
        raise ValueError("La imagen no puede importarse a sí misma.")
    posicion = buscar_entrada_libre(datos, volumen)

    cluster = volumen.tamano_cluster
    capacidad = (volumen.clusters_totales - 1 - volumen.clusters_directorio) * cluster
    # La lectura limitada evita cargar archivos que nunca cabrían en el disco.
    with origen.open("rb") as archivo_origen:
        contenido = archivo_origen.read(capacidad + 1)
    if len(contenido) > capacidad:
        raise ValueError("El archivo supera la capacidad del área de datos.")

    # Reserva espacio contiguo, escribe la nueva entrada en el directorio y guarda los datos
    # rellenando con ceros el último cluster antes de persistir el volumen completo.
    necesarios = clusters_necesarios(len(contenido), cluster)
    inicio = buscar_espacio_libre(volumen, necesarios)
    datos[posicion:posicion + TAMANO_ENTRADA] = crear_entrada(nombre_bytes, len(contenido), inicio)
    desde = inicio * cluster
    datos[desde:desde + necesarios * cluster] = contenido.ljust(necesarios * cluster, b"\x00")
    guardar_volumen(ruta, datos)
    return nombre


def eliminar_archivo(ruta: Path, nombre: str) -> None:
    """Libera la entrada y permite reutilizar sus clusters; no borra físicamente los datos."""
    datos = bytearray(ruta.read_bytes())
    volumen = analizar_volumen(datos)
    # Borrado lógico: sobrescribe únicamente los 64 bytes de la entrada con ENTRADA_VACIA;
    # sus clusters quedan disponibles para futuras escrituras sin limpiar el área de datos.
    for posicion, entrada in recorrer_directorio(datos, volumen.tamano_cluster,
                                                  volumen.clusters_directorio):
        if entrada[:1] == TIPO_ARCHIVO and texto(entrada[1:1 + LONGITUD_NOMBRE]) == nombre:
            datos[posicion:posicion + TAMANO_ENTRADA] = ENTRADA_VACIA
            guardar_volumen(ruta, datos)
            return
    raise FileNotFoundError(f"No existe el archivo {nombre!r} en FiUnamFS.")


# Entrada por terminal: interpreta los argumentos y permite elegir una sola
# operación. Si no se indica ninguna, muestra el listado del disco.
def main() -> int:
    parser = argparse.ArgumentParser(description="Lista, extrae, importa o elimina archivos de FiUnamFS 27-1.")
    parser.add_argument("imagen", type=Path, help="Ruta al archivo fiunamfs.img")
    operaciones = parser.add_mutually_exclusive_group()
    operaciones.add_argument("--extraer", metavar="NOMBRE", help="Nombre exacto del archivo dentro del disco")
    operaciones.add_argument("--importar", type=Path, metavar="RUTA", help="Archivo local a copiar al disco")
    operaciones.add_argument("--eliminar", metavar="NOMBRE", help="Archivo a eliminar del disco")
    parser.add_argument("--nombre", help="Nombre para la copia importada (máximo 15 caracteres)")
    parser.add_argument("--destino", type=Path, metavar="RUTA", help="Ruta completa del archivo nuevo a crear")
    args = parser.parse_args()
    if (args.extraer is None) != (args.destino is None):
        parser.error("--extraer y --destino deben usarse juntos.")
    if args.nombre is not None and args.importar is None:
        parser.error("--nombre solamente puede usarse con --importar.")
    # Crea el hilo trabajador dedicado al disco y asegura su cierre ordenado al terminar.
    with TrabajadorDisco() as trabajador:
        return ejecutar_comando(args, trabajador)


def ejecutar_comando(args, trabajador: TrabajadorDisco) -> int:
    """El hilo principal presenta resultados; el trabajador accede al disco."""
    # Despacha la operación solicitada al hilo trabajador para aislar el acceso a la imagen.
    try:
        if args.importar is not None:
            nombre = trabajador.ejecutar(importar_archivo, args.imagen, args.importar, args.nombre)
            print(f"Archivo importado: {nombre}")
            return 0
        if args.eliminar is not None:
            trabajador.ejecutar(eliminar_archivo, args.imagen, args.eliminar)
            print(f"Archivo eliminado: {args.eliminar}")
            return 0
        if args.extraer is not None:
            tamano = trabajador.ejecutar(extraer_archivo, args.imagen, args.extraer, args.destino)
            print(f"Archivo extraído: {args.destino.resolve()} ({tamano} bytes)")
            return 0
        volumen = trabajador.ejecutar(leer_volumen, args.imagen)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"FiUnamFS 27-1 | Volumen: {volumen.etiqueta}")
    print(f"Cluster: {volumen.tamano_cluster} bytes | Archivos: {len(volumen.archivos)}")
    print(f"{'Nombre':15} {'Bytes':>10} {'Cluster':>8}  {'Creación':19}  Modificación")
    for archivo in volumen.archivos:
        print(f"{archivo.nombre:15} {archivo.tamano:10} {archivo.cluster_inicial:8}  "
              f"{archivo.creacion}  {archivo.modificacion}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
