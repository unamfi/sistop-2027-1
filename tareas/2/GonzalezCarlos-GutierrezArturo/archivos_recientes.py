import os
import sys
import time
from datetime import datetime


def main():
    # Se necesitan exactamente dos parámetros: directorio y número de días
    if len(sys.argv) != 3:
        print("Invocación: python archivos_recientes.py <directorio> <días>")
        sys.exit(1)

    ruta = sys.argv[1]

    # El número de días tiene que ser un entero
    try:
        dias = int(sys.argv[2])
    except ValueError:
        print("El número de días debe ser un entero")
        sys.exit(1)

    # Fecha límite: ahora menos N días (86400 segundos por día).
    # Lo modificado antes de este momento queda fuera de la lista.
    limite = time.time() - dias * 86400

    # Abre el directorio y ordena las entradas por nombre
    try:
        entradas = sorted(os.scandir(ruta), key=lambda e: e.name)
    except OSError as err:
        print(f"No se pudo abrir el directorio: {err}")
        sys.exit(1)

    # Encabezado de la tabla
    print(f"{'Nombre':<30} {'Modificación':<16} {'Modo':<6} Tamaño")
    print("=" * 62)

    for e in entradas:
        info = e.stat()
        # Solo se imprimen los archivos modificados dentro del plazo
        if info.st_mtime >= limite:
            fecha = datetime.fromtimestamp(info.st_mtime).strftime("%Y-%m-%d %H:%M")
            # Modo en octal de 6 dígitos (ej. 100644) y tamaño en bytes
            print(f"{e.name:<30} {fecha:<16} {info.st_mode:06o} {info.st_size}")


if __name__ == "__main__":
    main()