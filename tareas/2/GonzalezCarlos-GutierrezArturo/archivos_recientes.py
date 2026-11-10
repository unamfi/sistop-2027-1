import os
import sys
import time
from datetime import datetime


def main():
    if len(sys.argv) != 3:
        print("Invocación: python archivos_recientes.py <directorio> <días>")
        sys.exit(1)

    ruta = sys.argv[1]
    try:
        dias = int(sys.argv[2])
    except ValueError:
        print("El número de días debe ser un entero")
        sys.exit(1)

    limite = time.time() - dias * 86400

    try:
        entradas = sorted(os.scandir(ruta), key=lambda e: e.name)
    except OSError as err:
        print(f"No se pudo abrir el directorio: {err}")
        sys.exit(1)

    print(f"{'Nombre':<30} {'Modificación':<16} {'Modo':<6} Tamaño")
    print("=" * 62)
    for e in entradas:
        info = e.stat()
        if info.st_mtime >= limite:
            fecha = datetime.fromtimestamp(info.st_mtime).strftime("%Y-%m-%d %H:%M")
            print(f"{e.name:<30} {fecha:<16} {info.st_mode:06o} {info.st_size}")


if __name__ == "__main__":
    main()