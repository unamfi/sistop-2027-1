
import os
import math
import tempfile
from datetime import datetime


class Operaciones:

    CLUSTER_INICIAL_DATOS = 5

    def __init__(self, sistema, directorio):
        self.sistema = sistema
        self.directorio = directorio

    def validar_nombre(self, nombre):
        """Comprueba que el nombre cumpla las reglas del sistema."""

        if not isinstance(nombre, str) or not nombre:
            raise ValueError("El nombre del archivo esta vacio")

        if nombre in (".", ".."):
            raise ValueError("Nombre de archivo no valido")

        if nombre.startswith("#"):
            raise ValueError("El nombre no puede comenzar con #")

        if nombre != nombre.strip():
            raise ValueError(
                "El nombre no puede comenzar ni terminar con espacios"
            )

        caracteres_no_permitidos = '<>:"/\\|?*'

        if any(
            caracter in caracteres_no_permitidos
            for caracter in nombre
        ):
            raise ValueError(
                "El nombre contiene caracteres no permitidos"
            )

        try:
            nombre_bytes = nombre.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError(
                "El nombre debe contener solamente caracteres ASCII"
            )

        if len(nombre_bytes) > 15:
            raise ValueError(
                "El nombre del archivo no puede superar 15 bytes"
            )

        if any(byte < 32 or byte > 126 for byte in nombre_bytes):
            raise ValueError(
                "El nombre contiene caracteres no permitidos"
            )

        return nombre_bytes

    def calcular_clusters(self, tamano):
        """Calcula cuantos clusters necesita un archivo."""

        if (
            not isinstance(tamano, int)
            or isinstance(tamano, bool)
            or tamano < 0
        ):
            raise ValueError("El tamano del archivo no es valido")

        tamano_cluster = self.sistema.tamano_cluster

        if (
            not isinstance(tamano_cluster, int)
            or tamano_cluster <= 0
        ):
            raise ValueError("El tamano del cluster no es valido")

        cantidad = math.ceil(tamano / tamano_cluster)

        # Los archivos vacios también reservan un cluster.
        return max(cantidad, 1)

    def obtener_clusters_ocupados(self):
        """Obtiene los clusters utilizados y detecta solapamientos."""

        archivos = self.directorio.listar()
        rangos = []

        for archivo in archivos:

            inicio = archivo["cluster_inicial"]
            tamano = archivo["tamano"]
            nombre = archivo["nombre"]

            if (
                not isinstance(inicio, int)
                or isinstance(inicio, bool)
            ):
                raise ValueError(
                    f"Cluster inicial invalido en {nombre}"
                )

            if inicio < self.CLUSTER_INICIAL_DATOS:
                raise ValueError(
                    f"Cluster inicial invalido en {nombre}"
                )

            cantidad = self.calcular_clusters(tamano)
            final = inicio + cantidad

            if final > self.sistema.clusters_totales:
                raise ValueError(
                    f"El archivo {nombre} excede el disco"
                )

            rangos.append((inicio, final, nombre))

        # Comprobar que ningún archivo comparta clusters.
        rangos.sort()

        for indice in range(1, len(rangos)):

            inicio_anterior, final_anterior, nombre_anterior = (
                rangos[indice - 1]
            )

            inicio_actual, final_actual, nombre_actual = (
                rangos[indice]
            )

            if inicio_actual < final_anterior:
                raise ValueError(
                    f"Los archivos {nombre_anterior} y "
                    f"{nombre_actual} comparten clusters"
                )

        ocupados = set()

        for inicio, final, nombre in rangos:
            ocupados.update(range(inicio, final))

        return ocupados

    def buscar_espacio_contiguo(self, clusters_necesarios):
        """Busca una secuencia de clusters libres."""

        if (
            not isinstance(clusters_necesarios, int)
            or isinstance(clusters_necesarios, bool)
            or clusters_necesarios <= 0
        ):
            raise ValueError(
                "La cantidad de clusters solicitada no es valida"
            )

        with self.sistema.lock:

            ocupados = self.obtener_clusters_ocupados()
            limite = self.sistema.clusters_totales

            for posible in range(
                self.CLUSTER_INICIAL_DATOS,
                limite - clusters_necesarios + 1
            ):

                candidatos = range(
                    posible,
                    posible + clusters_necesarios
                )

                if all(
                    cluster not in ocupados
                    for cluster in candidatos
                ):
                    return posible

        raise ValueError(
            "No hay espacio contiguo suficiente en FiUnamFS"
        )

    def copiar_desde_fiunamfs(
        self,
        nombre,
        carpeta_destino="archivos"
    ):
        """Copia un archivo de FiUnamFS a la computadora."""

        self.validar_nombre(nombre)

        with self.sistema.lock:

            if (
                self.sistema.archivo is None
                or self.sistema.archivo.closed
            ):
                raise RuntimeError("La imagen no esta abierta")

            archivo = self.directorio.buscar(nombre)

            if archivo is None:
                raise FileNotFoundError(
                    f"No existe el archivo {nombre} en FiUnamFS"
                )

            inicio_cluster = archivo["cluster_inicial"]
            tamano = archivo["tamano"]
            cantidad = self.calcular_clusters(tamano)

            # Validar todos los archivos y sus posibles solapamientos.
            ocupados = self.obtener_clusters_ocupados()

            clusters_archivo = set(
                range(
                    inicio_cluster,
                    inicio_cluster + cantidad
                )
            )

            if not clusters_archivo.issubset(ocupados):
                raise ValueError(
                    "Los clusters del archivo no estan registrados "
                    "correctamente"
                )

            if inicio_cluster < self.CLUSTER_INICIAL_DATOS:
                raise ValueError(
                    "El archivo tiene un cluster inicial invalido"
                )

            if (
                inicio_cluster + cantidad
                > self.sistema.clusters_totales
            ):
                raise ValueError(
                    "El archivo excede los limites del disco"
                )

            inicio = (
                inicio_cluster * self.sistema.tamano_cluster
            )

            self.sistema.archivo.seek(inicio)
            contenido = self.sistema.archivo.read(tamano)

        if len(contenido) != tamano:
            raise ValueError(
                "No se pudo leer el archivo completo"
            )

        os.makedirs(carpeta_destino, exist_ok=True)

        ruta_destino = os.path.join(
            carpeta_destino,
            nombre
        )

        archivo_temporal = None

        try:

            # Escribir primero en un archivo temporal.
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=carpeta_destino,
                prefix=".fiunamfs_",
                suffix=".tmp",
                delete=False
            ) as temporal:

                archivo_temporal = temporal.name

                escritos = temporal.write(contenido)

                if escritos != len(contenido):
                    raise IOError(
                        "No se pudo escribir la copia completa"
                    )

                temporal.flush()

            # Verificar que el archivo temporal sea idéntico.
            with open(archivo_temporal, "rb") as comprobacion:

                contenido_copiado = comprobacion.read()

            if contenido_copiado != contenido:
                raise IOError(
                    "La verificacion de la copia fallo"
                )

            # Reemplazar el destino cuando la copia esté lista.
            os.replace(archivo_temporal, ruta_destino)
            archivo_temporal = None

        finally:

            # Eliminar archivos temporales si ocurrió un error.
            if (
                archivo_temporal is not None
                and os.path.exists(archivo_temporal)
            ):
                os.remove(archivo_temporal)

        print(
            f"Archivo copiado correctamente: {ruta_destino}"
        )

        return ruta_destino

    def copiar_a_fiunamfs(self, ruta_origen):
        """Agrega un archivo de la computadora a FiUnamFS."""

        if not os.path.isfile(ruta_origen):
            raise FileNotFoundError(
                "El archivo de origen no existe"
            )

        nombre = os.path.basename(ruta_origen)
        nombre_bytes = self.validar_nombre(nombre)

        with open(ruta_origen, "rb") as origen:
            contenido = origen.read()

        tamano = len(contenido)
        tamano_cluster = self.sistema.tamano_cluster

        clusters_necesarios = self.calcular_clusters(tamano)

        capacidad_maxima = (
            self.sistema.clusters_totales
            - self.CLUSTER_INICIAL_DATOS
        )

        if clusters_necesarios > capacidad_maxima:
            raise ValueError(
                "El archivo es demasiado grande para FiUnamFS"
            )

        with self.sistema.lock:

            if (
                self.sistema.archivo is None
                or self.sistema.archivo.closed
            ):
                raise RuntimeError("La imagen no esta abierta")

            # Comprobar que el archivo no exista.
            if self.directorio.buscar(nombre) is not None:
                raise ValueError(
                    "Ya existe un archivo con ese nombre"
                )

            # Buscar espacio y una entrada disponible.
            cluster_inicial = self.buscar_espacio_contiguo(
                clusters_necesarios
            )

            posicion = self.directorio.entrada_libre()

            fecha = datetime.now().strftime(
                "%Y%m%d%H%M%S"
            ).encode("ascii")

            entrada = (
                b"F"
                + nombre_bytes.ljust(15, b" ")
                + tamano.to_bytes(4, "little")
                + cluster_inicial.to_bytes(4, "little")
                + fecha
                + fecha
                + bytes(12)
            )

            inicio_datos = (
                cluster_inicial * tamano_cluster
            )

            contenido_relleno = contenido.ljust(
                clusters_necesarios * tamano_cluster,
                b"\x00"
            )

            entrada_escrita = False

            try:

                # Escribir los datos antes de registrar el archivo.
                self.sistema.archivo.seek(inicio_datos)

                escritos = self.sistema.archivo.write(
                    contenido_relleno
                )

                if escritos != len(contenido_relleno):
                    raise IOError(
                        "No se pudieron escribir todos los datos"
                    )

                self.sistema.archivo.flush()

                # Verificar los datos escritos.
                self.sistema.archivo.seek(inicio_datos)

                verificacion = self.sistema.archivo.read(
                    len(contenido_relleno)
                )

                if verificacion != contenido_relleno:
                    raise IOError(
                        "La verificacion de escritura fallo"
                    )

                # Registrar el archivo en el directorio.
                entrada_escrita = True

                self.directorio.escribir_entrada(
                    posicion,
                    entrada
                )

            except Exception as error:

                errores_limpieza = []

                # Liberar la entrada si se intentó registrar.
                if entrada_escrita:

                    try:
                        self.directorio.liberar_entrada(posicion)

                    except Exception as error_limpieza:
                        errores_limpieza.append(error_limpieza)

                # Limpiar los clusters utilizados.
                try:

                    self.sistema.archivo.seek(inicio_datos)

                    escritos = self.sistema.archivo.write(
                        bytes(
                            clusters_necesarios * tamano_cluster
                        )
                    )

                    if escritos != (
                        clusters_necesarios * tamano_cluster
                    ):
                        raise IOError(
                            "No se pudo limpiar todo el espacio utilizado"
                        )

                    self.sistema.archivo.flush()

                except Exception as error_limpieza:
                    errores_limpieza.append(error_limpieza)

                if errores_limpieza:
                    raise RuntimeError(
                        "La operacion fallo y no se pudo completar "
                        "toda la limpieza de recuperacion"
                    ) from error

                raise

        print(
            f"Archivo agregado correctamente: {nombre}"
        )

        return nombre

    def eliminar_archivo(self, nombre):
        """Elimina un archivo del directorio de FiUnamFS."""

        self.validar_nombre(nombre)

        with self.sistema.lock:

            if (
                self.sistema.archivo is None
                or self.sistema.archivo.closed
            ):
                raise RuntimeError("La imagen no esta abierta")

            archivo = self.directorio.buscar(nombre)

            if archivo is None:
                raise FileNotFoundError(
                    f"No existe el archivo {nombre} en FiUnamFS"
                )

            # Validar los clusters antes de eliminar.
            ocupados = self.obtener_clusters_ocupados()

            cluster_inicial = archivo["cluster_inicial"]
            cantidad = self.calcular_clusters(
                archivo["tamano"]
            )

            clusters_archivo = set(
                range(
                    cluster_inicial,
                    cluster_inicial + cantidad
                )
            )

            if not clusters_archivo.issubset(ocupados):
                raise ValueError(
                    "Los clusters del archivo no estan registrados "
                    "correctamente"
                )

            if cluster_inicial < self.CLUSTER_INICIAL_DATOS:
                raise ValueError(
                    "El archivo tiene un cluster inicial invalido"
                )

            if (
                cluster_inicial + cantidad
                > self.sistema.clusters_totales
            ):
                raise ValueError(
                    "Los clusters del archivo exceden el disco"
                )

            # Liberar la entrada del directorio.
            # Los clusters quedarán disponibles para reutilizarse.
            self.directorio.liberar_entrada(
                archivo["posicion"]
            )

        print(
            f"Archivo eliminado correctamente: {nombre}"
        )

        return nombre
