#!/usr/bin/env python3

#Peralta Rojas Jose Daniel Tarea 2
import sys
import os
import stat
import time
from datetime import datetime
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="Lista archivos en un directorio dentro de los últimos N dias."
    )
    parser.add_argument("directorio", help="Ruta del directorio")
    parser.add_argument("dias", type=float, help="Num de días como limite de modificacion")
    
    args = parser.parse_args()

    directorio = args.directorio
    dias_limite = args.dias

    if dias_limite < 0:
        print("Error, el número de dias debe ser un valor positivo", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(directorio):
        print(f"Error, la ruta '{directorio}' no existe.", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(directorio):
        print(f"Error, la ruta '{directorio}' no es un directorio valio.", file=sys.stderr)
        sys.exit(1)

    tiempo_actual = time.time()
    segundos_limite = dias_limite * 86400  # porque un dia son 86400 segundo        
    
    entradas = os.listdir(directorio)

    # Ordenamiento lexicográfico estricto por nombre de archivo
    entradas.sort()

    # Formato de salida
    print(f"{'MODO':<11} {'TAMAÑO (B)':<12} {'ÚLTIMA MODIFICACIÓN':<20} {'NOMBRE'}")
    print("-" * 65)

    archivos_procesados = 0

    for nombre in entradas:
        ruta_completa = os.path.join(directorio, nombre)

        # Obtención de metadatos
        info = os.stat(ruta_completa)

        # Filtrar solo archivos
        if not stat.S_ISREG(info.st_mode):
            continue

        mtime = info.st_mtime
        antiguedad_segundos = tiempo_actual - mtime

        if antiguedad_segundos <= segundos_limite:
            # Formatear el modo de permisos
            permisos_str = stat.filemode(info.st_mode)
            permisos_octal = oct(info.st_mode & 0o777)
            
            # Formatear la fecha de modificacion
            fecha_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            longitud = info.st_size

            print(f"{permisos_str:<11} {longitud:<12} {fecha_str:<20} {nombre}")
            archivos_procesados += 1

if __name__ == "__main__":
    main()