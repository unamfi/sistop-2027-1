import struct
from datetime import datetime

TAMANO_SECTOR = 512
SECTORES_POR_CLUSTER = 4
TAMANO_CLUSTER = TAMANO_SECTOR * SECTORES_POR_CLUSTER
CLUSTERS_DIRECTORIO = 4
TAMANO_DISCO = 1440 * 1024
CLUSTERS_TOTALES = TAMANO_DISCO // TAMANO_CLUSTER
TAMANO_ENTRADA = 64


def crear_imagen(ruta, etiqueta):
    archivo = open(ruta, 'wb')

    # Primero se llena todo el disco con ceros para que mida exactamente 1440 KB
    archivo.write(b'\x00' * TAMANO_DISCO)

    archivo.seek(0)
    archivo.write(b'FiUnamFS')

    archivo.seek(10)
    archivo.write(b'27-1')

    etiqueta = etiqueta[:16]
    etiqueta = etiqueta.ljust(16)
    archivo.seek(20)
    archivo.write(etiqueta.encode('ascii'))

    archivo.seek(40)
    archivo.write(struct.pack('<I', TAMANO_CLUSTER))
    archivo.seek(44)
    archivo.write(struct.pack('<I', CLUSTERS_DIRECTORIO))
    archivo.seek(48)
    archivo.write(struct.pack('<I', CLUSTERS_TOTALES))

    # El directorio empieza en el cluster 1; todas sus entradas se marcan como vacías
    inicio_directorio = TAMANO_CLUSTER
    numero_entradas = (CLUSTERS_DIRECTORIO * TAMANO_CLUSTER) // TAMANO_ENTRADA

    for i in range(numero_entradas):
        posicion = inicio_directorio + i * TAMANO_ENTRADA
        archivo.seek(posicion)
        archivo.write(b'-')
        archivo.write(b'#..............')

    archivo.close()


def agregar_archivo_ejemplo(ruta, numero_entrada, nombre, contenido, cluster_inicial):
    archivo = open(ruta, 'r+b')

    fecha = datetime.now().strftime("%Y%m%d%H%M%S")

    posicion_datos = cluster_inicial * TAMANO_CLUSTER
    archivo.seek(posicion_datos)
    archivo.write(contenido.encode('ascii'))

    posicion_entrada = TAMANO_CLUSTER + numero_entrada * TAMANO_ENTRADA
    archivo.seek(posicion_entrada)
    archivo.write(b'F')
    archivo.write(nombre.ljust(15).encode('ascii'))
    archivo.write(struct.pack('<I', len(contenido)))
    archivo.write(struct.pack('<I', cluster_inicial))
    archivo.write(fecha.encode('ascii'))
    archivo.write(fecha.encode('ascii'))

    archivo.close()


if __name__ == "__main__":
    ruta = input("Nombre de la imagen a crear (ej. prueba.img): ")
    etiqueta = input("Etiqueta del volumen: ")
    crear_imagen(ruta, etiqueta)
    print("Imagen creada:", ruta)

    respuesta = input("¿Agregar archivos de ejemplo? (s/n): ")
    if respuesta == 's' or respuesta == 'S':
        # Los datos empiezan después del directorio, en el cluster 5
        agregar_archivo_ejemplo(ruta, 0, "hola.txt", "Hola desde FiUnamFS\n", 5)
        agregar_archivo_ejemplo(ruta, 1, "notas.txt", "Proyecto de Sistemas Operativos\nFacultad de Ingenieria\n", 6)
        agregar_archivo_ejemplo(ruta, 2, "grande.txt", "A" * 5000, 7)
        print("Se agregaron 3 archivos de ejemplo")
