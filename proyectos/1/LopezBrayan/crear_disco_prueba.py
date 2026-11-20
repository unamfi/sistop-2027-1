import os
import struct
import sys

BYTES_VOLUMEN = 1440 * 1024
BYTES_POR_CLUSTER = 2048
CLUSTERS_DIRECTORIO = 4
CANT_CLUSTERS = BYTES_VOLUMEN // BYTES_POR_CLUSTER   
MARCA_LIBRE = b"#" + b"." * 14

def armar_registro(nombre_archivo, tam_archivo, cluster_inicio, sello_tiempo):
    return (b"F" + nombre_archivo.encode("ascii").ljust(15, b" ")
            + struct.pack("<II", tam_archivo, cluster_inicio)
            + sello_tiempo.encode("ascii") + sello_tiempo.encode("ascii") + bytes(12))

def main():
    archivo_salida = sys.argv[1] if len(sys.argv) > 1 else "fiunamfs.img"
    if os.path.exists(archivo_salida):
        print("Ya existe '%s'; borralo o elige otro nombre." % archivo_salida)
        sys.exit(1)

    imagen = bytearray(BYTES_VOLUMEN)

    imagen[0:8] = b"FiUnamFS"
    imagen[10:14] = b"27-1"
    imagen[20:36] = b"DiscoDePrueba".ljust(16, b" ")
    imagen[40:52] = struct.pack("<III", BYTES_POR_CLUSTER, CLUSTERS_DIRECTORIO, CANT_CLUSTERS)

    inicio_dir = 1 * BYTES_POR_CLUSTER
    for idx in range(CLUSTERS_DIRECTORIO * BYTES_POR_CLUSTER // 64):
        imagen[inicio_dir + idx * 64: inicio_dir + (idx + 1) * 64] = b"-" + MARCA_LIBRE + bytes(48)

    archivos_base = [
        ("hola.txt", b"Hola desde dentro del FiUnamFS!\n"),
        ("README.txt", b"Este es un disco de prueba.\n" * 200),       
        ("numeros.bin", bytes(range(256)) * 10),                     
    ]
    cluster_actual = 5
    for idx, (nombre_archivo, datos_archivo) in enumerate(archivos_base):
        num_clusters = (len(datos_archivo) + BYTES_POR_CLUSTER - 1) // BYTES_POR_CLUSTER
        imagen[cluster_actual * BYTES_POR_CLUSTER: cluster_actual * BYTES_POR_CLUSTER + len(datos_archivo)] = datos_archivo
        registro = armar_registro(nombre_archivo, len(datos_archivo), cluster_actual, "20261028182600")
        imagen[inicio_dir + idx * 64: inicio_dir + (idx + 1) * 64] = registro
        cluster_actual += num_clusters

    with open(archivo_salida, "wb") as f_out:
        f_out.write(imagen)
    print("Disco de prueba creado: %s (%d bytes)" % (archivo_salida, len(imagen)))

main()