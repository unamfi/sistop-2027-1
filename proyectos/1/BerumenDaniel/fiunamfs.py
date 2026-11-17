import struct

NOMBRE_FS = "FiUnamFS"
VERSION_FS = "27-1"
TAMANO_SECTOR = 512
TAMANO_ENTRADA = 64


def leer_entero(archivo, posicion):
    archivo.seek(posicion)
    datos = archivo.read(4)
    numero = struct.unpack('<I', datos)[0]
    return numero


def leer_texto(archivo, posicion, longitud):
    archivo.seek(posicion)
    datos = archivo.read(longitud)
    texto = datos.decode('ascii')
    texto = texto.strip()
    texto = texto.strip('\x00')
    return texto


def leer_superbloque(ruta_imagen):
    archivo = open(ruta_imagen, 'rb')

    superbloque = {}
    superbloque['nombre'] = leer_texto(archivo, 0, 8)
    superbloque['version'] = leer_texto(archivo, 10, 4)
    superbloque['etiqueta'] = leer_texto(archivo, 20, 16)
    superbloque['tamano_cluster'] = leer_entero(archivo, 40)
    superbloque['clusters_directorio'] = leer_entero(archivo, 44)
    superbloque['clusters_totales'] = leer_entero(archivo, 48)

    archivo.close()
    return superbloque


def validar_superbloque(superbloque):
    # Si la imagen no es FiUnamFS 27-1 no se debe modificar, para no corromperla
    if superbloque['nombre'] != NOMBRE_FS:
        print("Error: la imagen no es un sistema de archivos FiUnamFS")
        return False

    if superbloque['version'] != VERSION_FS:
        print("Error: la versión es", superbloque['version'], "y se esperaba", VERSION_FS)
        return False

    return True


def mostrar_superbloque(superbloque):
    print("Sistema de archivos:", superbloque['nombre'])
    print("Versión:", superbloque['version'])
    print("Etiqueta del volumen:", superbloque['etiqueta'])
    print("Tamaño del cluster:", superbloque['tamano_cluster'], "bytes")
    print("Clusters del directorio:", superbloque['clusters_directorio'])
    print("Clusters totales:", superbloque['clusters_totales'])


def leer_directorio(ruta_imagen, superbloque):
    archivo = open(ruta_imagen, 'rb')

    tamano_cluster = superbloque['tamano_cluster']
    inicio_directorio = tamano_cluster
    numero_entradas = (superbloque['clusters_directorio'] * tamano_cluster) // TAMANO_ENTRADA

    lista_archivos = []

    for i in range(numero_entradas):
        posicion = inicio_directorio + i * TAMANO_ENTRADA

        entrada = {}
        entrada['numero_entrada'] = i
        entrada['tipo'] = leer_texto(archivo, posicion, 1)
        entrada['nombre'] = leer_texto(archivo, posicion + 1, 15)
        entrada['tamano'] = leer_entero(archivo, posicion + 16)
        entrada['cluster_inicial'] = leer_entero(archivo, posicion + 20)
        entrada['fecha_creacion'] = leer_texto(archivo, posicion + 24, 14)
        entrada['fecha_modificacion'] = leer_texto(archivo, posicion + 38, 14)

        # Las entradas vacías se marcan con '-' o con un nombre que empieza con '#'
        if entrada['tipo'] == 'F' and not entrada['nombre'].startswith('#'):
            lista_archivos.append(entrada)

    archivo.close()
    return lista_archivos


def formatear_fecha(fecha):
    if len(fecha) != 14:
        return fecha
    anio = fecha[0:4]
    mes = fecha[4:6]
    dia = fecha[6:8]
    hora = fecha[8:10]
    minuto = fecha[10:12]
    segundo = fecha[12:14]
    return anio + "-" + mes + "-" + dia + " " + hora + ":" + minuto + ":" + segundo


def mostrar_directorio(lista_archivos):
    if len(lista_archivos) == 0:
        print("El directorio está vacío")
        return

    print("Nombre           Tamaño   Cluster  Creado               Modificado")
    print("---------------  -------  -------  -------------------  -------------------")
    for entrada in lista_archivos:
        nombre = entrada['nombre'].ljust(15)
        tamano = str(entrada['tamano']).rjust(7)
        cluster = str(entrada['cluster_inicial']).rjust(7)
        creado = formatear_fecha(entrada['fecha_creacion'])
        modificado = formatear_fecha(entrada['fecha_modificacion'])
        print(nombre, "", tamano, "", cluster, "", creado, "", modificado)

    print()
    print("Total de archivos:", len(lista_archivos))


if __name__ == "__main__":
    ruta = input("Ruta de la imagen: ")
    sb = leer_superbloque(ruta)
    mostrar_superbloque(sb)

    if validar_superbloque(sb):
        print("La imagen es válida")
        print()
        archivos = leer_directorio(ruta, sb)
        mostrar_directorio(archivos)
    else:
        print("La imagen NO es válida")
