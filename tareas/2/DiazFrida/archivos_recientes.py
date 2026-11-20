#!/usr/bin/env python3
import sys
import os
from datetime import datetime, timedelta

def main():
    if len(sys.argv) != 3:
        print(f"Invocación: {sys.argv[0]} <directorio> <días>")
        sys.exit(1)

    dir_path = sys.argv[1]
    try:
        max_dias = float(sys.argv[2])
    except ValueError:
        print("Error: El número de días debe ser un valor numérico.")
        sys.exit(1)

    if not os.path.isdir(dir_path):
        print(f"Error: '{dir_path}' no es un directorio válido.")
        sys.exit(1)

    ahora = datetime.now()
    limite_tiempo = ahora - timedelta(days=max_dias)

    archivos_info = []

    try:
        elementos = os.listdir(dir_path)
    except PermissionError:
        print(f"Error: Permiso denegado para leer el directorio '{dir_path}'.")
        sys.exit(1)

    for nombre in elementos:
        ruta_completa = os.path.join(dir_path, nombre)
        try:
            st = os.stat(ruta_completa)
            mtime = datetime.fromtimestamp(st.st_mtime)

            if mtime >= limite_tiempo:
                tamano = st.st_size
                modo = oct(st.st_mode)[2:]
                modificacion_str = mtime.strftime("%Y-%m-%d %H:%M")
                
                archivos_info.append({
                    'nombre': nombre,
                    'modificacion': modificacion_str,
                    'modo': modo,
                    'tamano': tamano
                })
        except (PermissionError, FileNotFoundError):
            continue

    archivos_info.sort(key=lambda x: x['nombre'])

    print(f"{'Nombre':<30} {'Modificación':<16} {'Modo':<8} {'Tamaño':<10}")
    print("=" * 66)

    for arch in archivos_info:
        print(f"{arch['nombre']:<30} {arch['modificacion']:<16} {arch['modo']:<8} {arch['tamano']:<10}")

if __name__ == "__main__":
    main()