#!/usr/bin/env python3
"""
FiUnamFS 27-1: cliente para el micro sistema de archivos.

Proyecto 1 de Sistemas Operativos (Facultad de Ingeniería, UNAM).

Requisitos
----------
Python 3.8 o superior. Solo biblioteca estándar (sin dependencias).

"""

import os
import struct
import sys

# --- Constantes de la especificación -------------------------------------
NOMBRE_FS = b"FiUnamFS"
VERSION_FS = b"27-1"
TAM_ENTRADA = 64
TIPO_ARCHIVO = b"F"
# Una entrada vacía lleva '-' como tipo y un marcador en el nombre: '#..............'
# según la especificación, o 14 '#' más un nulo en el disco de ejemplo.
NOMBRES_VACIOS = (b"#" * 14, b"#" + b"." * 14)    # sin nulo final


class ErrorFS(Exception):
    """Error esperable (entrada inválida, disco lleno, archivo inexistente...)."""


class Entrada:
    """Un archivo del directorio (ya interpretado)."""

    def __init__(self, indice, nombre, tamano, cluster, creacion, modificacion):
        self.indice = indice          # posición dentro del directorio
        self.nombre = nombre
        self.tamano = tamano          # bytes
        self.cluster = cluster        # cluster inicial
        self.creacion = creacion      # 'AAAAMMDDHHMMSS'
        self.modificacion = modificacion


class FiUnamFS:
    """Acceso de bajo nivel a la imagen FiUnamFS."""

    def __init__(self, ruta):
        try:
            self.archivo = open(ruta, "r+b")
        except OSError as e:
            raise ErrorFS(f"No pude abrir la imagen '{ruta}': {e}")
        try:
            self._validar_superbloque()
        except Exception:
            self.archivo.close()
            raise

    # --- utilidades internas ---------------------------------------------
    def _leer(self, desplazamiento, cantidad):
        self.archivo.seek(desplazamiento)
        return self.archivo.read(cantidad)

    def _validar_superbloque(self):
        sb = self._leer(0, 64)
        if len(sb) < 52 or sb[0:8] != NOMBRE_FS:
            raise ErrorFS("La imagen no es un FiUnamFS (nombre incorrecto); no se modificará.")
        if sb[10:14] != VERSION_FS:
            version = sb[10:14].decode("ascii", "replace")
            raise ErrorFS(f"Versión no soportada ('{version}'); se requiere '27-1'.")
        self.etiqueta = sb[20:36].decode("ascii", "replace").rstrip(" \x00")
        self.tam_cluster, self.clusters_dir, self.clusters_total = struct.unpack("<III", sb[40:52])
        if self.tam_cluster == 0 or self.clusters_dir == 0 or self.clusters_total == 0:
            raise ErrorFS("Superbloque inconsistente (valores en cero).")
        self.archivo.seek(0, os.SEEK_END)
        if self.archivo.tell() < self.tam_cluster * self.clusters_total:
            raise ErrorFS("La imagen es más pequeña de lo que indica el superbloque.")
        self.inicio_datos = 1 + self.clusters_dir      # primer cluster de datos
        self.tam_directorio = self.clusters_dir * self.tam_cluster
        self.num_entradas = self.tam_directorio // TAM_ENTRADA

    def _entradas_crudas(self):
        directorio = self._leer(self.tam_cluster, self.tam_directorio)
        return [directorio[i * TAM_ENTRADA:(i + 1) * TAM_ENTRADA] for i in range(self.num_entradas)]

    @staticmethod
    def _interpretar(indice, crudo):
        """Devuelve una Entrada, o None si la posición está libre."""
        if crudo[0:1] != TIPO_ARCHIVO or crudo[1:16].rstrip(b"\x00") in NOMBRES_VACIOS:
            return None
        tamano, cluster = struct.unpack("<II", crudo[16:24])
        return Entrada(
            indice,
            crudo[1:16].decode("ascii", "replace").rstrip(" \x00"),
            tamano,
            cluster,
            crudo[24:38].decode("ascii", "replace"),
            crudo[38:52].decode("ascii", "replace"),
        )

    def _archivos(self):
        crudas = self._entradas_crudas()
        usados = [self._interpretar(i, c) for i, c in enumerate(crudas)]
        return crudas, usados

    # --- operaciones públicas --------------------
    def info(self):
        _, usados = self._archivos()
        return {
            "etiqueta": self.etiqueta,
            "tam_cluster": self.tam_cluster,
            "clusters_dir": self.clusters_dir,
            "clusters_total": self.clusters_total,
            "archivos": sum(1 for e in usados if e is not None),
            "capacidad_entradas": self.num_entradas,
        }

    def listar(self):
        _, usados = self._archivos()
        return [e for e in usados if e is not None]

    def cerrar(self):
        self.archivo.close()


# --- Interfaz de línea de comandos ---------------------------------------
AYUDA = """Órdenes:
  ls     lista los archivos del disco
  info   datos del volumen"""


def formatear_fecha(s):
    if len(s) == 14 and s.isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}:{s[12:14]}"
    return s


def mostrar_archivos(archivos):
    for e in archivos:
        print(f"{e.nombre:<14} {e.tamano:>9} B  cluster {e.cluster:<4} "
              f"creado {formatear_fecha(e.creacion)}  modif. {formatear_fecha(e.modificacion)}")


def mostrar_info(datos):
    print(f"Etiqueta del volumen: {datos['etiqueta']}")
    print(f"Tamaño de cluster:    {datos['tam_cluster']} bytes")
    print(f"Clusters en total:    {datos['clusters_total']} ({datos['clusters_dir']} del directorio)")
    print(f"Archivos:             {datos['archivos']} de {datos['capacidad_entradas']} posibles")


def atender(fs, partes):
    """Ejecuta una orden."""
    orden, args = partes[0].lower(), partes[1:]
    try:
        if orden in ("ls", "dir", "listar") and not args:
            archivos = fs.listar()
            if archivos:
                mostrar_archivos(archivos)
            else:
                print("(directorio vacío)")
        elif orden == "info" and not args:
            mostrar_info(fs.info())
        else:
            print(AYUDA)
    except ErrorFS as err:
        print(f"Error: {err}")


def main(argv):
    if len(argv) < 2:
        print("Uso: python3 fiunamfs.py <imagen> <orden> [argumentos]")
        print(AYUDA)
        return 1
    try:
        fs = FiUnamFS(argv[0])
    except ErrorFS as err:
        print(f"Error: {err}")
        return 1
    try:
        atender(fs, argv[1:])
    finally:
        fs.cerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
