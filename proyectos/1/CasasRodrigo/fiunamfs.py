import sys


def read_superblock(image):
    header = image.read(52)

    if len(header) < 52:
        raise ValueError("El superbloque está incompleto.")

    if header[0:8] != b"FiUnamFS":
        raise ValueError("La imagen no es FiUnamFS.")

    if header[10:14] != b"27-1":
        raise ValueError("La versión de la imagen debe ser 27-1.")

    label = header[20:36].decode("ascii").strip("\x00 ")
    cluster_size = int.from_bytes(header[40:44], "little")
    directory_clusters = int.from_bytes(header[44:48], "little")
    total_clusters = int.from_bytes(header[48:52], "little")

    if cluster_size != 2048 or directory_clusters != 4:
        raise ValueError("El tamaño del clúster o del directorio es incorrecto.")

    # seek(0, 2) va al final del archivo y devuelve su tamaño en bytes.
    image_size = image.seek(0, 2)
    if total_clusters <= 1 + directory_clusters:
        raise ValueError("La imagen no tiene espacio para los datos.")
    if image_size != cluster_size * total_clusters:
        raise ValueError("El tamaño de la imagen no coincide con el superbloque.")

    print("FiUnamFS 27-1")
    print("Etiqueta del volumen:", label)
    print("Tamaño del clúster:", cluster_size, "bytes")
    print("Clústeres del directorio:", directory_clusters)
    print("Clústeres totales:", total_clusters)


if len(sys.argv) != 2:
    sys.exit("Uso: python3 fiunamfs.py ruta_de_la_imagen.img")

try:
    with open(sys.argv[1], "rb") as image:
        read_superblock(image)
except (OSError, ValueError) as error:
    sys.exit(f"Error: {error}")