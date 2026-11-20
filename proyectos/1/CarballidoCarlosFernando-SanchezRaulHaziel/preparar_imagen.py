
#!/usr/bin/env python3
"""Etapa 1: crear y validar una imagen vacia de FiUnamFS."""

from pathlib import Path
import struct

SECTOR = 512
SECTORES_POR_CLUSTER = 4
TAM_CLUSTER = SECTOR * SECTORES_POR_CLUSTER

TAM_DISCO = 1440 * 1024
TOTAL_CLUSTERS = TAM_DISCO // TAM_CLUSTER
CLUSTERS_DIRECTORIO = 4
TAM_ENTRADA = 64

RUTA_IMAGEN = Path("fiunamfs_prueba.img")


def crear_imagen(ruta):
    """Prepara un volumen nuevo con el directorio vacio."""
    disco = bytearray(TAM_DISCO)

    # Identificacion del sistema de archivos.
    disco[0:8] = b"FiUnamFS"
    disco[10:14] = b"27-1"
    disco[20:36] = b"FI-PRUEBA".ljust(16, b" ")

    # Valores de 32 bits en little-endian.
    struct.pack_into("<I", disco, 40, TAM_CLUSTER)
    struct.pack_into("<I", disco, 44, CLUSTERS_DIRECTORIO)
    struct.pack_into("<I", disco, 48, TOTAL_CLUSTERS)

    # Inicializamos las 128 entradas del directorio como vacias.
    inicio_directorio = TAM_CLUSTER
    total_entradas = CLUSTERS_DIRECTORIO * TAM_CLUSTER // TAM_ENTRADA

    for numero in range(total_entradas):
        posicion = inicio_directorio + numero * TAM_ENTRADA
        disco[posicion] = ord("-")
        disco[posicion + 1:posicion + 16] = b"#" + b"." * 14

    # "xb" evita sobrescribir accidentalmente una imagen existente.
    with ruta.open("xb") as archivo:
        archivo.write(disco)

    print(f"Imagen creada: {ruta}")


def validar_imagen(ruta):
    """Revisa la identidad y las dimensiones del volumen."""
    with ruta.open("rb") as archivo:
        superbloque = archivo.read(TAM_CLUSTER)

    identificador = superbloque[0:8].decode("ascii", errors="replace")
    version = superbloque[10:14].decode("ascii", errors="replace")
    etiqueta = superbloque[20:36].decode("ascii", errors="replace").strip()

    tam_cluster, clusters_directorio, clusters_total = (
        struct.unpack_from("<III", superbloque, 40)
    )

    print("\n--- Verificacion del superbloque ---")
    print(f"Identificador: {identificador}")
    print(f"Version: {version}")
    print(f"Etiqueta: {etiqueta}")
    print(f"Tamano de cluster: {tam_cluster} bytes")
    print(f"Clusters de directorio: {clusters_directorio}")
    print(f"Clusters totales: {clusters_total}")
    print(f"Tamano de imagen: {ruta.stat().st_size} bytes")

    correcto = (
        identificador == "FiUnamFS"
        and version == "27-1"
        and tam_cluster == TAM_CLUSTER
        and clusters_directorio == CLUSTERS_DIRECTORIO
        and clusters_total == TOTAL_CLUSTERS
        and ruta.stat().st_size == TAM_DISCO
    )

    if correcto:
        print("\nResultado: imagen valida.")
    else:
        print("\nResultado: imagen no valida.")

    return correcto


def main():
    try:
        if not RUTA_IMAGEN.exists():
            crear_imagen(RUTA_IMAGEN)
        else:
            print("La imagen ya existe. No se sobrescribira.")

        if not validar_imagen(RUTA_IMAGEN):
            return 1

        return 0

    except (OSError, struct.error) as error:
        print(f"Error al preparar o validar la imagen: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
