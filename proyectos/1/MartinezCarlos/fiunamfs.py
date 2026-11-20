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

    def _buscar_espacio_continuo(self, clusters_requeridos, archivos_activos):
        """Encuentra el primer bloque de clusters contiguos libres tras el directorio."""
        inicio_datos = 1 + self.clusters_directorio
        mapa_ocupados = [False] * self.clusters_totales

        for c in range(inicio_datos):
            mapa_ocupados[c] = True

        for arch in archivos_activos:
            c_ini = arch["cluster_inicial"]
            c_necesarios = max(1, math.ceil(arch["tamano"] / self.tamano_cluster))
            for c in range(c_ini, min(c_ini + c_necesarios, self.clusters_totales)):
                mapa_ocupados[c] = True

        consecutivos = 0
        cluster_candidato = -1

        for c in range(inicio_datos, self.clusters_totales):
            if not mapa_ocupados[c]:
                if consecutivos == 0:
                    cluster_candidato = c
                consecutivos += 1
                if consecutivos == clusters_requeridos:
                    return cluster_candidato
            else:
                consecutivos = 0
                cluster_candidato = -1

        return -1

    def copiar_desde_host(self, ruta_origen, nombre_destino=None):
        """Copia un archivo local hacia FiUnamFS respetando asignación continua y US-ASCII."""
        if not os.path.isfile(ruta_origen):
            raise ErrorFiUnamFS(f"El archivo origen '{ruta_origen}' no existe en tu equipo.")

        if not nombre_destino:
            nombre_destino = os.path.basename(ruta_origen)

        try:
            nombre_bytes = nombre_destino.encode("ascii")
        except UnicodeEncodeError:
            raise ErrorFiUnamFS("El nombre debe contener únicamente caracteres US-ASCII (sin acentos ni ñ).")

        if len(nombre_bytes) > 15 or len(nombre_bytes) == 0:
            raise ErrorFiUnamFS("El nombre del archivo en FiUnamFS debe medir entre 1 y 15 caracteres.")

        entradas = self._leer_entradas_directorio()
        activos = [e for e in entradas if not e.get("libre")]

        if any(a["nombre"] == nombre_destino for a in activos):
            raise ErrorFiUnamFS(f"Ya existe un archivo llamado '{nombre_destino}' en FiUnamFS.")

        entrada_libre = next((e for e in entradas if e.get("libre")), None)
        if not entrada_libre:
            raise ErrorFiUnamFS("El directorio está lleno (máximo 128 entradas).")

        tamano_archivo = os.path.getsize(ruta_origen)
        clusters_necesarios = max(1, math.ceil(tamano_archivo / self.tamano_cluster))
        cluster_inicio = self._buscar_espacio_continuo(clusters_necesarios, activos)

        if cluster_inicio == -1:
            raise ErrorFiUnamFS("No hay espacio contiguo suficiente en el disco FiUnamFS.")

        with open(ruta_origen, "rb") as f_in:
            datos = f_in.read()

        ahora_str = datetime.now().strftime("%Y%m%d%H%M%S").encode("ascii")

        nueva_entrada = bytearray(TAMANO_ENTRADA_DIR)
        nueva_entrada[0:1] = b"F"
        nueva_entrada[1 : 1 + len(nombre_bytes)] = nombre_bytes
        nueva_entrada[16:20] = struct.pack("<I", tamano_archivo)
        nueva_entrada[20:24] = struct.pack("<I", cluster_inicio)
        nueva_entrada[24:38] = ahora_str
        nueva_entrada[38:52] = ahora_str

        with open(self.ruta_imagen, "r+b") as f_img:
            f_img.seek(cluster_inicio * self.tamano_cluster)
            f_img.write(datos)
            offset_dir = self.tamano_cluster + (entrada_libre["indice"] * TAMANO_ENTRADA_DIR)
            f_img.seek(offset_dir)
            f_img.write(nueva_entrada)

    def eliminar_archivo(self, nombre_archivo):
        """Marca la entrada del directorio como libre ('-' y '#..............')."""
        entradas = self._leer_entradas_directorio()
        objetivo = next((e for e in entradas if not e.get("libre") and e["nombre"] == nombre_archivo), None)

        if not objetivo:
            raise ErrorFiUnamFS(f"El archivo '{nombre_archivo}' no existe en FiUnamFS.")

        entrada_vacia = bytearray(TAMANO_ENTRADA_DIR)
        entrada_vacia[0:1] = b"-"
        entrada_vacia[1:16] = b"#.............."

        with open(self.ruta_imagen, "r+b") as f_img:
            offset_dir = self.tamano_cluster + (objetivo["indice"] * TAMANO_ENTRADA_DIR)
            f_img.seek(offset_dir)
            f_img.write(entrada_vacia)
