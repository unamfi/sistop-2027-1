import os
import sys
from datetime import datetime
from queue import Empty, Queue
from threading import Thread


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

    image_size = image.seek(0, 2)
    if total_clusters <= 1 + directory_clusters:
        raise ValueError("La imagen no tiene espacio para los datos.")
    if image_size != cluster_size * total_clusters:
        raise ValueError("El tamaño de la imagen no coincide con el superbloque.")

    return label, cluster_size, directory_clusters, total_clusters


def read_directory(image, cluster_size, directory_clusters):
    image.seek(cluster_size)
    entry_count = cluster_size * directory_clusters // 64
    files = []
    free_entry = None

    for _ in range(entry_count):
        entry_position = image.tell()
        entry = image.read(64)

        if entry[0:1] == b"-" and free_entry is None:
            free_entry = entry_position

        if entry[0:1] != b"F":
            continue

        name = entry[1:16].decode("ascii").rstrip("\x00 ")
        size = int.from_bytes(entry[16:20], "little")
        start_cluster = int.from_bytes(entry[20:24], "little")
        files.append((name, size, start_cluster, entry_position))

    return files, free_entry


def list_files(files):
    if not files:
        return "El directorio está vacío."

    lines = [
        "Archivos en la imagen",
        f"{'Nombre':15} {'Bytes':>10} {'Clúster inicial':>15}",
    ]
    for name, size, start_cluster, _ in files:
        lines.append(f"{name:15} {size:10} {start_cluster:15}")

    return "\n".join(lines)


def extract_file(image, files, cluster_size, directory_clusters, name, destination):
    for file_name, size, start_cluster, _ in files:
        if file_name != name:
            continue

        data = b""
        if size > 0:
            if start_cluster <= directory_clusters:
                raise ValueError("El archivo empieza fuera del área de datos.")

            image.seek(start_cluster * cluster_size)
            data = image.read(size)
            if len(data) != size:
                raise ValueError("El archivo se extiende fuera de la imagen.")

        with open(destination, "xb") as output:
            output.write(data)

        return f"Se extrajo {name} a {destination} ({size} bytes)."

    raise ValueError(f"No se encontró {name} en la imagen.")


def find_free_clusters(files, cluster_size, first_data_cluster, total_clusters, needed):
    occupied = [False] * total_clusters

    for name, size, start, _ in files:
        if size == 0:
            continue

        # El último clúster cuenta aunque el archivo use solo una parte.
        count = (size + cluster_size - 1) // cluster_size
        end = start + count
        if start < first_data_cluster or end > total_clusters:
            raise ValueError(f"El archivo {name} está fuera del área de datos.")

        for cluster in range(start, end):
            occupied[cluster] = True

    consecutive = 0
    for cluster in range(first_data_cluster, total_clusters):
        if occupied[cluster]:
            consecutive = 0
        else:
            consecutive += 1
            if consecutive == needed:
                return cluster - needed + 1

    raise ValueError("No hay suficientes clústeres libres consecutivos.")


def import_file(
    image, files, free_entry, cluster_size, directory_clusters, total_clusters, source
):
    name = os.path.basename(source)
    if not name.isascii() or not 1 <= len(name) <= 15 or name.endswith(" "):
        raise ValueError(
            "El nombre debe tener de 1 a 15 caracteres ASCII y no acabar en espacio."
        )
    if name == "#..............":
        raise ValueError("Ese nombre está reservado para las entradas libres.")

    for file_name, _, _, _ in files:
        if file_name == name:
            raise ValueError(f"Ya existe {name} en la imagen.")

    if free_entry is None:
        raise ValueError("El directorio está lleno.")

    first_data_cluster = 1 + directory_clusters
    capacity = (total_clusters - first_data_cluster) * cluster_size
    with open(source, "rb") as input_file:
        data = input_file.read(capacity + 1)

    size = len(data)
    if size > capacity:
        raise ValueError("El archivo es demasiado grande para la imagen.")

    start_cluster = 0
    if size > 0:
        needed = (size + cluster_size - 1) // cluster_size
        start_cluster = find_free_clusters(
            files, cluster_size, first_data_cluster, total_clusters, needed
        )
        image.seek(start_cluster * cluster_size)
        image.write(data)


    timestamp = datetime.now().strftime("%Y%m%d%H%M%S").encode("ascii")
    entry = (
        b"F"
        + name.encode("ascii").ljust(15, b" ")
        + size.to_bytes(4, "little")
        + start_cluster.to_bytes(4, "little")
        + timestamp
        + timestamp
        + bytes(12)
    )

    image.seek(free_entry)
    image.write(entry)
    return f"Se importó {name} ({size} bytes)."


def delete_file(image, files, name):
    for file_name, _, _, entry_position in files:
        if file_name == name:
            # Al liberar la entrada, sus clústeres quedan disponibles.
            image.seek(entry_position)
            image.write(b"-#.............." + bytes(48))
            return f"Se eliminó {name} de la imagen."

    raise ValueError(f"No se encontró {name} en la imagen.")


def run_operation(image_path, operation, *args):
    mode = "r+b" if operation in ("importar", "borrar") else "rb"

    with open(image_path, mode) as image:
        _, cluster_size, directory_clusters, total_clusters = read_superblock(image)
        files, free_entry = read_directory(image, cluster_size, directory_clusters)

        if operation == "listar":
            return list_files(files)
        if operation == "extraer":
            return extract_file(image, files, cluster_size, directory_clusters, *args)
        if operation == "importar":
            return import_file(
                image, files, free_entry, cluster_size, directory_clusters,
                total_clusters, *args
            )

        return delete_file(image, files, *args)


def disk_worker(image_path, requests, results):
    while True:
        request = requests.get()

      
        if request is None:
            return

        operation, args = request
        try:
            message = run_operation(image_path, operation, *args)
        except (OSError, ValueError) as error:
            message = f"Error: {error}"

        results.put(message)


def run_menu(image_path):
    with open(image_path, "rb") as image:
        label, _, _, _ = read_superblock(image)
    print(f"FiUnamFS 27-1 | {label}")

    requests = Queue()
    results = Queue()
    worker = Thread(target=disk_worker, args=(image_path, requests, results))
    worker.start()
    pending = 0

    try:
        while True:
          
            while pending > 0:
                try:
                    print("\n" + results.get_nowait())
                    pending -= 1
                except Empty:
                    break

            print(f"\nSolicitudes por mostrar: {pending}")
            print("1. Listar archivos")
            print("2. Extraer un archivo")
            print("3. Importar un archivo")
            print("4. Borrar un archivo")
            print("5. Esperar y mostrar resultados")
            print("0. Salir")

            choice = input("Opción: ").strip()
            if choice == "0":
                break

            if choice == "5":
                while pending > 0:
                    print("\n" + results.get())
                    pending -= 1
                continue

            if choice == "1":
                request = ("listar", ())
            elif choice == "2":
                name = input("Nombre del archivo en la imagen: ")
                destination = input("Ruta donde se guardará: ")
                request = ("extraer", (name, destination))
            elif choice == "3":
                source = input("Ruta del archivo local: ")
                request = ("importar", (source,))
            elif choice == "4":
                name = input("Nombre del archivo que quieres borrar: ")
                request = ("borrar", (name,))
            else:
                print("Opción inválida.")
                continue

            requests.put(request)
            pending += 1

    except (EOFError, KeyboardInterrupt):
        print()

    finally:
        requests.put(None)
        worker.join()

    for _ in range(pending):
        print("\n" + results.get())


def main():
    args = sys.argv[1:]

    if len(args) == 1:
        run_menu(args[0])
    elif len(args) == 2 and args[1] == "--listar":
        print(run_operation(args[0], "listar"))
    elif len(args) == 3:
        image_path, option, value = args
        if option == "--importar":
            print(run_operation(image_path, "importar", value))
        elif option == "--borrar":
            print(run_operation(image_path, "borrar", value))
        else:
            print(run_operation(image_path, "extraer", option, value))
    else:
        sys.exit(
            "Uso:\n"
            "  python3 fiunamfs.py imagen.img\n"
            "  python3 fiunamfs.py imagen.img --listar\n"
            "  python3 fiunamfs.py imagen.img archivo destino\n"
            "  python3 fiunamfs.py imagen.img --importar archivo_local\n"
            "  python3 fiunamfs.py imagen.img --borrar archivo"
        )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        sys.exit(f"Error: {error}")