"""Interfaz de consola temporal para verificar la fase 1 de FiUnamFS."""

import argparse
from fiunamfs import ErrorFiUnamFS, FiUnamFS


def main() -> None:
    parser = argparse.ArgumentParser(description="Lista archivos de una imagen FiUnamFS 27-1")
    parser.add_argument("imagen", help="Ruta de la imagen .img")
    argumentos = parser.parse_args()

    try:
        disco = FiUnamFS(argumentos.imagen)
        superbloque = disco.leer_superbloque()
        archivos = disco.listar_archivos()
    except (OSError, ErrorFiUnamFS) as error:
        parser.exit(1, f"Error: {error}\n")

    print(f"Volumen: {superbloque.etiqueta or '(sin etiqueta)'}")
    print(f"Archivos encontrados: {len(archivos)}\n")
    print(f"{'Nombre':15} {'Bytes':>10} {'Cluster':>8}  {'Creación':14}  {'Modificación':14}")
    print("-" * 73)
    for archivo in archivos:
        print(f"{archivo.nombre:15} {archivo.tamanio:10} "
              f"{archivo.cluster_inicial:8}  {archivo.creacion}  {archivo.modificacion}")


if __name__ == "__main__":
    main()
