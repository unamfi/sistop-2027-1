from pathlib import Path
from fiunamfs import ErrorFiUnamFS


def mostrar_archivos(sistema):
    """Muestra los archivos del directorio FiUnamFS."""
    archivos = sistema.listar_archivos()

    if not archivos:
        print("El directorio de FiUnamFS está vacío.")
        return archivos

    print("\nArchivos en FiUnamFS:")
    print(f"{'Nombre':<16} {'Tamaño':>12} {'Cluster inicial':>16}")
    print("-" * 48)

    for archivo in archivos:
        print(
            f"{archivo.nombre:<16} "
            f"{archivo.tamano:>12} "
            f"{archivo.cluster_inicial:>16}"
        )

    return archivos


def extraer_archivo(sistema):
    """Solicita los datos necesarios para extraer un archivo."""
    archivos = mostrar_archivos(sistema)
    if not archivos:
        return

    nombre = input("Nombre exacto del archivo que quieres copiar con todo y extensión: ").strip()
    if not nombre:
        print("Operación cancelada.")
        return

    ruta = input(
        "Ruta destino completa, incluye el nombre del archivo: "
    ).strip().strip('"')
    if not ruta:
        print("Operación cancelada.")
        return

    try:
        destino = sistema.extraer_archivo(nombre, Path(ruta))
        print(f"El archivo extraído en: {destino.resolve()}")
    except (ErrorFiUnamFS, OSError) as error:
        print(f"No se pudo extraer el archivo: {error}")


def iniciar(sistema):
    """Muestra el menú inicial de listado y extracción."""
    while True:
        print("\n Administrador FiUnamFS ")
        print("1. Listar archivos de la imagen")
        print("2. Copiar un archivo de la imagen a mi equipo")
        print("0. Salir")

        opcion = input("Elige una opción: ").strip()

        if opcion == "0":
            print("Cerrando programa...")
            break
        elif opcion == "1":
            mostrar_archivos(sistema)
        elif opcion == "2":
            extraer_archivo(sistema)
        else:
            print("Opción no válida. Elige 1, 2 o 0.")
