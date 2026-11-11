import os
import stat
import sys
import time

SEGUNDOS_POR_DIA = 86400

def main(argv):
    if len(argv) != 3:
        print(f"u{argv[0]} Escribe: <directorio> <dias>", file=sys.stderr)
        return 1

    ruta = argv[1]
    try:
        dias = int(argv[2])
        if dias < 0:
            raise ValueError
    except ValueError:
        print(f"Error: '{argv[2]}' no es un número de días válido "
              "(entero >= 0).", file=sys.stderr)
        return 1

    limite = time.time() - dias * SEGUNDOS_POR_DIA
    try:
        nombres = os.listdir(ruta)
    except OSError as e:
        print(f"Error: no se pudo abrir el directorio")
        return 1

    nombres.sort()
    for nombre in nombres:
        completa = os.path.join(ruta, nombre)

        try:
            info = os.lstat(completa)
        except OSError as e:
            print(f"Aviso: no se pudo leer '{nombre}': {e}", file=sys.stderr)
            continue

        if not stat.S_ISREG(info.st_mode):
            continue
        if info.st_mtime < limite:
            continue

        fecha = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info.st_mtime))
        modo = stat.filemode(info.st_mode)
        print(f"{nombre}\t{info.st_size}\t{fecha}\t{modo}")

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))