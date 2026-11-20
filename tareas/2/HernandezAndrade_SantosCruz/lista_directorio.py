#!/usr/bin/env/python3
'''
Tarea 2: Obteniendo información de un directorio
Programa que entregue una lista parcial de los archivos contenidos en un directorio.

Datos:
Universidad Nacional Autónoma de México
Facultad de Ingeniería
Sistemas Operativos -> Grupo 7
Profesor: Gunnar Eyal Wolf Iszaevich
Hecho por: 
- Hernández Andrade Miguel Ángel
- Santos Cruz Lair Abraham

Restricciones:
- El programa no debe ser interactivo, debe obtener todos sus parámetros de su invocación desde la línea de comandos.
- El programa recibe dos parámetros: La ruta del directorio que va a procesar y el número de dias.
- El programa debe abrir el directorio que fue especificado como primer parámetro, e imprimir todos aquellos archivos 
cuya última modificación tenga el número de días especificado o menos.
- La salida del programa debe presentarse ordenada lexicográficamente por nombre de archivo. El programa debe imprimir
el nombre del archivo, su longitud, la fecha en que fue modifcado por última vez, y el modo (los permisos) que tiene.
- Su programa no debe llamar a ningún programa externo para obtener información, todo debe ser hecho desde el lenguaje que hayan elegido para implementar (y de ser posible, desde su biblioteca estándar).

'''
# Importaciones
import sys
import os
from datetime import datetime, timedelta

# Función para agregar un archivo a la lista de archivos si es que cumple con la condición de fecha

# Función para enlistar archivos según la ruta del directorio dado y el número de días especificado.
def enlistar_archivos(ruta_directorio, n):
    # Obtenemos la fecha actual y la fecha límite según n
    fecha_actual = datetime.now()
    fecha_limite = fecha_actual - timedelta(days=n)
    fecha_limite = fecha_limite.timestamp()

    # Creamos una lista para almacenar los archivos del directorio
    archivos = []

    # Recorremos los archivos del directorio y verificamos su fecha de modificación
    for archivo in os.listdir(ruta_directorio):
        ruta_archivo = os.path.join(ruta_directorio, archivo)
        if os.path.isfile(ruta_archivo):
            ultima_fecha = os.path.getmtime(ruta_archivo)
            # Si la fecha de modificacón fue después de la límite, agregamos el archivo a la lista.
            if ultima_fecha >= fecha_limite:
                archivos.append(archivo)
    
    return archivos

# Función para imprimir los archivos validados en el directorio
def imprimir_archivos(ruta_directorio, archivos):
    # Ordenamos los archivos lexicográficamente
    archivos.sort()

    # Imprimimos la información de cada archivo
    for archivo in archivos:
        ruta_archivo = os.path.join(ruta_directorio, archivo)
        nombre = os.path.basename(ruta_archivo)
        fecha_mod = os.path.getmtime(ruta_archivo)
        fecha_impr = datetime.fromtimestamp(fecha_mod).strftime("%Y-%m-%d %H:%M")
        modo = f"{os.stat(ruta_archivo).st_mode:06o}" 
        tamano = os.path.getsize(ruta_archivo)
        print(f"{nombre}\t|{fecha_impr}\t|{modo}\t\t|{tamano}\t")

def main():
    # Verificamos los parámetros de entrada
    if len(sys.argv) != 3:
        print(f"Invocación: {sys.argv[0]} <directorio> <días>")
        sys.exit(1)
    
    # Leemos los parámetros de la línea de comandos
    ruta_directorio = sys.argv[1]
    try:
        n = int(sys.argv[2])
    except ValueError:
        print("Error: El segundo valor ingresado debe ser un número entero (días).")
        sys.exit(1)

    # Invocamos las funciones para enlistar archivos e imprimirlos
    archivos = enlistar_archivos(ruta_directorio, n)
    print("\tNombre\t|\tModificación\t|\tModo\t|\tTamaño\t")
    print("-------------------------------------------------------------------------------------")
    imprimir_archivos(ruta_directorio, archivos)

if __name__ == "__main__":
    main()

