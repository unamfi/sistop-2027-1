
#!/usr/bin/env python3
"""Agrega archivos a una imagen FiUnamFS."""

import struct
import sys
from datetime import datetime
from pathlib import Path

from listar_directorio import leer_superbloque, leer_directorio


def agregar_archivo(ruta_imagen, ruta_origen):
    """Busca espacio libre e incorpora un archivo al volumen."""

    if ruta_imagen.resolve() == ruta_origen.resolve():
        raise ValueError("El archivo origen no puede ser la imagen.")

    nombre = ruta_origen.name
    nombre_bytes = nombre.encode("ascii")

    if not 1 <= len(nombre_bytes) <= 15:
        raise ValueError("El nombre debe tener de 1 a 15 caracteres ASCII.")

    if nombre != nombre.strip() or "\x00" in nombre:
        raise ValueError("Nombre de archivo no valido.")

    contenido = ruta_origen.read_bytes()
    tamano = len(contenido)

    if tamano > 0xFFFFFFFF:
        raise ValueError("El archivo es demasiado grande.")

    with ruta_imagen.open("r+b") as imagen:
        etiqueta, tam_cluster, clusters_dir, clusters_total = (
            leer_superbloque(imagen, ruta_imagen.stat().st_size)
        )

        archivos, _ = leer_directorio(
            imagen, tam_cluster, clusters_dir, clusters_total
        )

        if any(a["nombre"] == nombre for a in archivos):
            raise ValueError(f"El archivo '{nombre}' ya existe.")

        # Buscar una entrada libre en el directorio.
        inicio_directorio = tam_cluster
        tam_directorio = clusters_dir * tam_cluster

        imagen.seek(inicio_directorio)
        directorio = imagen.read(tam_directorio)

        if len(directorio) != tam_directorio:
            raise ValueError("No se pudo leer el directorio.")

        posicion_libre = None

        for indice in range(0, len(directorio), 64):
            if directorio[indice:indice + 1] == b"-":
                posicion_libre = inicio_directorio + indice
                break

        if posicion_libre is None:
            raise ValueError("El directorio esta lleno.")

        # Identificar los clusters ocupados.
        primer_cluster_datos = 1 + clusters_dir
        ocupados = set()

        for archivo in archivos:
            cantidad = (
                archivo["tamano"] + tam_cluster - 1
            ) // tam_cluster

            if cantidad == 0:
                continue

            inicio = archivo["cluster"]

            if (
                inicio < primer_cluster_datos
                or inicio + cantidad > clusters_total
            ):
                raise ValueError("Archivo fuera del area de datos.")

            rango = set(range(inicio, inicio + cantidad))

            if ocupados.intersection(rango):
                raise ValueError("Hay clusters superpuestos.")

            ocupados.update(rango)

        # Buscar espacio contiguo suficiente.
        necesarios = (tamano + tam_cluster - 1) // tam_cluster
        cluster_inicial = 0

        if necesarios > 0:
            encontrado = False

            for posible in range(
                primer_cluster_datos,
                clusters_total - necesarios + 1
            ):
                rango = range(posible, posible + necesarios)

                if all(c not in ocupados for c in rango):
                    cluster_inicial = posible
                    encontrado = True
                    break

            if not encontrado:
                raise ValueError("No hay espacio contiguo suficiente.")

            # Escribir contenido y completar el ultimo cluster.
            imagen.seek(cluster_inicial * tam_cluster)
            imagen.write(contenido)

            relleno = necesarios * tam_cluster - tamano

            if relleno:
                imagen.write(b"\x00" * relleno)

            imagen.flush()

        # Crear la entrada de directorio de 64 bytes.
        fecha = datetime.now().strftime("%Y%m%d%H%M%S").encode("ascii")

        entrada = bytearray(64)
        entrada[0:1] = b"F"
        entrada[1:16] = nombre_bytes.ljust(15, b" ")

        struct.pack_into("<I", entrada, 16, tamano)
        struct.pack_into("<I", entrada, 20, cluster_inicial)

        entrada[24:38] = fecha
        entrada[38:52] = fecha

        # Registrar el archivo al terminar de guardar los datos.
        imagen.seek(posicion_libre)
        imagen.write(entrada)
        imagen.flush()

    print(f"Volumen: {etiqueta}")
    print(f"Archivo agregado: {nombre}")
    print(f"Tamano: {tamano} bytes")
    print(f"Cluster inicial: {cluster_inicial}")
    print(f"Clusters utilizados: {necesarios}")
    print("Incorporacion completada correctamente.")


def main():
    if len(sys.argv) != 3:
        print(
            "Uso: python3 agregar_archivo.py <imagen> <origen>",
            file=sys.stderr
        )
        return 1

    try:
        agregar_archivo(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError, UnicodeError, struct.error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
