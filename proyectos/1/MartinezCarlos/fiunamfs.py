#!/usr/bin/env python3
import os
import sys
import struct
import math
from datetime import datetime

# Constantes de especificación FiUnamFS
TAMANO_SECTOR = 512
SECTORES_POR_CLUSTER = 4
TAMANO_CLUSTER = TAMANO_SECTOR * SECTORES_POR_CLUSTER  # 2048 bytes
TAMANO_DISCO_BYTES = 1440 * 1024  # 1474560 bytes (720 clusters)
TAMANO_ENTRADA_DIR = 64

class ErrorFiUnamFS(Exception):
    """Excepción personalizada para errores de validación o estructura del sistema."""
    pass

class SistemaArchivosFiUnamFS:
    def __init__(self, ruta_imagen):
        self.ruta_imagen = ruta_imagen
        self.etiqueta = ""
        self.tamano_cluster = TAMANO_CLUSTER
        self.clusters_directorio = 4
        self.clusters_totales = 720
        self._validar_superbloque()

    def _validar_superbloque(self):
        """Valida la firma 'FiUnamFS' y la versión '27-1' en el cluster 0."""
        if not os.path.exists(self.ruta_imagen):
            raise ErrorFiUnamFS(f"No se encontró el archivo de imagen: {self.ruta_imagen}")

        with open(self.ruta_imagen, "rb") as f:
            superbloque = f.read(TAMANO_CLUSTER)

        if len(superbloque) < TAMANO_CLUSTER:
            raise ErrorFiUnamFS("La imagen de disco está truncada o corrupta.")

        nombre_fs = superbloque[0:8].decode("ascii", errors="ignore").strip("\x00 ")
        if nombre_fs != "FiUnamFS":
            raise ErrorFiUnamFS(f"Identificador inválido: '{nombre_fs}'. Se esperaba 'FiUnamFS'.")

        version = superbloque[10:14].decode("ascii", errors="ignore").strip("\x00 ")
        if version != "27-1":
            raise ErrorFiUnamFS(f"Versión incompatible: '{version}'. Se esperaba '27-1'.")

        self.etiqueta = superbloque[20:36].decode("ascii", errors="ignore").strip("\x00 ")
        self.tamano_cluster = struct.unpack("<I", superbloque[40:44])[0]
        self.clusters_directorio = struct.unpack("<I", superbloque[44:48])[0]
        self.clusters_totales = struct.unpack("<I", superbloque[48:52])[0]
