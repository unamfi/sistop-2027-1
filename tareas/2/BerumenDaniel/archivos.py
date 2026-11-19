#!/usr/bin/env python3
# Lista los archivos de un directorio modificados en los últimos N días,
# con su fecha de modificación, modo (permisos) y tamaño.

import os # Acceso al sistema de archivos (listdir, lstat, path.join)
import sys # Argumentos de línea de comandos y salida del programa
import time # Hora actual y formato de fechas

# Verifica que se reciban los dos parámetros; si no, muestra cómo invocarlo
if len(sys.argv) < 3:
    print("Invocación: " + sys.argv[0] + " <directorio> <días>")
    sys.exit(1)

# Primer parámetro: ruta del directorio a procesar
directorio = sys.argv[1]

# Segundo parámetro: número de días, debe ser un entero
try:
    dias = int(sys.argv[2])
except ValueError:
    print("Error: el número de días debe ser un entero")
    sys.exit(1)

# Obtiene los nombres de las entradas del directorio
try:
    lista = os.listdir(directorio)
except OSError as e:
    print("Error: no se pudo abrir el directorio: " + str(e))
    sys.exit(1)

# Ordena por nombre
lista.sort()

# Momento actual en segundos desde la época Unix
ahora = time.time()

# Encabezado de la tabla
print("Nombre                         Modificación     Modo   Tamaño")
print("==============================================================")

for nombre in lista:
    # Construye la ruta completa de la entrada
    ruta = os.path.join(directorio, nombre)

    # Obtiene los metadatos
    # si la entrada no puede leerse, se omite
    try:
        info = os.lstat(ruta)
    except OSError:
        continue

    # Antigüedad de la última modificación, convertida de segundos a días
    diferencia = ahora - info.st_mtime
    dias_archivo = diferencia / 86400

    # Solo se muestran las entradas modificadas hace "dias" días o menos
    if dias_archivo <= dias:
        # Fecha de modificación en formato AAAA-MM-DD HH:MM, hora local
        fecha = time.strftime("%Y-%m-%d %H:%M", time.localtime(info.st_mtime))

        # Modo en octal sin el prefijo "0o", rellenado con ceros a 6 dígitos
        # (ej. 040755 para directorios, 100644 para archivos regulares)
        modo = oct(info.st_mode)
        modo = modo[2:]
        while len(modo) < 6:
            modo = "0" + modo

        # Rellena el nombre con espacios hasta 30 caracteres para alinear columnas
        nombre2 = nombre
        while len(nombre2) < 30:
            nombre2 = nombre2 + " "

        # Imprime la línea: nombre, fecha, modo y tamaño en bytes
        print(nombre2 + " " + fecha + " " + modo + " " + str(info.st_size))