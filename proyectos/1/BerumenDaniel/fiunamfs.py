# fiunamfs.py
# aqui esta todo lo que sabe leer y escribir una imagen de FiUnamFS
# (superbloque, directorio y datos). fiunamfs_fuse.py usa estas funciones,
# y si se corre este archivo solo, sale un menu para probarlas sin FUSE

import struct
import os
from datetime import datetime

# lo que tiene que decir el superbloque para que la imagen sea valida
NOMBRE_FS = "FiUnamFS"
VERSION_FS = "27-1"

TAMANO_SECTOR = 512
# cada entrada del directorio mide 64 bytes
TAMANO_ENTRADA = 64


# lee un entero de 32 bits en little endian que empieza en 'posicion'
def leer_entero(archivo, posicion):
    archivo.seek(posicion)
    datos = archivo.read(4)
    # '<I' = little endian, entero sin signo de 4 bytes
    # unpack regresa una tupla, por eso el [0]
    numero = struct.unpack('<I', datos)[0]
    return numero


# lee un texto de 'longitud' bytes que empieza en 'posicion'
def leer_texto(archivo, posicion, longitud):
    archivo.seek(posicion)
    datos = archivo.read(longitud)
    texto = datos.decode('ascii')
    # en la imagen del profe los textos vienen con espacios y un \0 al final,
    # primero se quita el \0 y luego los espacios (al reves no funcionaba)
    texto = texto.replace('\x00', '')
    texto = texto.strip()
    return texto


# lee el cluster 0 (superbloque) y regresa sus datos en un diccionario
def leer_superbloque(ruta_imagen):
    archivo = open(ruta_imagen, 'rb')

    # las posiciones vienen de la especificacion del profe
    superbloque = {}
    superbloque['nombre'] = leer_texto(archivo, 0, 8)            # bytes 0 a 7
    superbloque['version'] = leer_texto(archivo, 10, 4)          # bytes 10 a 13
    superbloque['etiqueta'] = leer_texto(archivo, 20, 16)        # bytes 20 a 35
    superbloque['tamano_cluster'] = leer_entero(archivo, 40)     # bytes 40 a 43
    superbloque['clusters_directorio'] = leer_entero(archivo, 44)  # bytes 44 a 47
    superbloque['clusters_totales'] = leer_entero(archivo, 48)   # bytes 48 a 51

    archivo.close()
    return superbloque


# revisa que la imagen sea FiUnamFS version 27-1
def validar_superbloque(superbloque):
    # si no es FiUnamFS 27-1 no hay que tocarla porque se puede dañar
    if superbloque['nombre'] != NOMBRE_FS:
        print("Error: la imagen no es un sistema de archivos FiUnamFS")
        return False

    if superbloque['version'] != VERSION_FS:
        print("Error: la versión es", superbloque['version'], "y se esperaba", VERSION_FS)
        return False

    return True


# imprime los datos del superbloque
def mostrar_superbloque(superbloque):
    print("Sistema de archivos:", superbloque['nombre'])
    print("Versión:", superbloque['version'])
    print("Etiqueta del volumen:", superbloque['etiqueta'])
    print("Tamaño del cluster:", superbloque['tamano_cluster'], "bytes")
    print("Clusters del directorio:", superbloque['clusters_directorio'])
    print("Clusters totales:", superbloque['clusters_totales'])


# lee todas las entradas del directorio y regresa una lista solo con
# las que tienen un archivo (cada una es un diccionario)
def leer_directorio(ruta_imagen, superbloque):
    archivo = open(ruta_imagen, 'rb')

    tamano_cluster = superbloque['tamano_cluster']
    # el directorio empieza en el cluster 1, o sea en el byte 2048
    inicio_directorio = tamano_cluster
    # 4 clusters * 2048 bytes / 64 bytes por entrada = 128 entradas
    numero_entradas = (superbloque['clusters_directorio'] * tamano_cluster) // TAMANO_ENTRADA

    lista_archivos = []

    for i in range(numero_entradas):
        posicion = inicio_directorio + i * TAMANO_ENTRADA

        # cada entrada mide 64 bytes: tipo (1), nombre (15), tamaño (4),
        # cluster inicial (4), fecha creacion (14), fecha modificacion (14)
        # y lo demas no se usa
        entrada = {}
        # se guarda el numero de entrada para poder borrarla despues
        entrada['numero_entrada'] = i
        entrada['tipo'] = leer_texto(archivo, posicion, 1)
        entrada['nombre'] = leer_texto(archivo, posicion + 1, 15)
        entrada['tamano'] = leer_entero(archivo, posicion + 16)
        entrada['cluster_inicial'] = leer_entero(archivo, posicion + 20)
        entrada['fecha_creacion'] = leer_texto(archivo, posicion + 24, 14)
        entrada['fecha_modificacion'] = leer_texto(archivo, posicion + 38, 14)

        # las entradas vacias tienen '-' o el nombre empieza con #
        if entrada['tipo'] == 'F' and not entrada['nombre'].startswith('#'):
            lista_archivos.append(entrada)

    archivo.close()
    return lista_archivos


# convierte '20261105163124' en '2026-11-05 16:31:24' para que se lea mejor
def formatear_fecha(fecha):
    # si no mide 14 no tiene el formato esperado y se regresa como venia
    if len(fecha) != 14:
        return fecha
    anio = fecha[0:4]
    mes = fecha[4:6]
    dia = fecha[6:8]
    hora = fecha[8:10]
    minuto = fecha[10:12]
    segundo = fecha[12:14]
    return anio + "-" + mes + "-" + dia + " " + hora + ":" + minuto + ":" + segundo


# imprime la lista de archivos como tabla (para el menu)
def mostrar_directorio(lista_archivos):
    if len(lista_archivos) == 0:
        print("El directorio está vacío")
        return

    print("Nombre           Tamaño   Cluster  Creado               Modificado")
    print("---------------  -------  -------  -------------------  -------------------")
    for entrada in lista_archivos:
        # ljust y rjust rellenan con espacios para que las columnas queden alineadas
        nombre = entrada['nombre'].ljust(15)
        tamano = str(entrada['tamano']).rjust(7)
        cluster = str(entrada['cluster_inicial']).rjust(7)
        creado = formatear_fecha(entrada['fecha_creacion'])
        modificado = formatear_fecha(entrada['fecha_modificacion'])
        print(nombre, "", tamano, "", cluster, "", creado, "", modificado)

    print()
    print("Total de archivos:", len(lista_archivos))


# busca un archivo por nombre, regresa su entrada o None si no existe
def buscar_archivo(ruta_imagen, superbloque, nombre):
    lista_archivos = leer_directorio(ruta_imagen, superbloque)
    for entrada in lista_archivos:
        if entrada['nombre'] == nombre:
            return entrada
    return None


# regresa el contenido (bytes) de un archivo de FiUnamFS, o None si no existe
def leer_archivo(ruta_imagen, superbloque, nombre):
    entrada = buscar_archivo(ruta_imagen, superbloque, nombre)
    if entrada == None:
        print("Error: no existe el archivo", nombre)
        return None

    archivo = open(ruta_imagen, 'rb')
    # el archivo empieza en cluster_inicial * 2048 y esta todo seguido
    # (asignacion contigua), asi que basta con un solo read
    # solo se leen los bytes que dice el tamaño, lo que sobra del ultimo cluster es basura
    posicion = entrada['cluster_inicial'] * superbloque['tamano_cluster']
    archivo.seek(posicion)
    contenido = archivo.read(entrada['tamano'])
    archivo.close()

    return contenido


# copia un archivo de FiUnamFS a la computadora (operacion 2 del proyecto)
def copiar_a_equipo(ruta_imagen, superbloque, nombre, ruta_destino):
    contenido = leer_archivo(ruta_imagen, superbloque, nombre)
    if contenido == None:
        return False

    destino = open(ruta_destino, 'wb')
    destino.write(contenido)
    destino.close()

    print("Se copió", nombre, "a", ruta_destino, "(", len(contenido), "bytes )")
    return True


# regresa el numero de la primera entrada vacia del directorio, o -1 si esta lleno
def buscar_entrada_libre(ruta_imagen, superbloque):
    archivo = open(ruta_imagen, 'rb')

    tamano_cluster = superbloque['tamano_cluster']
    numero_entradas = (superbloque['clusters_directorio'] * tamano_cluster) // TAMANO_ENTRADA

    for i in range(numero_entradas):
        posicion = tamano_cluster + i * TAMANO_ENTRADA
        tipo = leer_texto(archivo, posicion, 1)
        nombre = leer_texto(archivo, posicion + 1, 15)
        # misma regla que en leer_directorio para saber si esta vacia
        if tipo == '-' or nombre.startswith('#'):
            archivo.close()
            return i

    archivo.close()
    return -1


# cuantos clusters ocupa un archivo de 'tamano' bytes (redondeando hacia arriba)
# ej: con clusters de 2048, 5000 bytes -> 2 completos y sobran 904 -> 3 clusters
def clusters_que_ocupa(tamano, tamano_cluster):
    clusters = tamano // tamano_cluster
    # si sobra algo hace falta un cluster mas
    if tamano % tamano_cluster != 0:
        clusters = clusters + 1
    # un archivo vacio igual ocupa un cluster
    if clusters == 0:
        clusters = 1
    return clusters


# busca donde poner un archivo que necesita 'clusters_necesarios' clusters seguidos
# regresa el cluster donde puede empezar, o -1 si no cabe en ningun lado
def buscar_hueco(ruta_imagen, superbloque, clusters_necesarios):
    tamano_cluster = superbloque['tamano_cluster']
    # los datos empiezan despues del superbloque (1) y el directorio (4) = cluster 5
    primer_cluster_datos = 1 + superbloque['clusters_directorio']
    total_clusters = superbloque['clusters_totales']

    # lista de lo que ya esta ocupado, cada archivo es [inicio, fin]
    # fin es el primer cluster que ya NO usa el archivo
    ocupados = []
    for entrada in leer_directorio(ruta_imagen, superbloque):
        inicio = entrada['cluster_inicial']
        clusters = clusters_que_ocupa(entrada['tamano'], tamano_cluster)
        ocupados.append([inicio, inicio + clusters])

    # se ordena por cluster de inicio para revisar el disco de principio a fin
    ocupados.sort()

    # first fit: busco el primer hueco entre los archivos donde quepa todo
    # el archivo junto (la asignacion es contigua)
    # 'actual' es desde donde esta libre el disco hasta ahora
    actual = primer_cluster_datos
    for rango in ocupados:
        inicio = rango[0]
        fin = rango[1]
        # el hueco va de 'actual' hasta donde empieza el siguiente archivo
        if inicio - actual >= clusters_necesarios:
            return actual
        # no cupo, se brinca al final de este archivo y se sigue buscando
        if fin > actual:
            actual = fin

    # ultimo hueco: desde el ultimo archivo hasta el final del disco
    if total_clusters - actual >= clusters_necesarios:
        return actual

    return -1


# revisa que un nombre se pueda usar en FiUnamFS
def validar_nombre(nombre):
    if nombre == "":
        print("Error: el nombre está vacío")
        return False

    # el campo del nombre en la entrada mide 15 bytes
    if len(nombre) > 15:
        print("Error: el nombre tiene más de 15 caracteres")
        return False

    # la especificacion pide US-ASCII de 7 bits, sin acentos
    # 32 a 126 son los caracteres que se pueden imprimir
    for letra in nombre:
        if ord(letra) < 32 or ord(letra) > 126:
            print("Error: el nombre solo puede tener caracteres ASCII sin acentos")
            return False

    # si empieza con # se confundiria con una entrada vacia
    if nombre.startswith('#'):
        print("Error: el nombre no puede empezar con '#'")
        return False

    return True


# guarda un archivo nuevo en FiUnamFS con el contenido (bytes) que se le pase
# regresa True si se pudo y False si no
def escribir_archivo(ruta_imagen, superbloque, nombre, contenido):
    if not validar_nombre(nombre):
        return False

    if buscar_archivo(ruta_imagen, superbloque, nombre) != None:
        print("Error: ya existe un archivo llamado", nombre)
        return False

    # hace falta una entrada libre en el directorio...
    numero_entrada = buscar_entrada_libre(ruta_imagen, superbloque)
    if numero_entrada == -1:
        print("Error: el directorio está lleno")
        return False

    # ...y un hueco en los datos donde quepa completo
    tamano_cluster = superbloque['tamano_cluster']
    clusters_necesarios = clusters_que_ocupa(len(contenido), tamano_cluster)

    cluster_inicial = buscar_hueco(ruta_imagen, superbloque, clusters_necesarios)
    if cluster_inicial == -1:
        print("Error: no hay espacio contiguo suficiente para", nombre)
        return False

    # fecha en el formato que pide la especificacion: AAAAMMDDHHMMSS
    fecha = datetime.now().strftime("%Y%m%d%H%M%S")

    # 'r+b' abre para leer y escribir sin borrar lo que ya tiene la imagen
    archivo = open(ruta_imagen, 'r+b')

    # primero los datos y luego la entrada, asi si algo falla el directorio
    # no apunta a datos a medias
    archivo.seek(cluster_inicial * tamano_cluster)
    archivo.write(contenido)

    # se llena la entrada campo por campo, en el mismo orden que la especificacion
    posicion_entrada = tamano_cluster + numero_entrada * TAMANO_ENTRADA
    archivo.seek(posicion_entrada)
    archivo.write(b'F')                                  # tipo
    archivo.write(nombre.ljust(15).encode('ascii'))      # nombre relleno con espacios
    archivo.write(struct.pack('<I', len(contenido)))     # tamaño
    archivo.write(struct.pack('<I', cluster_inicial))    # cluster inicial
    archivo.write(fecha.encode('ascii'))                 # fecha de creacion
    archivo.write(fecha.encode('ascii'))                 # fecha de modificacion

    archivo.close()
    return True


# copia un archivo de la computadora a FiUnamFS (operacion 3 del proyecto)
def copiar_a_fiunamfs(ruta_imagen, superbloque, ruta_origen):
    if not os.path.isfile(ruta_origen):
        print("Error: no existe el archivo", ruta_origen)
        return False

    # basename quita las carpetas: '/home/daniel/foto.jpg' -> 'foto.jpg'
    nombre = os.path.basename(ruta_origen)

    origen = open(ruta_origen, 'rb')
    contenido = origen.read()
    origen.close()

    if escribir_archivo(ruta_imagen, superbloque, nombre, contenido):
        print("Se copió", ruta_origen, "a FiUnamFS como", nombre, "(", len(contenido), "bytes )")
        return True
    return False


# borra un archivo de FiUnamFS (operacion 4 del proyecto)
def eliminar_archivo(ruta_imagen, superbloque, nombre):
    entrada = buscar_archivo(ruta_imagen, superbloque, nombre)
    if entrada == None:
        print("Error: no existe el archivo", nombre)
        return False

    # no hace falta borrar los datos, con marcar la entrada como vacia
    # esos clusters ya quedan libres
    posicion = superbloque['tamano_cluster'] + entrada['numero_entrada'] * TAMANO_ENTRADA

    archivo = open(ruta_imagen, 'r+b')
    archivo.seek(posicion)
    # asi marca la especificacion una entrada vacia
    archivo.write(b'-')
    archivo.write(b'#..............')
    archivo.close()

    return True


# menu para probar todo sin FUSE (solo corre si se ejecuta este archivo directo,
# no cuando fiunamfs_fuse.py lo importa)
if __name__ == "__main__":
    ruta = input("Ruta de la imagen: ")
    sb = leer_superbloque(ruta)
    mostrar_superbloque(sb)

    if not validar_superbloque(sb):
        print("La imagen NO es válida")
    else:
        print("La imagen es válida")

        opcion = ""
        while opcion != "0":
            print()
            print("1. Listar")
            print("2. Copiar de FiUnamFS a tu equipo")
            print("3. Copiar de tu equipo a FiUnamFS")
            print("4. Eliminar un archivo")
            print("0. Salir")
            opcion = input("Opción: ")

            if opcion == "1":
                archivos = leer_directorio(ruta, sb)
                mostrar_directorio(archivos)
            elif opcion == "2":
                nombre = input("Archivo de FiUnamFS: ")
                destino = input("Guardar como: ")
                copiar_a_equipo(ruta, sb, nombre, destino)
            elif opcion == "3":
                origen = input("Archivo de tu equipo: ")
                copiar_a_fiunamfs(ruta, sb, origen)
            elif opcion == "4":
                nombre = input("Archivo a eliminar: ")
                if eliminar_archivo(ruta, sb, nombre):
                    print("Se eliminó", nombre)
            elif opcion != "0":
                print("Opción no válida")
