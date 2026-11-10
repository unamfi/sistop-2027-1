
"""Interfaz de consola para consultar y exportar archivos FiUnamFS."""

import argparse
from fiunamfs import ErrorFiUnamFS, FiUnamFS


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Consulta, importa y exporta archivos de FiUnamFS 27-1"
    )

    parser.add_argument("imagen", help="Ruta de la imagen FiUnamFS")
    parser.add_argument("--exportar", help="Nombre del archivo a extraer")
    parser.add_argument("--destino", help="Ruta donde guardar el archivo")
    parser.add_argument("--importar", help="Ruta del archivo local que se incorporará a FiUnamFS")

    args = parser.parse_args()
    if args.importar and (args.exportar or args.destino):
        parser.error("--importar no puede combinarse con --exportar ni --destino" )

    # La exportación necesita un nombre y una ruta de destino.
    if (args.exportar is None) != (args.destino is None):
        parser.error("Debes indicar --exportar y --destino juntos")

    try:
        disco = FiUnamFS(args.imagen)
        superbloque = disco.leer_superbloque()
        if args.importar is not None:
            archivo = disco.importar_archivo(args.importar)

            print(
                f"Archivo importado: {archivo.nombre} "
                f"({archivo.tamanio} bytes) "
                f"al cluster {archivo.cluster_inicial}")
            return



        if args.exportar is not None:
            ruta = disco.exportar_archivo(args.exportar, args.destino)
            print(f"Archivo exportado: {args.exportar} -> {ruta}")
            return

        archivos = disco.listar_archivos()

    except (OSError, ErrorFiUnamFS) as error:
        parser.exit(1, f"Error: {error}\n")

    print(f"Volumen: {superbloque.etiqueta or '(sin etiqueta)'}")
    print(f"Archivos encontrados: {len(archivos)}\n")
    print(f"{'Nombre':15} {'Bytes':>10} {'Cluster':>8}  "
          f"{'Creación':14}  {'Modificación':14}")
    print("-" * 73)

    for archivo in archivos:
        print(f"{archivo.nombre:15} {archivo.tamanio:10} "
              f"{archivo.cluster_inicial:8}  "
              f"{archivo.creacion}  {archivo.modificacion}")


if __name__ == "__main__":
    main()
