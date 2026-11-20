
"""Interfaz de consola para administrar archivos FiUnamFS."""

import argparse
from fiunamfs import ErrorFiUnamFS, FiUnamFS


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Administración de archivos FiUnamFS 27-1"
    )

    parser.add_argument(
        "imagen",
        help="Ruta de la imagen FiUnamFS"
    )

    # Solo se permite una operación por ejecución.
    operaciones = parser.add_mutually_exclusive_group()

    operaciones.add_argument(
        "--exportar",
        help="Nombre del archivo que se desea extraer"
    )

    operaciones.add_argument(
        "--importar",
        help="Ruta del archivo que se incorporará a FiUnamFS"
    )

    operaciones.add_argument(
        "--eliminar",
        help="Nombre del archivo que se eliminará de FiUnamFS"
    )

    parser.add_argument(
        "--destino",
        help="Ruta donde se guardará el archivo exportado"
    )

    args = parser.parse_args()

    # La exportación requiere un nombre y una ruta de destino.
    if (args.exportar is None) != (args.destino is None):
        parser.error("Debes indicar --exportar y --destino juntos")

    try:
        disco = FiUnamFS(args.imagen)
        superbloque = disco.leer_superbloque()

        # Importación de archivos.
        if args.importar is not None:
            archivo = disco.importar_archivo(args.importar)

            print(
                f"Archivo importado: {archivo.nombre} "
                f"({archivo.tamanio} bytes) "
                f"al cluster {archivo.cluster_inicial}"
            )
            return

        # Exportación de archivos.
        if args.exportar is not None:
            ruta = disco.exportar_archivo(
                args.exportar, args.destino
            )

            print(
                f"Archivo exportado: "
                f"{args.exportar} -> {ruta}"
            )
            return

        # Eliminación de archivos.
        if args.eliminar is not None:
            archivo = disco.eliminar_archivo(args.eliminar)

            print(
                f"Archivo eliminado: {archivo.nombre} "
                f"({archivo.tamanio} bytes)"
            )
            return

        # Listado del directorio.
        archivos = disco.listar_archivos()

    except (OSError, ErrorFiUnamFS) as error:
        parser.exit(1, f"Error: {error}\n")

    print(f"Volumen: {superbloque.etiqueta or '(sin etiqueta)'}")
    print(f"Archivos encontrados: {len(archivos)}\n")

    print(
        f"{'Nombre':15} {'Bytes':>10} {'Cluster':>8}  "
        f"{'Creación':14}  {'Modificación':14}"
    )
    print("-" * 73)

    for archivo in archivos:
        print(
            f"{archivo.nombre:15} {archivo.tamanio:10} "
            f"{archivo.cluster_inicial:8}  "
            f"{archivo.creacion}  {archivo.modificacion}"
        )


if __name__ == "__main__":
    main()
