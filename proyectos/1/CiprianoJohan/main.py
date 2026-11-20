#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — Interfaz de texto para FiUnamFS

Proyecto 1 · Sistemas Operativos 2027-1 · Facultad de Ingeniería, UNAM
Autor: Cipriano Amador Johan Tadeo

Menú navegable que no requiere conocer el código: cada opción pide lo que
necesita y ofrece valores por omisión. Toda operación sobre la imagen pasa
por VolumenConcurrente, es decir, por el hilo «disco».

Uso:
    python main.py [imagen.img]
"""

import os
import sys

from concurrencia import VolumenConcurrente
from fiunamfs import ErrorFiUnamFS, LONG_MAX_NOMBRE, formatear_fecha, validar_nombre

IMAGEN_POR_OMISION = os.path.join("..", "fiunamfs.img")
CARPETA_EXTRAIDOS = "extraidos"


def preguntar(texto, por_omision=""):
    """Lee una respuesta; Enter acepta el valor por omisión."""
    sufijo = f" [{por_omision}]" if por_omision else ""
    respuesta = input(f"{texto}{sufijo}: ").strip()
    # Al arrastrar un archivo a la terminal, Windows lo rodea de comillas
    respuesta = respuesta.strip('"').strip("'")
    return respuesta or por_omision


def confirmar(texto):
    return preguntar(f"{texto} (s/n)", "n").lower().startswith("s")


def mostrar_tabla(archivos):
    if not archivos:
        print("  (el volumen está vacío)")
        return
    print(f"  {'#':>2}  {'Nombre':<16} {'Tamaño':>9} {'Cluster':>7}  Modificación")
    print("  " + "-" * 64)
    for numero, e in enumerate(archivos, 1):
        print(f"  {numero:>2}  {e.nombre:<16} {e.tamano:>9} {e.cluster:>7}  "
              f"{formatear_fecha(e.modificacion)}")


def elegir_archivo(volumen, accion):
    """Muestra el listado y deja escoger un archivo por número o por nombre."""
    archivos = volumen.listar()
    mostrar_tabla(archivos)
    if not archivos:
        return None
    eleccion = preguntar(f"Número o nombre del archivo a {accion} (Enter cancela)")
    if not eleccion:
        return None
    if eleccion.isdigit() and 1 <= int(eleccion) <= len(archivos):
        return archivos[int(eleccion) - 1].nombre
    return eleccion


# ---------------------------------------------------------------------------
# Opciones del menú
# ---------------------------------------------------------------------------
def opcion_listar(volumen):
    mostrar_tabla(volumen.listar())


def opcion_extraer(volumen):
    nombre = elegir_archivo(volumen, "copiar a tu equipo")
    if not nombre:
        return
    destino = preguntar("Carpeta destino", CARPETA_EXTRAIDOS)
    os.makedirs(destino, exist_ok=True)
    ruta = volumen.extraer(nombre, destino)
    print(f"✓ Copiado a {ruta}")


def opcion_copiar(volumen):
    ruta = preguntar("Ruta del archivo en tu equipo (puedes arrastrarlo aquí)")
    if not ruta:
        return
    if not os.path.isfile(ruta):
        print(f"✗ No existe el archivo '{ruta}'")
        return
    nombre = os.path.basename(ruta)
    # Si el nombre no cumple la especificación, se pide otro en lugar de fallar
    while True:
        try:
            validar_nombre(nombre)
            break
        except ErrorFiUnamFS as error:
            print(f"  {error}")
            nombre = preguntar(f"Nombre dentro de FiUnamFS (ASCII, máx. {LONG_MAX_NOMBRE})")
            if not nombre:
                return
    entrada = volumen.copiar_hacia(ruta, nombre)
    print(f"✓ '{entrada.nombre}' copiado: {entrada.tamano} bytes desde el cluster {entrada.cluster}")


def opcion_eliminar(volumen):
    nombre = elegir_archivo(volumen, "eliminar")
    if not nombre:
        return
    if confirmar(f"¿Eliminar '{nombre}' del volumen?"):
        volumen.eliminar(nombre)
        print(f"✓ '{nombre}' eliminado")


def opcion_bitacora(volumen):
    print(f"  {volumen.superbloque}")
    print("  Bitácora (registrada por el hilo «bitácora»):")
    for linea in volumen.obtener_bitacora():
        print(f"    {linea}")


OPCIONES = [
    ("Listar el contenido", opcion_listar),
    ("Copiar de FiUnamFS a mi equipo", opcion_extraer),
    ("Copiar de mi equipo a FiUnamFS", opcion_copiar),
    ("Eliminar un archivo", opcion_eliminar),
    ("Información del volumen y bitácora", opcion_bitacora),
]


def menu(volumen):
    while True:
        # Lectura directa del estado compartido (sin pasar por la cola)
        archivos, libres, _ = volumen.estado.instantanea()
        print(f"\n=== FiUnamFS · '{volumen.superbloque.etiqueta}' · "
              f"{len(archivos)} archivo(s) · {libres} clusters libres ===")
        for numero, (texto, _) in enumerate(OPCIONES, 1):
            print(f"  {numero}. {texto}")
        print("  0. Salir")

        eleccion = preguntar("Opción")
        if eleccion == "0":
            return
        if not eleccion.isdigit() or not 1 <= int(eleccion) <= len(OPCIONES):
            print("✗ Opción no válida")
            continue
        print()
        try:
            OPCIONES[int(eleccion) - 1][1](volumen)
        except (OSError, ErrorFiUnamFS) as error:
            print(f"✗ {error}")


def main():
    # Git Bash en Windows conecta Python por tuberías: se fuerza UTF-8 (para
    # los acentos) y escritura por línea (para que el menú aparezca al momento)
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except (AttributeError, ValueError):
        pass

    try:
        ruta = sys.argv[1] if len(sys.argv) > 1 else preguntar(
            "Imagen de FiUnamFS", IMAGEN_POR_OMISION)
        with VolumenConcurrente(ruta) as volumen:
            print(volumen.superbloque)
            menu(volumen)
    except (OSError, ErrorFiUnamFS) as error:
        print(f"✗ No se pudo abrir la imagen: {error}", file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print()
    print("¡Hasta luego!")


if __name__ == "__main__":
    main()
