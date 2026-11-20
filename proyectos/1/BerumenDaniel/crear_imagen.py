# crear_imagen.py
# crea una imagen de FiUnamFS vacia para hacer pruebas sin usar la del profe
# (opcionalmente con 3 archivos de ejemplo)

import struct
from datetime import datetime

# medidas que pide la especificacion
TAMANO_SECTOR = 512
SECTORES_POR_CLUSTER = 4
TAMANO_CLUSTER = TAMANO_SECTOR * SECTORES_POR_CLUSTER   # 2048 bytes
CLUSTERS_DIRECTORIO = 4
TAMANO_DISCO = 1440 * 1024                              # un diskette de 1440 KB
CLUSTERS_TOTALES = TAMANO_DISCO // TAMANO_CLUSTER       # 720 clusters
TAMANO_ENTRADA = 64


# crea la imagen con el superbloque y el directorio vacio
def crear_imagen(ruta, etiqueta):
    # 'wb' crea el archivo (o lo borra si ya existia)
    archivo = open(ruta, 'wb')

    # lleno todo con ceros para que mida 1440 KB
    archivo.write(b'\x00' * TAMANO_DISCO)

    # superbloque: cada dato va en la posicion que dice la especificacion
    archivo.seek(0)
    archivo.write(b'FiUnamFS')

    archivo.seek(10)
    archivo.write(b'27-1')

    # la etiqueta mide 16 bytes: se corta si es mas larga
    # y se rellena con espacios si es mas corta
    etiqueta = etiqueta[:16]
    etiqueta = etiqueta.ljust(16)
    archivo.seek(20)
    archivo.write(etiqueta.encode('ascii'))

    # los enteros se guardan en little endian de 32 bits ('<I')
    archivo.seek(40)
    archivo.write(struct.pack('<I', TAMANO_CLUSTER))
    archivo.seek(44)
    archivo.write(struct.pack('<I', CLUSTERS_DIRECTORIO))
    archivo.seek(48)
    archivo.write(struct.pack('<I', CLUSTERS_TOTALES))

    # el directorio esta en el cluster 1, todas las entradas empiezan vacias
    inicio_directorio = TAMANO_CLUSTER
    numero_entradas = (CLUSTERS_DIRECTORIO * TAMANO_CLUSTER) // TAMANO_ENTRADA

    for i in range(numero_entradas):
        posicion = inicio_directorio + i * TAMANO_ENTRADA
        archivo.seek(posicion)
        # asi se marca una entrada vacia segun la especificacion
        archivo.write(b'-')
        archivo.write(b'#..............')

    archivo.close()


# mete un archivo de texto en la imagen "a mano", en la entrada y el cluster
# que se le digan (sirve para probar el listado antes de tener la copia hacia FiUnamFS)
def agregar_archivo_ejemplo(ruta, numero_entrada, nombre, contenido, cluster_inicial):
    # 'r+b' para modificar la imagen sin borrarla
    archivo = open(ruta, 'r+b')

    fecha = datetime.now().strftime("%Y%m%d%H%M%S")

    # primero el contenido en su cluster
    posicion_datos = cluster_inicial * TAMANO_CLUSTER
    archivo.seek(posicion_datos)
    archivo.write(contenido.encode('ascii'))

    # luego la entrada del directorio, campo por campo
    posicion_entrada = TAMANO_CLUSTER + numero_entrada * TAMANO_ENTRADA
    archivo.seek(posicion_entrada)
    archivo.write(b'F')                                  # tipo
    archivo.write(nombre.ljust(15).encode('ascii'))      # nombre
    archivo.write(struct.pack('<I', len(contenido)))     # tamaño
    archivo.write(struct.pack('<I', cluster_inicial))    # cluster inicial
    archivo.write(fecha.encode('ascii'))                 # fecha de creacion
    archivo.write(fecha.encode('ascii'))                 # fecha de modificacion

    archivo.close()


if __name__ == "__main__":
    ruta = input("Nombre de la imagen a crear (ej. prueba.img): ")
    etiqueta = input("Etiqueta del volumen: ")
    crear_imagen(ruta, etiqueta)
    print("Imagen creada:", ruta)

    respuesta = input("¿Agregar archivos de ejemplo? (s/n): ")
    if respuesta == 's' or respuesta == 'S':
        # los datos empiezan en el cluster 5 (despues del directorio)
        agregar_archivo_ejemplo(ruta, 0, "hola.txt", "Hola desde FiUnamFS\n", 5)
        agregar_archivo_ejemplo(ruta, 1, "notas.txt", "Proyecto de Sistemas Operativos\nFacultad de Ingenieria\n", 6)
        # grande.txt mide 5000 bytes y ocupa 3 clusters (7, 8 y 9),
        # sirve para probar archivos de mas de un cluster
        agregar_archivo_ejemplo(ruta, 2, "grande.txt", "A" * 5000, 7)
        print("Se agregaron 3 archivos de ejemplo")
