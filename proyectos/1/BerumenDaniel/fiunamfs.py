import struct

NOMBRE_FS = "FiUnamFS"
VERSION_FS = "27-1"
TAMANO_SECTOR = 512


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


if __name__ == "__main__":
    ruta = input("Ruta de la imagen: ")
    sb = leer_superbloque(ruta)
    mostrar_superbloque(sb)

    if validar_superbloque(sb):
        print("La imagen es válida")
    else:
        print("La imagen NO es válida")
