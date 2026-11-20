import math
import os
import struct
from datetime import datetime


class FiUnamFS:
    """Manejador de sistema de archivos FiUnamFS."""

    tamano_entrada = 64

    def __init__(self, img_path: str):

        self.img_path = img_path
        self.etiqueta = ""
        self.tamano_cluster = 0
        self.dir_clusters = 0
        self.total_clusters = 0
        self.max_entradas = 0
        self.data_ini_cluster = 0

        # Etapa 1: Validar estructura y metadatos
        self._validar_superbloque()

    # Lectura y validacion del superbloloque
    def _validar_superbloque(self) -> None:
        """Leer los primeros 52 bytes del cluster 0 y valida el volumen"""
        with open(self.img_path, "rb") as f:
            sb = f.read(52)

        if len(sb) < 52:
            raise ValueError("El archivo es demasiado pequeño para contener un superbloque valido")

        # Decodifica etiqueta (bytes 20-35) sin nulos o espacios
        self.etiqueta = sb[20:36].decode("ascii", errors="replace").rstrip("\x00 ")

        # Sacar enteros de 32 bits en little endian
        self.tamano_cluster, self.dir_clusters, self.total_clusters = struct.unpack("<III", sb[40:52])

        # Verificar que el tamaño  del archivo sea igual al esperado en superbloque
        tamano_esperado = self.total_clusters * self.tamano_cluster
        tamano_real = os.path.getsize(self.img_path)
        if tamano_real != tamano_esperado:
            raise ValueError(
                f"Tamaño de imagen incorrecto, el superbloque declara {tamano_esperado} bytes, "
                f"pero el archivo mide {tamano_real} bytes"
            )
        # Calculo de entradas totales
        self.max_entradas = (self.dir_clusters * self.tamano_cluster) // self.tamano_entrada
        self.data_ini_cluster = 1 + self.dir_clusters

    # Recorrido de directorio y listado
    @staticmethod
    def _formatear_fecha(raw_fecha: bytes) -> str:
        """Convierte fecha a 'AAAA-MM-DD HH:MM:SS'"""
        s = raw_fecha.decode("ascii", errors="replace")
        if len(s) == 14 and s.isdigit():
            return f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}:{s[12:14]}"
        return s

    def listar_entradas(self) -> list[dict]:
        """Ver las 128 entradas del directorio y devuelve los archivos"""
        archivos = []
        offset_directorio = self.tamano_cluster  # Inicio del cluster 1

        with open(self.img_path, "rb") as f:
            f.seek(offset_directorio)
            for idx in range(self.max_entradas):
                raw = f.read(self.tamano_entrada)
                tipo = raw[0:1]

                # Solo procesar entradas activas F, no detenerse si hay vacio con -
                if tipo == b"F":
                    nombre = raw[1:16].decode("ascii").rstrip(" \x00")
                    tamano, cluster_ini = struct.unpack("<II", raw[16:24])
                    creacion = self._formatear_fecha(raw[24:38])
                    modificacion = self._formatear_fecha(raw[38:52])

                    archivos.append({
                        "indice": idx,
                        "nombre": nombre,
                        "tamano": tamano,
                        "cluster_ini": cluster_ini,
                        "creacion": creacion,
                        "modificacion": modificacion,
                    })

        return archivos

    # Extraccion de archvios

    def _buscar_entrada(self, nombre_fs: str) -> dict | None:
        """Busca un archivo activo por su nombre en el directorio"""
        for entrada in self.listar_entradas():
            if entrada["nombre"] == nombre_fs:
                return entrada
        return None

    def _primer_slot_libre(self) -> int | None:
        """Regresa el indice de la primera entrada vacia con - en el directorio"""
        with open(self.img_path, "rb") as f:
            f.seek(self.tamano_cluster)
            for idx in range(self.max_entradas):
                raw = f.read(self.tamano_entrada)
                if raw[0:1] == b"-":
                    return idx
        return None

    def _buscar_hueco_contiguo(self, clusters_necesarios: int) -> int:
        """Encuentra el primer cluster donde quepa el archivo en forma contiuga"""
        ocupados = []
        for ent in self.listar_entradas():
            n_clusters = max(1, math.ceil(ent["tamano"] / self.tamano_cluster))
            ocupados.append((ent["cluster_ini"], ent["cluster_ini"] + n_clusters))

        # Ordenar intervalo de entradas en ocupado
        ocupados.sort(key=lambda x: x[0])
        cursor = self.data_ini_cluster

        for inicio, fin in ocupados:
            if inicio - cursor >= clusters_necesarios:
                return cursor
            cursor = max(cursor, fin)

        if self.total_clusters - cursor >= clusters_necesarios:
            return cursor

    def copiar_desde_fs(self, nombre_fs: str, ruta_destino: str) -> None:
        """Copia un archivo desde el sistema hacia una ruta en mi compu"""
        entrada = self._buscar_entrada(nombre_fs)
        if not entrada:
            raise FileNotFoundError(f"El archivo '{nombre_fs}' no existe")

        if os.path.isdir(ruta_destino):
            ruta_destino = os.path.join(ruta_destino, nombre_fs)

        offset = entrada["cluster_ini"] * self.tamano_cluster
        with open(self.img_path, "rb") as f_img:
            f_img.seek(offset)
            datos = f_img.read(entrada["tamano"])

        with open(ruta_destino, "wb") as f_out:
            f_out.write(datos)

    # Asignacion e insercion de archivos

    def copiar_hacia_fs(self, ruta_origen: str, nombre_destino: str) -> None:
        """Copia un archivo desde la computadora hacia FiUnamFS de forma contigua"""
        if not os.path.isfile(ruta_origen):
            raise FileNotFoundError(f"No existe el archivo local: {ruta_origen}")
        # Longitud de nombre
        if len(nombre_destino) == 0 or len(nombre_destino) > 15:
            raise ValueError("El nombre destino debe tener entre 1 y 15 simbolos")
        # Requisito de ascii en el nomber
        if not all(32 <= ord(c) < 127 for c in nombre_destino):
            raise ValueError("El nombre destino solo admite caracteres ASCII de 7 bits")
        # Duplicados
        if self._buscar_entrada(nombre_destino):
            raise FileExistsError(f"Ya existe un archivo llamado '{nombre_destino}'")

        slot_libre = self._primer_slot_libre()
        if slot_libre is None:
            raise RuntimeError("El directorio está lleno (128 entradas ocupadas).")

        # Calcular clusters requeridos y espacio
        tamano = os.path.getsize(ruta_origen)
        clusters_req = max(1, math.ceil(tamano / self.tamano_cluster))
        cluster_ini = self._buscar_hueco_contiguo(clusters_req)

        with open(ruta_origen, "rb") as f_in:
            datos = f_in.read()

        # Rellenar el sobrante del cluster con ceros
        padding = (clusters_req * self.tamano_cluster) - len(datos)
        bloque_datos = datos + (b"\x00" * padding)

        # Construir la entrada de directorio
        ahora = datetime.now().strftime("%Y%m%d%H%M%S").encode("ascii")
        nombre_bytes = nombre_destino.encode("ascii").ljust(15, b" ")
        entrada_bin = struct.pack(
            "<1s15sII14s14s12s",
            b"F",
            nombre_bytes,
            tamano,
            cluster_ini,
            ahora,
            ahora,
            b"\x00" * 12,
        )

        # Escribir datos y metadatos en el disco
        with open(self.img_path, "r+b") as f_img:
            f_img.seek(cluster_ini * self.tamano_cluster)
            f_img.write(bloque_datos)

            f_img.seek(self.tamano_cluster + (slot_libre * self.tamano_entrada))
            f_img.write(entrada_bin)
   
    # Eliminacion de archivos
    def eliminar(self, nombre_fs: str) -> None:
        """Marca la entrada de directorio como vacio - sin borrar los clusters de dato"""
        entrada = self._buscar_entrada(nombre_fs)
        if not entrada:
            raise FileNotFoundError(f"El archivo '{nombre_fs}' no existe")

        entrada_vacia = b"-" + b"#.............." + (b"\x00" * 48)
        offset_dir = self.tamano_cluster + (entrada["indice"] * self.tamano_entrada)

        with open(self.img_path, "r+b") as f_img:
            f_img.seek(offset_dir)
            f_img.write(entrada_vacia)