
import os
import sys
import time
from datetime import datetime


def listar_archivos(directorio, dias):
    """Muestra los elementos modificados en los ultimos dias."""

    ahora = time.time()
    limite = ahora - (dias * 24 * 60 * 60)
    archivos = []

    # Abrimos el directorio y revisamos sus elementos
    with os.scandir(directorio) as entradas:
        for entrada in entradas:
            datos = entrada.stat(follow_symlinks=False)

            # Comprobamos su ultima modificacion
            if limite <= datos.st_mtime <= ahora:
                nombre = entrada.name
                fecha = datetime.fromtimestamp(
                    datos.st_mtime
                ).strftime("%Y-%m-%d %H:%M")

                modo = f"{datos.st_mode:06o}"
                tamano = datos.st_size

                archivos.append(
                    (nombre, fecha, modo, tamano)
                )

    # Ordenamos alfabeticamente por nombre
    archivos.sort(key=lambda archivo: archivo[0])

    # Ajustamos el ancho para nombres largos
    ancho = max(
        [30] + [len(archivo[0]) for archivo in archivos]
    )

    encabezado = (
        f"{'Nombre':<{ancho}}  "
        f"{'Modificación':<16}  "
        f"{'Modo':<6}  "
        f"{'Tamaño':>8}"
    )

    print(encabezado)
    print("=" * len(encabezado))

    for nombre, fecha, modo, tamano in archivos:
        print(
            f"{nombre:<{ancho}}  "
            f"{fecha:<16}  "
            f"{modo:<6}  "
            f"{tamano:>8}"
        )


def main():
    # Verificamos la cantidad de argumentos
    if len(sys.argv) != 3:
        print(
            f"Invocación: {sys.argv[0]} "
            "<directorio> <días>"
        )
        return 1

    directorio = sys.argv[1]

    # Validamos el numero de dias
    try:
        dias = int(sys.argv[2])
    except ValueError:
        print("Error: los días deben ser un número entero.")
        return 1

    if dias < 0:
        print("Error: el número de días no puede ser negativo.")
        return 1

    # Comprobamos que el directorio exista
    if not os.path.isdir(directorio):
        print("Error: el directorio indicado no existe.")
        return 1

    # Ejecutamos la consulta
    try:
        listar_archivos(directorio, dias)
    except OSError as error:
        print(f"Error al leer el directorio: {error}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
