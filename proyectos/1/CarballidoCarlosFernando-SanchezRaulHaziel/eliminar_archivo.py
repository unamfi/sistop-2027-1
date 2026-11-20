
#!/usr/bin/env python3
"""Elimina una entrada del directorio de FiUnamFS."""

import struct
import sys
from pathlib import Path

from listar_directorio import leer_superbloque, leer_directorio

TAM_ENTRADA = 64


def eliminar_archivo(ruta_imagen, nombre):
    """Marca como libre la entrada de un archivo existente."""

    with ruta_imagen.open("r+b") as imagen:
        etiqueta, tam_cluster, clusters_dir, clusters_total = (
            leer_superbloque(imagen, ruta_imagen.stat().st_size)
        )

        archivos, _ = leer_directorio(
            imagen, tam_cluster, clusters_dir, clusters_total
        )

        encontrados = [
            archivo for archivo in archivos
            if archivo["nombre"] == nombre
        ]

        if not encontrados:
            raise ValueError(
                f"El archivo '{nombre}' no existe en FiUnamFS."
            )

        if len(encontrados) != 1:
            raise ValueError(
                "Hay nombres duplicados en el directorio."
            )

        archivo_encontrado = encontrados[0]

        inicio_directorio = tam_cluster
        tam_directorio = clusters_dir * tam_cluster

        imagen.seek(inicio_directorio)
        directorio = imagen.read(tam_directorio)

        if len(directorio) != tam_directorio:
            raise ValueError("No se pudo leer el directorio completo.")

        posicion = None

        for indice in range(0, len(directorio), TAM_ENTRADA):
            entrada = directorio[indice:indice + TAM_ENTRADA]

            if entrada[0:1] != b"F":
                continue

            nombre_entrada = (
                entrada[1:16]
                .decode("ascii")
                .rstrip(" \x00")
            )

            if nombre_entrada == nombre:
                posicion = inicio_directorio + indice
                break

        if posicion is None:
            raise ValueError("No se encontro la entrada del archivo.")

        # Entrada libre: tipo '-' y nombre de marcador.
        entrada_vacia = (
            b"-"
            + b"#"
            + b"." * 14
            + b"\x00" * 48
        )

        imagen.seek(posicion)
        imagen.write(entrada_vacia)

    print(f"Volumen: {etiqueta}")
    print(f"Archivo eliminado: {nombre}")
    print(f"Tamano liberado: {archivo_encontrado['tamano']} bytes")
    print("Entrada del directorio marcada como libre.")
    print("Eliminacion completada correctamente.")


def main():
    if len(sys.argv) != 3:
        print(
            "Uso: python3 eliminar_archivo.py <imagen> <nombre>",
            file=sys.stderr
        )
        return 1

    ruta_imagen = Path(sys.argv[1])
    nombre = sys.argv[2]

    try:
        eliminar_archivo(ruta_imagen, nombre)
    except (OSError, ValueError, UnicodeError, struct.error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
