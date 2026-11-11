#!/usr/bin/env python3
import os
import sys
import stat
import time
from datetime import datetime

def obtener_archivos_recientes(ruta_dir, dias_limite):
    ahora = time.time()
    segundos_limite = dias_limite * 86400  # 1 día = 86400 segundos
    
    if not os.path.isdir(ruta_dir):
        print(f"Error: La ruta '{ruta_dir}' no es un directorio válido.")
        sys.exit(1)
        
    archivos = []
    
    try:
        entradas = os.listdir(ruta_dir)
    except PermissionError:
        print(f"Error: Sin permisos para acceder a '{ruta_dir}'.")
        sys.exit(1)

    for nombre in entradas:
        ruta_completa = os.path.join(ruta_dir, nombre)
        try:
            info = os.stat(ruta_completa)
            tiempo_mod = info.st_mtime
            diferencia = ahora - tiempo_mod
            
            # Filtrar archivos cuyo tiempo de modificación esté dentro del rango especificado
            if diferencia <= segundos_limite:
                modo_octal = f"{stat.S_IMODE(info.st_mode) | (stat.S_IFMT(info.st_mode)):06o}"
                fecha_formateada = datetime.fromtimestamp(tiempo_mod).strftime('%Y-%m-%d %H:%M')
                tamano = info.st_size
                archivos.append((nombre, fecha_formateada, modo_octal, tamano))
        except FileNotFoundError:
            continue

    # Ordenar lexicográficamente por nombre de archivo
    archivos.sort(key=lambda x: x[0])
    return archivos

def main():
    if len(sys.argv) != 3:
        print(f"Invocación: {sys.argv[0]} <directorio> <días>")
        sys.exit(1)

    ruta_dir = sys.argv[1]
    
    try:
        dias_limite = float(sys.argv[2])
    except ValueError:
        print("Error: El segundo argumento (días) debe ser un número.")
        sys.exit(1)

    resultados = obtener_archivos_recientes(ruta_dir, dias_limite)

    # Imprimir encabezado idéntico al formato solicitado
    print(f"{'Nombre':<30} {'Modificación':<16} {'Modo':<6} {'Tamaño'}")
    print("=" * 65)

    for nombre, mod, modo, tamano in resultados:
        print(f"{nombre:<30} {mod:<16} {modo:<6} {tamano}")

if __name__ == "__main__":
    main()

