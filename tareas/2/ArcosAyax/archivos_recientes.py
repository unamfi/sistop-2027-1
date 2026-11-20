import os
import sys
import stat
from datetime import datetime, timedelta


def mostrar_uso():
    print(f"Invocacion: {sys.argv[0]} <directorio> <dias>")


if len(sys.argv) != 3:
    mostrar_uso()
    sys.exit(1)

directorio = sys.argv[1]

try:
    dias = int(sys.argv[2])
except ValueError:
    print("El numero de dias debe ser un entero.")
    sys.exit(1)

if dias < 0:
    print("El numero de dias no puede ser negativo.")
    sys.exit(1)

if not os.path.isdir(directorio):
    print("La ruta indicada no es un directorio valido.")
    sys.exit(1)

limite = datetime.now() - timedelta(days=dias)

resultados = []

for nombre in os.listdir(directorio):
    ruta = os.path.join(directorio, nombre)

    try:
        info = os.stat(ruta)
    except OSError:
        continue

    fecha_modificacion = datetime.fromtimestamp(info.st_mtime)

    if fecha_modificacion >= limite:
        modo = format(info.st_mode, "06o")
        tamano = info.st_size

        resultados.append(
            (nombre, fecha_modificacion, modo, tamano)
        )

resultados.sort(key=lambda elemento: elemento[0])

print(f"{'Nombre':30} {'Modificacion':16} {'Modo':6} {'Tamano'}")
print("=" * 65)

for nombre, fecha, modo, tamano in resultados:
    fecha_texto = fecha.strftime("%Y-%m-%d %H:%M")

    print(
        f"{nombre:30} "
        f"{fecha_texto:16} "
        f"{modo:6} "
        f"{tamano}"
    )
