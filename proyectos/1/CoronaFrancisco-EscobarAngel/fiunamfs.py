#!/usr/bin/python3
import os
import struct
import sys
import time

# Así se ven las entradas vacías en la imagen de ejemplo
entrada_vacia = b'-' + b'#' * 14 + b'\x00' + bytes(8) + b'0' * 28 + bytes(12)

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

def clusters_que_ocupa(tam):
    return max(1, -(-tam // tam_cluster))

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

def busca(disco, nombre):
    for entrada in lee_directorio(disco):
        if entrada['nombre'] == nombre:
            return entrada
    raise ValueError(f'No existe {nombre} en FiUnamFS')

def busca_espacio(entradas, tam):
    # Asignación contigua: el primer hueco entre archivos donde quepa completo
    inicio = 1 + clusters_dir
    for entrada in sorted(entradas, key=lambda e: e['cluster']):
        if entrada['cluster'] - inicio >= clusters_que_ocupa(tam):
            return inicio
        inicio = max(inicio, entrada['cluster'] + clusters_que_ocupa(entrada['tam']))
    if clusters_total - inicio >= clusters_que_ocupa(tam):
        return inicio
    raise ValueError('No hay espacio contiguo suficiente en FiUnamFS')

def escribe_entrada(disco, num, datos):
    disco.seek(tam_cluster + num * 64)
    disco.write(datos)

def listar(disco):
    entradas = lee_directorio(disco)
    lineas = [f'{"Nombre":15} {"Tamaño":>8} {"Cluster":>7}  {"Creación":16}  Modificación']
    lineas.append('=' * 68)
    for e in entradas:
        lineas.append(f'{e["nombre"]:15} {e["tam"]:8} {e["cluster"]:7}  {fecha(e["creado"])}  {fecha(e["modificado"])}')
    lineas.append(f'\n{len(entradas)} archivos')
    return '\n'.join(lineas)

def copia_a_equipo(disco, nombre, destino):
    entrada = busca(disco, nombre)
    if os.path.isdir(destino):
        destino = os.path.join(destino, nombre)
    if os.path.exists(destino):
        raise ValueError(f'Ya existe {destino} en tu equipo')
    disco.seek(entrada['cluster'] * tam_cluster)
    datos = disco.read(entrada['tam'])
    with open(destino, 'wb') as archivo:
        archivo.write(datos)
    return f'Se copió {nombre} a {destino} ({len(datos)} bytes)'

def copia_a_fiunamfs(disco, origen):
    nombre = os.path.basename(origen)
    if not nombre.isascii() or not nombre.isprintable() or len(nombre) > 14:
        raise ValueError('El nombre debe ser ASCII y medir máximo 14 caracteres')
    with open(origen, 'rb') as archivo:
        datos = archivo.read()
    entradas = lee_directorio(disco)
    if any(e['nombre'] == nombre for e in entradas):
        raise ValueError(f'Ya existe {nombre} en FiUnamFS')
    ocupadas = [e['num'] for e in entradas]
    libres = [num for num in range(clusters_dir * tam_cluster // 64) if num not in ocupadas]
    if not libres:
        raise ValueError('El directorio está lleno')
    cluster = busca_espacio(entradas, len(datos))
    disco.seek(cluster * tam_cluster)
    disco.write(datos)
    creado = time.strftime('%Y%m%d%H%M%S')
    modificado = time.strftime('%Y%m%d%H%M%S', time.localtime(os.path.getmtime(origen)))
    entrada = b'F' + nombre.ljust(14).encode('ascii') + b'\x00'
    entrada += struct.pack('<II', len(datos), cluster)
    entrada += creado.encode('ascii') + modificado.encode('ascii') + bytes(12)
    escribe_entrada(disco, libres[0], entrada)
    return f'Se copió {nombre} a FiUnamFS en el cluster {cluster}'

def elimina(disco, nombre):
    entrada = busca(disco, nombre)
    # Basta con liberar la entrada; los datos se quedan hasta que otro archivo ocupe ese espacio
    escribe_entrada(disco, entrada['num'], entrada_vacia)
    return f'Se eliminó {nombre}'

def pide(operacion, *args):
    try:
        return operacion(disco, *args)
    except (OSError, ValueError, UnicodeError) as e:
        return f'Error: {e}'

def menu():
    while True:
        print('\n1) Listar  2) Copiar a mi equipo  3) Copiar a FiUnamFS  4) Eliminar  5) Salir')
        opcion = input('Opción: ').strip()
        if opcion == '1':
            print(pide(listar))
        elif opcion == '2':
            nombre = input('Archivo de FiUnamFS: ').strip()
            destino = input(f'Guardar como [{nombre}]: ').strip() or nombre
            print(pide(copia_a_equipo, nombre, destino))
        elif opcion == '3':
            origen = input('Archivo de tu equipo: ').strip()
            print(pide(copia_a_fiunamfs, origen))
        elif opcion == '4':
            nombre = input('Archivo a eliminar: ').strip()
            if input(f'¿Seguro que quieres borrar {nombre}? (s/n): ').strip().lower() == 's':
                print(pide(elimina, nombre))
        elif opcion == '5':
            return
        else:
            print('Opción no válida')

if len(sys.argv) != 2 or not os.path.isfile(sys.argv[1]):
    uso()
etiqueta, tam_cluster, clusters_dir, clusters_total = lee_superbloque(sys.argv[1])
print(f'Volumen: {etiqueta} ({clusters_total} clusters de {tam_cluster} bytes)')
with open(sys.argv[1], 'r+b') as disco:
    try:
        menu()
    except (EOFError, KeyboardInterrupt):
        print()
