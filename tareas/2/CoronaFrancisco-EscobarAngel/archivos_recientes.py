#!/usr/bin/python3
import math
import os
import stat
import sys
import time

def uso():
    print(f'Invocación: {sys.argv[0]} <directorio> <días>')
    sys.exit(1)

def lee_parametros():
    if len(sys.argv) != 3 or not os.path.isdir(sys.argv[1]):
        uso()
    try:
        dias = float(sys.argv[2])
    except ValueError:
        uso()
    if not math.isfinite(dias) or dias < 0:
        uso()
    return sys.argv[1], dias

def busca_recientes(directorio, limite):
    archivos = []
    with os.scandir(directorio) as entradas:
        for entrada in entradas:
            try:
                info = entrada.stat(follow_symlinks=False)
            except OSError as e:
                print(f'No se pudo leer {entrada.name}: {e.strerror}', file=sys.stderr)
                continue
            if info.st_mtime >= limite:
                archivos.append((entrada.name, info))
    return sorted(archivos, key=lambda archivo: archivo[0])

def imprime_tabla(archivos):
    ancho = max([30] + [len(nombre) for nombre, info in archivos])
    print(f'{"Nombre":{ancho}} {"Modificación":16} {"Modo":6} {"Permisos":10} Tamaño')
    print('=' * (ancho + 43))
    total = 0
    for nombre, info in archivos:
        fecha = time.strftime('%Y-%m-%d %H:%M', time.localtime(info.st_mtime))
        permisos = stat.filemode(info.st_mode)
        print(f'{nombre:{ancho}} {fecha} {info.st_mode:06o} {permisos} {info.st_size}')
        total += info.st_size
    print(f'\n{len(archivos)} archivos, {total} bytes en total')

directorio, dias = lee_parametros()
limite = time.time() - dias * 24 * 60 * 60
try:
    archivos = busca_recientes(directorio, limite)
except OSError as e:
    print(f'No se pudo abrir {directorio}: {e.strerror}', file=sys.stderr)
    sys.exit(1)
imprime_tabla(archivos)
