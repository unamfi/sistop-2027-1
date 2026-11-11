#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarea 2 - Obteniendo información de un directorio
Sistemas Operativos 2027-1 · Facultad de Ingeniería, UNAM
Autor: Cipriano Amador Johan Tadeo

Lista, ordenados lexicográficamente por nombre, los archivos de un
directorio cuya última modificación tenga a lo más N días de antigüedad,
mostrando su fecha de modificación, su modo (permisos) y su tamaño.

Uso:
    archivos_recientes.py <directorio> <días>

Solo usa la biblioteca estándar de Python (os, sys, time); no invoca
ningún programa externo.
"""

import os
import sys
import time

SEGUNDOS_POR_DIA = 24 * 60 * 60
ANCHO_NOMBRE = 30


def uso():
    """Muestra la forma de invocación y termina con error."""
    print(f"Invocación: {sys.argv[0]} <directorio> <días>", file=sys.stderr)
    sys.exit(1)


def leer_parametros():
    """Valida y devuelve (directorio, días) a partir de la línea de comandos."""
    if len(sys.argv) != 3:
        uso()

    directorio = sys.argv[1]
    try:
        dias = float(sys.argv[2])
    except ValueError:
        print(f"Error: '{sys.argv[2]}' no es un número de días válido",
              file=sys.stderr)
        uso()

    if dias < 0:
        print("Error: el número de días no puede ser negativo", file=sys.stderr)
        uso()

    if not os.path.isdir(directorio):
        print(f"Error: '{directorio}' no es un directorio", file=sys.stderr)
        sys.exit(2)

    return directorio, dias


def archivos_recientes(directorio, dias):
    """Devuelve una lista de (nombre, stat) modificados hace <= `dias` días."""
    limite = time.time() - dias * SEGUNDOS_POR_DIA
    recientes = []

    # os.scandir abre el directorio y lo recorre entrada por entrada
    with os.scandir(directorio) as entradas:
        for entrada in entradas:
            try:
                # lstat: no seguimos ligas simbólicas, reportamos la liga misma
                info = entrada.stat(follow_symlinks=False)
            except OSError as e:
                print(f"Aviso: no se pudo leer '{entrada.name}': {e.strerror}",
                      file=sys.stderr)
                continue

            if info.st_mtime >= limite:
                recientes.append((entrada.name, info))

    # Orden lexicográfico por nombre de archivo
    recientes.sort(key=lambda par: par[0])
    return recientes


def main():
    directorio, dias = leer_parametros()

    try:
        lista = archivos_recientes(directorio, dias)
    except PermissionError:
        print(f"Error: sin permiso para leer '{directorio}'", file=sys.stderr)
        sys.exit(3)

    encabezado = f"{'Nombre':<{ANCHO_NOMBRE}} {'Modificación':<16} {'Modo':<6} Tamaño"
    print(encabezado)
    print("=" * len(encabezado))

    for nombre, info in lista:
        fecha = time.strftime("%Y-%m-%d %H:%M", time.localtime(info.st_mtime))
        modo = f"{info.st_mode:06o}"
        print(f"{nombre:<{ANCHO_NOMBRE}} {fecha} {modo} {info.st_size}")


if __name__ == "__main__":
    main()
