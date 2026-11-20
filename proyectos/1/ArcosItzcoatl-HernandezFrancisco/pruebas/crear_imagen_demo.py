"""Crea una imagen ARTIFICIAL para pruebas; no es la imagen del profesor."""

from pathlib import Path
import struct
import sys

# Permite importarlo al ejecutar las pruebas desde la carpeta del proyecto.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fiunamfs import (CLUSTERS_DIRECTORIO, CLUSTERS_TOTALES, MARCA_LIBRE,
                      TAMANIO_CLUSTER, TAMANIO_DISCO, TAMANIO_ENTRADA)


def crear_imagen(ruta: Path) -> None:
    """Crea un volumen de prueba con dos archivos, sin sobrescribir uno existente."""
    archivos = [("HOLA.TXT", b"Hola desde FiUnamFS!\n", 5),
                ("DATOS.BIN", bytes(range(256)), 6)]
    with ruta.open("xb") as imagen:
        imagen.write(b"\x00" * TAMANIO_DISCO)
        imagen.seek(0)
        imagen.write(b"FiUnamFS")
        imagen.seek(10)
        imagen.write(b"27-1")
        imagen.seek(20)
        imagen.write(b"DEMO_FIUNAMFS".ljust(16, b"\x00"))
        imagen.seek(40)
        imagen.write(struct.pack("<III", TAMANIO_CLUSTER,
                                CLUSTERS_DIRECTORIO, CLUSTERS_TOTALES))

        imagen.seek(TAMANIO_CLUSTER)
        libre = b"-" + MARCA_LIBRE + b"\x00" * (TAMANIO_ENTRADA - 16)
        imagen.write(libre * (CLUSTERS_DIRECTORIO * TAMANIO_CLUSTER // TAMANIO_ENTRADA))

        for indice, (nombre, contenido, cluster) in enumerate(archivos):
            registro = (b"F" + nombre.encode("ascii").ljust(15, b"\x00")
                        + struct.pack("<II", len(contenido), cluster)
                        + b"20261104180000" * 2 + b"\x00" * 12)
            imagen.seek(TAMANIO_CLUSTER + indice * TAMANIO_ENTRADA)
            imagen.write(registro)
            imagen.seek(cluster * TAMANIO_CLUSTER)
            imagen.write(contenido)


if __name__ == "__main__":
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("demo_fiunamfs.img")
    crear_imagen(destino)
    print(f"Imagen de prueba creada: {destino} ({TAMANIO_DISCO} bytes)")
