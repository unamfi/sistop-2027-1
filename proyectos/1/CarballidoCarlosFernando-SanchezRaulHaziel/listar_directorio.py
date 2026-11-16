
#!/usr/bin/env python3
"""Lee y muestra el directorio de una imagen FiUnamFS."""

import struct
import sys
from pathlib import Path

TAM_ENTRADA = 64


def leer_superbloque(archivo, tam_imagen):
    """Comprueba que el volumen tenga el formato esperado."""
    superbloque = archivo.read(52)

    if len(superbloque) != 52:
        raise ValueError("El superbloque esta incompleto.")

    identificador = superbloque[0:8].decode("ascii")
    version = superbloque[10:14].decode("ascii")
    etiqueta = superbloque[20:36].decode("ascii").strip()

    tam_cluster, clusters_dir, clusters_total = (
        struct.unpack_from("<III", superbloque, 40)
    )

    if identificador != "FiUnamFS" or version != "27-1":
        raise ValueError("Identificador o version no compatibles.")

    if (tam_cluster != 2048 or clusters_dir != 4
            or clusters_total != 720):
        raise ValueError("Dimensiones del volumen incorrectas.")

    if tam_imagen != tam_cluster * clusters_total:
        raise ValueError("El tamaño de la imagen no coincide.")

    return etiqueta, tam_cluster, clusters_dir, clusters_total


def leer_directorio(archivo, tam_cluster, clusters_dir, clusters_total):
    """Interpreta las entradas del directorio FiUnamFS."""
    archivo.seek(tam_cluster)

    datos = archivo.read(tam_cluster * clusters_dir)
    archivos = []

    total_entradas = len(datos) // TAM_ENTRADA

    for indice in range(total_entradas):
        inicio = indice * TAM_ENTRADA
        entrada = datos[inicio:inicio + TAM_ENTRADA]

        tipo = entrada[0:1]

        # Las entradas libres no representan archivos.
        if tipo == b"-":
            continue

        if tipo != b"F":
            raise ValueError(
                f"Tipo de entrada desconocido en posicion {indice}."
            )

        nombre = entrada[1:16].decode("ascii").rstrip(" \x00")

        tamano, cluster_inicial = struct.unpack_from(
            "<II", entrada, 16
        )

        creacion = entrada[24:38].decode("ascii").strip(" \x00")
        modificacion = entrada[38:52].decode("ascii").strip(" \x00")

        # Comprobamos que los datos no apunten fuera del disco.
        if tamano > 0:
            clusters_ocupados = (
                tamano + tam_cluster - 1
            ) // tam_cluster

            if (cluster_inicial < 1 + clusters_dir
                    or cluster_inicial + clusters_ocupados > clusters_total):
                raise ValueError(
                    f"Ubicacion invalida del archivo '{nombre}'."
                )

        archivos.append({
            "nombre": nombre,
            "tamano": tamano,
            "cluster": cluster_inicial,
            "creacion": creacion,
            "modificacion": modificacion,
        })

    return archivos, total_entradas


def mostrar_archivos(archivos):
    """Presenta una tabla con los archivos encontrados."""
    print()
    print(
        f"{'Nombre':<17} {'Tamano':>10} "
        f"{'Cluster':>8} {'Creacion':<14} {'Modificacion':<14}"
    )
    print("-" * 70)

    for archivo in archivos:
        print(
            f"{archivo['nombre']:<17} "
            f"{archivo['tamano']:>10} "
            f"{archivo['cluster']:>8} "
            f"{archivo['creacion']:<14} "
            f"{archivo['modificacion']:<14}"
        )

    print("-" * 70)
    print(f"Total de archivos encontrados: {len(archivos)}")


def main():
    if len(sys.argv) != 2:
        print("Uso: python3 listar_directorio.py <imagen>")
        return 1

    ruta = Path(sys.argv[1])

    try:
        with ruta.open("rb") as imagen:
            etiqueta, tam_cluster, clusters_dir, clusters_total = (
                leer_superbloque(imagen, ruta.stat().st_size)
            )

            archivos, total_entradas = leer_directorio(
                imagen, tam_cluster, clusters_dir, clusters_total
            )

        print(f"Volumen: {etiqueta}")
        print(f"Entradas del directorio: {total_entradas}")
        mostrar_archivos(archivos)

    except (OSError, ValueError, UnicodeError, struct.error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
