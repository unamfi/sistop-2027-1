#!/usr/bin/env python3
"""
Obteniendo información de un directorio, tarea 2 de Sistemas Operativos
(sistop-2027-1)
Sebastián Ladrón de Guevara Castro y Jessica Estefani Pérez Báez

Recibe un directorio y un número de días, e imprime los archivos de ese
directorio cuya última modificación fue hace ese número de días o menos.
De cada archivo muestra el nombre, la fecha de modificación, el modo y el
tamaño, ordenados lexicográficamente por nombre.

Toda la información se obtiene con la biblioteca estándar de Python, sin
llamar a ningún programa externo.

Ejemplos de uso
      ./archivos_recientes.py /tmp 1
      ./archivos_recientes.py ~/Documents 7
"""
import os
import sys
import time

SEGUNDOS_POR_DIA = 24 * 60 * 60


# ─── Parámetros de la línea de comandos ─────────────────────────────────────

def uso():
    """Muestra cómo se invoca el programa y termina con error."""
    print(f'Invocación: {sys.argv[0]} <directorio> <días>', file=sys.stderr)
    sys.exit(1)


def leer_parametros():
    """Regresa el directorio y los días que se pasaron al programa.

    El programa no es interactivo, así que si falta algún parámetro o los
    días no son válidos solo se muestra la forma de uso.
    """
    if len(sys.argv) != 3:
        uso()

    directorio = sys.argv[1]
    try:
        dias = float(sys.argv[2])          # acepta decimales, 0.5 = 12 horas
    except ValueError:
        print(f'Error: "{sys.argv[2]}" no es un número de días válido',
              file=sys.stderr)
        uso()
    if dias < 0:
        print('Error: el número de días no puede ser negativo', file=sys.stderr)
        uso()

    return directorio, dias


# ─── Lectura del directorio ─────────────────────────────────────────────────

def archivos_recientes(directorio, dias):
    """Lista de (nombre, información) de los archivos modificados en los
    últimos `dias` días, ordenada por nombre."""
    limite = time.time() - dias * SEGUNDOS_POR_DIA
    encontrados = []

    # os.scandir abre el directorio y entrega sus entradas una por una
    with os.scandir(directorio) as entradas:
        for entrada in entradas:
            # Los archivos ocultos se omiten, igual que hace ls sin -a
            if entrada.name.startswith('.'):
                continue

            # follow_symlinks=False equivale a lstat. Un enlace simbólico se
            # describe a sí mismo y no al archivo al que apunta, así que un
            # enlace roto no provoca un error.
            try:
                info = entrada.stat(follow_symlinks=False)
            except OSError:
                # El archivo se borró entre que se leyó el directorio y que
                # se pidió su información (pasa seguido en /tmp)
                continue

            if info.st_mtime >= limite:
                encontrados.append((entrada.name, info))

    # sorted compara las cadenas por el código de cada carácter, que es el
    # orden lexicográfico. Por eso las mayúsculas quedan antes que las
    # minúsculas, igual que en el ejemplo del enunciado.
    return sorted(encontrados, key=lambda par: par[0])


# ─── Salida ─────────────────────────────────────────────────────────────────

def imprimir(archivos):
    """Imprime la tabla con el mismo formato que el ejemplo del enunciado."""
    print(f'{"Nombre":<30} {"Modificación":<16} {"Modo":<6} Tamaño')
    print('=' * 62)
    for nombre, info in archivos:
        fecha = time.strftime('%Y-%m-%d %H:%M', time.localtime(info.st_mtime))
        # st_mode incluye el tipo de archivo además de los permisos. En octal
        # un directorio se ve como 040755 y un archivo regular como 100644.
        print(f'{nombre:<30} {fecha} {info.st_mode:06o} {info.st_size}')


def main():
    directorio, dias = leer_parametros()
    try:
        archivos = archivos_recientes(directorio, dias)
    except FileNotFoundError:
        print(f'Error: no existe el directorio {directorio}', file=sys.stderr)
        sys.exit(2)
    except NotADirectoryError:
        print(f'Error: {directorio} no es un directorio', file=sys.stderr)
        sys.exit(2)
    except PermissionError:
        print(f'Error: no hay permiso para leer {directorio}', file=sys.stderr)
        sys.exit(2)
    imprimir(archivos)


if __name__ == '__main__':
    main()
