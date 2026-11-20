
class Directorio:

    TAMANO_ENTRADA = 64
    CLUSTER_INICIAL_DIRECTORIO = 1

    def __init__(self, sistema):
        self.sistema = sistema

    def _leer_directorio_completo(self):
        """Lee todas las entradas del directorio."""

        sistema = self.sistema

        if sistema.archivo is None or sistema.archivo.closed:
            raise RuntimeError("La imagen no esta abierta")

        inicio = (
            self.CLUSTER_INICIAL_DIRECTORIO
            * sistema.tamano_cluster
        )

        tamano = (
            sistema.clusters_directorio
            * sistema.tamano_cluster
        )

        with sistema.lock:
            sistema.archivo.seek(inicio)
            datos = sistema.archivo.read(tamano)

        if len(datos) != tamano:
            raise ValueError(
                "No se pudo leer todo el directorio"
            )

        return datos

    def listar(self):
        """Obtiene los archivos registrados en el directorio."""

        datos = self._leer_directorio_completo()
        archivos = []
        nombres_encontrados = set()

        for posicion in range(
            0,
            len(datos),
            self.TAMANO_ENTRADA
        ):

            entrada = datos[
                posicion:posicion + self.TAMANO_ENTRADA
            ]

            if len(entrada) != self.TAMANO_ENTRADA:
                raise ValueError(
                    "Se encontro una entrada incompleta"
                )

            tipo = entrada[0:1]

            if tipo != b"F":
                continue

            nombre_bytes = entrada[1:16]

            nombre = nombre_bytes.decode(
                "ascii",
                errors="replace"
            ).rstrip(" \x00")

            if not nombre or nombre.startswith("#"):
                continue

            # Validar que el nombre contenga caracteres ASCII imprimibles.
            if any(
                ord(caracter) < 32 or ord(caracter) > 126
                for caracter in nombre
            ):
                raise ValueError(
                    f"Nombre invalido en la entrada: {nombre!r}"
                )

            if nombre in nombres_encontrados:
                raise ValueError(
                    f"Archivo duplicado en el directorio: {nombre}"
                )

            nombres_encontrados.add(nombre)

            tamano = int.from_bytes(
                entrada[16:20],
                "little"
            )

            cluster = int.from_bytes(
                entrada[20:24],
                "little"
            )

            fecha_creacion = entrada[24:38].decode(
                "ascii",
                errors="replace"
            )

            fecha_modificacion = entrada[38:52].decode(
                "ascii",
                errors="replace"
            )

            informacion = {
                "nombre": nombre,
                "tamano": tamano,
                "cluster_inicial": cluster,
                "fecha_creacion": fecha_creacion,
                "fecha_modificacion": fecha_modificacion,
                "posicion": posicion
            }

            archivos.append(informacion)

        return archivos

    def mostrar(self):
        """Muestra los archivos registrados."""

        archivos = self.listar()

        print("\nCONTENIDO DE FIUNAMFS")
        print("-" * 60)

        if not archivos:
            print("El directorio esta vacio")
            return

        for archivo in archivos:

            print("Nombre:", archivo["nombre"])
            print("Tamano:", archivo["tamano"], "bytes")
            print("Cluster inicial:", archivo["cluster_inicial"])
            print("Fecha de creacion:", archivo["fecha_creacion"])
            print("Ultima modificacion:", archivo["fecha_modificacion"])

            print("-" * 60)

    def buscar(self, nombre):
        """Busca un archivo por su nombre."""

        for archivo in self.listar():

            if archivo["nombre"] == nombre:
                return archivo

        return None

    def entrada_libre(self):
        """Encuentra una entrada disponible."""

        datos = self._leer_directorio_completo()

        for posicion in range(
            0,
            len(datos),
            self.TAMANO_ENTRADA
        ):

            entrada = datos[
                posicion:posicion + self.TAMANO_ENTRADA
            ]

            tipo = entrada[0:1]
            nombre = entrada[1:16]

            if tipo == b"-" or nombre.startswith(b"#"):
                return posicion

        raise ValueError("El directorio esta lleno")

    def escribir_entrada(self, posicion, datos):
        """Escribe una entrada de 64 bytes en el directorio."""

        if not isinstance(datos, bytes):
            raise TypeError(
                "Los datos de la entrada deben ser bytes"
            )

        if len(datos) != self.TAMANO_ENTRADA:
            raise ValueError(
                "La entrada debe medir 64 bytes"
            )

        tamano_directorio = (
            self.sistema.clusters_directorio
            * self.sistema.tamano_cluster
        )

        if not isinstance(posicion, int):
            raise TypeError(
                "La posicion debe ser un numero entero"
            )

        if (
            posicion < 0
            or posicion + self.TAMANO_ENTRADA > tamano_directorio
            or posicion % self.TAMANO_ENTRADA != 0
        ):
            raise ValueError(
                "La posicion de la entrada no es valida"
            )

        inicio = (
            self.CLUSTER_INICIAL_DIRECTORIO
            * self.sistema.tamano_cluster
        )

        with self.sistema.lock:

            if (
                self.sistema.archivo is None
                or self.sistema.archivo.closed
            ):
                raise RuntimeError("La imagen no esta abierta")

            self.sistema.archivo.seek(inicio + posicion)

            escritos = self.sistema.archivo.write(datos)

            if escritos != self.TAMANO_ENTRADA:
                raise IOError(
                    "No se pudo escribir la entrada completa"
                )

            self.sistema.archivo.flush()

    def liberar_entrada(self, posicion):
        """Marca una entrada como disponible."""

        nombre_libre = b"#" + b"." * 14

        entrada = (
            b"-" + nombre_libre + bytes(48)
        )

        self.escribir_entrada(posicion, entrada)
