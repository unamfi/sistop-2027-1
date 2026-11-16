#!/usr/bin/python3
import os
import struct
import sys
import time

def uso():
    print(f'Invocación: {sys.argv[0]} <imagen de FiUnamFS>')
    sys.exit(1)

def lee_superbloque(ruta):
    with open(ruta, 'rb') as disco:
        datos = disco.read(52)
    # Si no es FiUnamFS 27-1 no tocamos nada, podríamos echar a perder el archivo
    if datos[0:8] != b'FiUnamFS' or datos[10:14] != b'27-1':
        print(f'{ruta} no es un FiUnamFS versión 27-1')
        sys.exit(1)
    etiqueta = datos[20:36].decode('ascii').rstrip('\x00 ')
    return (etiqueta,) + struct.unpack('<III', datos[40:52])

def fecha(texto):
    return f'{texto[0:4]}-{texto[4:6]}-{texto[6:8]} {texto[8:10]}:{texto[10:12]}'

def lee_directorio(disco):
    entradas = []
    disco.seek(tam_cluster)
    for num in range(clusters_dir * tam_cluster // 64):
        datos = disco.read(64)
        if datos[0:1] != b'F':
            continue
        tam, cluster = struct.unpack('<II', datos[16:24])
        entradas.append({
            'num': num,
            # el nombre viene relleno con espacios y termina en \0
            'nombre': datos[1:16].decode('ascii').rstrip('\x00 '),
            'tam': tam,
            'cluster': cluster,
            'creado': datos[24:38].decode('ascii'),
            'modificado': datos[38:52].decode('ascii'),
        })
    return entradas

def listar(disco):
    entradas = lee_directorio(disco)
    lineas = [f'{"Nombre":15} {"Tamaño":>8} {"Cluster":>7}  {"Creación":16}  Modificación']
    lineas.append('=' * 68)
    for e in entradas:
        lineas.append(f'{e["nombre"]:15} {e["tam"]:8} {e["cluster"]:7}  {fecha(e["creado"])}  {fecha(e["modificado"])}')
    lineas.append(f'\n{len(entradas)} archivos')
    return '\n'.join(lineas)

if len(sys.argv) != 2 or not os.path.isfile(sys.argv[1]):
    uso()
etiqueta, tam_cluster, clusters_dir, clusters_total = lee_superbloque(sys.argv[1])
print(f'Volumen: {etiqueta} ({clusters_total} clusters de {tam_cluster} bytes)')
with open(sys.argv[1], 'rb') as disco:
    print(listar(disco))
