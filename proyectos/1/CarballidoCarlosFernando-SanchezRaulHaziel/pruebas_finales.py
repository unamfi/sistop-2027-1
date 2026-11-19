
#!/usr/bin/env python3
"""Pruebas de regresion del proyecto FiUnamFS."""

import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from listar_directorio import leer_superbloque, leer_directorio
from agregar_archivo import agregar_archivo
from extraer_archivo import extraer_archivo
from eliminar_archivo import eliminar_archivo


def leer_contenidos(ruta):
    """Devuelve los archivos de una imagen y sus bytes."""
    resultado = {}

    with ruta.open("rb") as imagen:
        _, tam_cluster, clusters_dir, clusters_total = leer_superbloque(
            imagen, ruta.stat().st_size
        )

        archivos, _ = leer_directorio(
            imagen, tam_cluster, clusters_dir, clusters_total
        )

        for archivo in archivos:
            nombre = archivo["nombre"]
            imagen.seek(archivo["cluster"] * tam_cluster)
            contenido = imagen.read(archivo["tamano"])

            if len(contenido) != archivo["tamano"]:
                raise AssertionError("Lectura incompleta de " + nombre)

            if nombre in resultado:
                raise AssertionError("Nombre duplicado: " + nombre)

            resultado[nombre] = contenido

    return resultado


def comprobar(condicion, descripcion):
    if not condicion:
        raise AssertionError(descripcion)
    print("OK:", descripcion)


def main():
    carpeta = Path(__file__).resolve().parent
    original = carpeta.parent / "fiunamfs.img"

    if not original.is_file():
        raise FileNotFoundError(
            "No se encontro la imagen de referencia: " + str(original)
        )

    hash_original = hashlib.sha256(original.read_bytes()).digest()
    archivos_originales = leer_contenidos(original)

    comprobar(
        set(archivos_originales)
        == {"README.org", "logo.png", "mensaje.jpg"},
        "lectura de los tres archivos originales"
    )

    with tempfile.TemporaryDirectory() as temporal:
        temporal = Path(temporal)
        copia = temporal / "prueba.img"
        shutil.copyfile(original, copia)

        origen = temporal / "PRUEBA.TXT"
        destino = temporal / "recuperado.txt"
        contenido = b"Prueba automatica de FiUnamFS\n" * 200
        origen.write_bytes(contenido)

        agregar_archivo(copia, origen)

        despues = leer_contenidos(copia)

        comprobar(
            despues.get("PRUEBA.TXT") == contenido,
            "incorporacion y lectura del archivo"
        )

        comprobar(
            all(
                despues.get(nombre) == datos
                for nombre, datos in archivos_originales.items()
            ),
            "archivos originales intactos tras incorporar"
        )

        try:
            agregar_archivo(copia, origen)
        except ValueError:
            print("OK: nombre duplicado rechazado")
        else:
            raise AssertionError("Se permitio un nombre duplicado")

        comprobar(
            leer_contenidos(copia) == despues,
            "rechazo de duplicado sin modificar el directorio"
        )

        extraer_archivo(copia, "PRUEBA.TXT", destino)

        comprobar(
            destino.read_bytes() == contenido,
            "extraccion con bytes identicos"
        )

        eliminar_archivo(copia, "PRUEBA.TXT")

        comprobar(
            leer_contenidos(copia) == archivos_originales,
            "eliminacion y conservacion de archivos originales"
        )

        try:
            eliminar_archivo(copia, "INEXISTENTE.TXT")
        except ValueError:
            print("OK: eliminacion inexistente rechazada")
        else:
            raise AssertionError("Se permitio borrar un archivo inexistente")

        comprobar(
            leer_contenidos(copia) == archivos_originales,
            "directorio intacto despues del error"
        )

        # Ejecutar la prueba de los dos hilos desde el menu.
        resultado = subprocess.run(
            [sys.executable, str(carpeta / "fiunamfs.py"), str(copia)],
            input="5\n0\n",
            text=True,
            capture_output=True,
            timeout=30
        )

        comprobar(
            resultado.returncode == 0
            and "PRUEBA CORRECTA:" in resultado.stdout
            and "Los dos hilos finalizaron correctamente." in resultado.stdout,
            "dos hilos sincronizados y cierre correcto"
        )

        comprobar(
            leer_contenidos(copia) == archivos_originales,
            "imagen de prueba intacta tras concurrencia"
        )

    comprobar(
        hashlib.sha256(original.read_bytes()).digest() == hash_original,
        "imagen original del profesor sin modificaciones"
    )

    print("\nTODAS LAS PRUEBAS SUPERADAS")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("PRUEBA FALLIDA:", error, file=sys.stderr)
        sys.exit(1)
