from pathlib import Path
from fiunamfs import ErrorFiUnamFS


def mostrar_archivos(solicitar_operacion):
    """Muestra los archivos del directorio FiUnamFS."""
    archivos = solicitar_operacion("listar_archivos")

    if not archivos:
        print("El directorio de FiUnamFS está vacío.")
        return archivos

    print("\nArchivos en FiUnamFS:")
    print(
        f"{'Nombre':<16} {'Tamaño':>10} {'Cluster':>8}  "
        f"{'Última modificación':<19}"
    )
    print("-" * 57)

    for archivo in archivos:
        print(
            f"{archivo.nombre:<16} "
            f"{archivo.tamano:>10} "
            f"{archivo.cluster_inicial:>8}  "
            f"{formatear_fecha(archivo.fecha_modificacion)}"
        )

    return archivos


def formatear_fecha(fecha):
    """Convierte AAAAMMDDHHMMSS a un formato más fácil de leer."""
    if len(fecha) != 14 or not fecha.isdigit():
        return fecha

    return (
        f"{fecha[0:4]}-{fecha[4:6]}-{fecha[6:8]} "
        f"{fecha[8:10]}:{fecha[10:12]}:{fecha[12:14]}"
    )


def extraer_archivo(solicitar_operacion):
    """Solicita los datos necesarios para extraer un archivo."""
    archivos = mostrar_archivos(solicitar_operacion)
    if not archivos:
        return

    nombre = input("Nombre exacto del archivo que quieres copiar con todo y extensión: ").strip()
    if not nombre:
        print("Operación cancelada.")
        return

    ruta = input(
        "Carpeta o ruta destino (Enter para guardarlo en extraidos/): "
    ).strip().strip('"').strip("'")
    if ruta:
        destino = Path(ruta)
    else:
        destino = Path("extraidos") / nombre

    try:
        destino = solicitar_operacion("extraer_archivo", nombre, destino)
        print(f"El archivo extraído en: {destino.resolve()}")
    except (ErrorFiUnamFS, OSError) as error:
        print(f"No se pudo extraer el archivo: {error}")


def copiar_archivo_local(solicitar_operacion):
    """Solicita un archivo local y lo agrega a FiUnamFS."""
    ruta_origen = input(
        "Ruta del archivo de tu equipo (puedes pegarla aquí): "
    ).strip().strip('"').strip("'")
    if not ruta_origen:
        print("Operación cancelada.")
        return

    nombre_destino = input(
        "Nombre dentro de la imagen (Enter para usar el mismo nombre): "
    ).strip()
    if not nombre_destino:
        nombre_destino = None

    try:
        archivo = solicitar_operacion(
            "copiar_archivo", ruta_origen, nombre_destino
        )
        print(
            f"Copiado '{archivo.nombre}': {archivo.tamano} bytes, "
            f"cluster inicial {archivo.cluster_inicial}."
        )
    except (ErrorFiUnamFS, OSError) as error:
        print(f"No se pudo copiar el archivo: {error}")


def eliminar_archivo(solicitar_operacion):
    """Elimina una entrada del directorio después de validar su nombre."""
    archivos = mostrar_archivos(solicitar_operacion)
    if not archivos:
        return

    nombre = input(
        "Nombre exacto del archivo que quieres eliminar: "
    ).strip()
    if not nombre:
        print("Operación cancelada.")
        return

    archivo_encontrado = next(
        (archivo for archivo in archivos if archivo.nombre == nombre),
        None,
    )
    if archivo_encontrado is None:
        print(f"No existe '{nombre}' en FiUnamFS.")
        return

    try:
        solicitar_operacion("eliminar_archivo", nombre)
        print(f"Se eliminó '{nombre}' exitosamente.")
    except (ErrorFiUnamFS, OSError) as error:
        print(f"No se pudo eliminar el archivo: {error}")


def iniciar(solicitar_operacion):
    """Muestra el menú de operaciones disponibles."""
    while True:
        print("\n Administrador FiUnamFS ")
        print("1. Listar archivos de la imagen")
        print("2. Copiar un archivo de la imagen a mi equipo")
        print("3. Copiar un archivo de mi equipo a FiUnamFS")
        print("4. Eliminar un archivo de FiUnamFS")
        print("0. Salir")

        opcion = input("Elige una opción: ").strip()

        if opcion == "0":
            print("Cerrando programa...")
            break
        elif opcion == "1":
            mostrar_archivos(solicitar_operacion)
        elif opcion == "2":
            extraer_archivo(solicitar_operacion)
        elif opcion == "3":
            copiar_archivo_local(solicitar_operacion)
        elif opcion == "4":
            eliminar_archivo(solicitar_operacion)
        else:
            print("Opción no válida. Elige 1, 2, 3, 4 o 0.")
