#!/usr/bin/env python3
import sys
import os
import time
from datetime import datetime

if len(sys.argv) != 3:
    print(f"Invocación: {sys.argv[0]} <directorio> <días>")
    sys.exit(1)

directorio = sys.argv[1]
dias = float(sys.argv[2])

limite = time.time() - (dias * 86400)

resultados = []

try:
    archivos = os.listdir(directorio)
except:
    print("Error: No se pudo leer el directorio")
    sys.exit(1)

for nombre in archivos:
    ruta = os.path.join(directorio, nombre)
    try:
        stats = os.lstat(ruta)
        if stats.st_mtime >= limite:
            resultados.append((nombre, stats))
    except:
        pass

resultados.sort(key=lambda x: x[0])

print(f"{'Nombre':<30} {'Modificación':<16} {'Modo':<6} Tamaño")
print("==============================================================")

for nombre, stats in resultados:
    fecha = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M')
    modo = f"{stats.st_mode:06o}" 
    tamano = stats.st_size
    
    print(f"{nombre:<30} {fecha:<16} {modo:<6} {tamano}")
