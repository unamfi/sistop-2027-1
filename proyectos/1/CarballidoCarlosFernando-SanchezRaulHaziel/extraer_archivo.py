
#!/usr/bin/env python3
"""Extrae un archivo de una imagen FiUnamFS hacia el equipo."""

import struct
import sys
from pathlib import Path

from listar_directorio import leer_superbloque, leer_directorio


def extraer_archivo(ruta_imagen, nombre, ruta_destino):
    """Localiza un archivo y copia sus bytes al sistema anfitrion."""

    with ruta_imagen.open("rb") as imagen:
        etiqueta, tam_cluster, clusters_dir, clusters_total = (
            leer_superbloque(imagen, ruta_imagen.stat().st_size)
        )

        entradas, _ = leer_directorio(
            imagen, tam_cluster, clusters_dir, clusters_total
        )

        # Buscamos el archivo por su nombre exacto.
        encontrado = next(
            (entrada for entrada in entradas
             if entrada["nombre"] == nombre),
            None
        )

        if encontrado is None:
            raise ValueError(
                f"El archivo '{nombre}' no existe en FiUnamFS."
            )

        tamano = encontrado["tamano"]
        cluster_inicial = encontrado["cluster"]

        if tamano > 0:
            clusters_necesarios = (
                tamano + tam_cluster - 1
            ) // tam_cluster

            if (cluster_inicial < 1 + clusters_dir
                    or cluster_inicial + clusters_necesarios > clusters_total):
                raise ValueError(
                    "El archivo tiene una ubicacion fuera del area de datos."
                )

        # El archivo empieza en el byte correspondiente a su cluster.
        desplazamiento = cluster_inicial * tam_cluster
        imagen.seek(desplazamiento)

        # Leemos solo el tamano real, sin incluir relleno del cluster.
        contenido = imagen.read(tamano)

        if len(contenido) != tamano:
            raise ValueError(
                "No fue posible leer el contenido completo del archivo."
            )

    # El modo xb impide sobrescribir un archivo ya existente.
    with ruta_destino.open("xb") as salida:
        salida.write(contenido)

    print(f"Volumen: {etiqueta}")
    print(f"Archivo extraido: {nombre}")
    print(f"Destino: {ruta_destino}")
    print(f"Tamano: {len(contenido)} bytes")
    print("Extraccion completada correctamente.")


def main():
    if len(sys.argv) != 4:
        print(
            "Uso: python3 extraer_archivo.py "
            "<imagen> <nombre> <destino>",
            file=sys.stderr
        )
        return 1

    ruta_imagen = Path(sys.argv[1])
    nombre = sys.argv[2]
    ruta_destino = Path(sys.argv[3])

    try:
        extraer_archivo(ruta_imagen, nombre, ruta_destino)
    except FileExistsError:
        print(
            f"Error: el destino '{ruta_destino}' ya existe.",
            file=sys.stderr
        )
        return 1
    except (OSError, ValueError, UnicodeError, struct.error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
