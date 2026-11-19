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

    def _leer_entradas_directorio(self):
        """Lee todas las entradas de 64 bytes en los clusters del directorio (1 a 4)."""
        entradas = []
        bytes_directorio = self.clusters_directorio * self.tamano_cluster
        total_entradas = bytes_directorio // TAMANO_ENTRADA_DIR

        with open(self.ruta_imagen, "rb") as f:
            f.seek(self.tamano_cluster)
            datos_dir = f.read(bytes_directorio)

        for i in range(total_entradas):
            offset = i * TAMANO_ENTRADA_DIR
            bloque = datos_dir[offset : offset + TAMANO_ENTRADA_DIR]
            tipo = bloque[0:1].decode("ascii", errors="ignore")
            nombre = bloque[1:16].decode("ascii", errors="ignore").rstrip("\x00 ")

            if tipo == "F" and nombre and not nombre.startswith("#"):
                tamano = struct.unpack("<I", bloque[16:20])[0]
                cluster_inicial = struct.unpack("<I", bloque[20:24])[0]
                fecha_creacion = bloque[24:38].decode("ascii", errors="ignore")
                fecha_mod = bloque[38:52].decode("ascii", errors="ignore")
                entradas.append({
                    "indice": i,
                    "nombre": nombre,
                    "tamano": tamano,
                    "cluster_inicial": cluster_inicial,
                    "creacion": fecha_creacion,
                    "modificacion": fecha_mod
                })
            else:
                entradas.append({
                    "indice": i,
                    "libre": True
                })
        return entradas

    def listar_contenido(self):
        """Retorna únicamente los archivos activos en el directorio."""
        return [e for e in self._leer_entradas_directorio() if not e.get("libre")]

    def copiar_a_host(self, nombre_archivo, ruta_destino):
        """Extrae un archivo desde FiUnamFS hacia el sistema local."""
        archivos = self.listar_contenido()
        objetivo = next((a for a in archivos if a["nombre"] == nombre_archivo), None)

        if not objetivo:
            raise ErrorFiUnamFS(f"El archivo '{nombre_archivo}' no existe en FiUnamFS.")

        offset_datos = objetivo["cluster_inicial"] * self.tamano_cluster
        with open(self.ruta_imagen, "rb") as f_img:
            f_img.seek(offset_datos)
            contenido = f_img.read(objetivo["tamano"])

        with open(ruta_destino, "wb") as f_out:
            f_out.write(contenido)
