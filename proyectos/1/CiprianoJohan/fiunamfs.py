#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fiunamfs.py — Núcleo del micro sistema de archivos FiUnamFS (versión 27-1)

Proyecto 1 · Sistemas Operativos 2027-1 · Facultad de Ingeniería, UNAM
Autor: Cipriano Amador Johan Tadeo

Este módulo concentra todo lo que depende de la especificación de FiUnamFS:
la geometría del «diskette», la disposición del superbloque y del
directorio, y las conversiones de enteros de 32 bits little endian.
"""

import struct

# ---------------------------------------------------------------------------
# Geometría del dispositivo
# ---------------------------------------------------------------------------
TAM_SECTOR = 512
SECTORES_POR_CLUSTER = 4
TAM_CLUSTER = TAM_SECTOR * SECTORES_POR_CLUSTER        # 2048 bytes
TAM_DISCO = 1440 * 1024                                # un diskette de 1440 KB
TOTAL_CLUSTERS = TAM_DISCO // TAM_CLUSTER              # 720 clusters

# ---------------------------------------------------------------------------
# Superbloque (cluster #0): (inicio, fin) de cada campo, fin exclusivo
# ---------------------------------------------------------------------------
SB_NOMBRE = (0, 8)            # "FiUnamFS"
SB_VERSION = (10, 14)         # "27-1" (cadena, no número)
SB_ETIQUETA = (20, 36)        # etiqueta del volumen
SB_TAM_CLUSTER = (40, 44)     # tamaño del cluster en bytes
SB_CLUSTERS_DIR = (44, 48)    # clusters que ocupa el directorio
SB_CLUSTERS_TOTAL = (48, 52)  # clusters de la unidad completa

NOMBRE_FS = b"FiUnamFS"
VERSION_FS = b"27-1"

# ---------------------------------------------------------------------------
# Directorio: clusters 1 a 4, entradas de 64 bytes
# ---------------------------------------------------------------------------
CLUSTER_INICIO_DIR = 1
CLUSTERS_DIR = 4
TAM_ENTRADA = 64
ENTRADAS_DIR = CLUSTERS_DIR * TAM_CLUSTER // TAM_ENTRADA   # 128 entradas

ENT_TIPO = (0, 1)             # 'F' archivo, '-' entrada vacía
ENT_NOMBRE = (1, 16)          # 15 caracteres ASCII
ENT_TAMANO = (16, 20)         # tamaño en bytes
ENT_CLUSTER = (20, 24)        # cluster inicial (asignación contigua)
ENT_CREACION = (24, 38)       # AAAAMMDDHHMMSS
ENT_MODIFICACION = (38, 52)   # AAAAMMDDHHMMSS
# bytes 52–63: sin uso

TIPO_ARCHIVO = b"F"
TIPO_VACIO = b"-"
NOMBRE_VACIO = b"#" + b"." * 14          # "#.............." (15 bytes)
LONG_MAX_NOMBRE = ENT_NOMBRE[1] - ENT_NOMBRE[0]
FORMATO_FECHA = "%Y%m%d%H%M%S"

# Primer cluster disponible para datos: justo después del directorio
CLUSTER_INICIO_DATOS = CLUSTER_INICIO_DIR + CLUSTERS_DIR    # cluster 5


# ---------------------------------------------------------------------------
# Conversión de enteros (32 bits, little endian)
# ---------------------------------------------------------------------------
def a_entero(datos):
    """Convierte 4 bytes little endian a entero sin signo."""
    return struct.unpack("<I", datos)[0]


def de_entero(valor):
    """Convierte un entero sin signo a 4 bytes little endian."""
    return struct.pack("<I", valor)
