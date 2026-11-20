
import os
import struct
import threading


class FiUnamFS:
    """Abre, valida y administra la imagen del sistema de archivos."""

    TAMANO_SECTOR = 512
    TAMANO_CLUSTER_ESPERADO = 2048
    CLUSTERS_DIRECTORIO_ESPERADOS = 4
    CLUSTERS_TOTALES_ESPERADOS = 720
    TAMANO_IMAGEN_ESPERADO = 1440 * 1024

    FIRMA_ESPERADA = b"FiUnamFS"
    VERSION_ESPERADA = b"27-1"

    def __init__(self, ruta):
        self.ruta = ruta
        self.archivo = None

        self.tamano_cluster = 0
        self.clusters_directorio = 0
        self.clusters_totales = 0

        # Evita que dos hilos accedan al disco al mismo tiempo.
        self.lock = threading.RLock()

    def abrir(self):
        """Abre la imagen y valida su estructura."""

        with self.lock:

            if self.archivo is not None and not self.archivo.closed:
                raise RuntimeError("La imagen ya se encuentra abierta")

            if not os.path.isfile(self.ruta):
                raise FileNotFoundError(
                    f"No se encontro la imagen del disco: {self.ruta}"
                )

            if os.path.getsize(self.ruta) != self.TAMANO_IMAGEN_ESPERADO:
                raise ValueError(
                    "La imagen debe medir exactamente 1440 KB"
                )

            self.archivo = open(self.ruta, "r+b")

            try:
                self.validar_superbloque()

            except Exception:
                self.cerrar()
                raise

    def validar_superbloque(self):
        """Comprueba que el superbloque corresponda a FiUnamFS."""

        with self.lock:

            if self.archivo is None or self.archivo.closed:
                raise RuntimeError("La imagen no esta abierta")

            self.archivo.seek(0)

            superbloque = self.archivo.read(self.TAMANO_SECTOR)

            if len(superbloque) != self.TAMANO_SECTOR:
                raise ValueError("El superbloque esta incompleto")

            identificacion = superbloque[0:8]
            version = superbloque[10:14]

            if identificacion != self.FIRMA_ESPERADA:
                raise ValueError(
                    "La imagen no corresponde a FiUnamFS"
                )

            if version != self.VERSION_ESPERADA:
                version_texto = version.decode(
                    "ascii", errors="replace"
                )

                raise ValueError(
                    f"Version no compatible: {version_texto}"
                )

            self.tamano_cluster = struct.unpack(
                "<I", superbloque[40:44]
            )[0]

            self.clusters_directorio = struct.unpack(
                "<I", superbloque[44:48]
            )[0]

            self.clusters_totales = struct.unpack(
                "<I", superbloque[48:52]
            )[0]

            # Validar el tamaño de cada cluster.
            if self.tamano_cluster != self.TAMANO_CLUSTER_ESPERADO:
                raise ValueError(
                    "El tamano de cluster debe ser 2048 bytes"
                )

            # Validar el espacio reservado para el directorio.
            if (
                self.clusters_directorio
                != self.CLUSTERS_DIRECTORIO_ESPERADOS
            ):
                raise ValueError(
                    "El directorio debe ocupar 4 clusters"
                )

            # Validar la cantidad total de clusters.
            if self.clusters_totales != self.CLUSTERS_TOTALES_ESPERADOS:
                raise ValueError(
                    "La imagen debe contener 720 clusters"
                )

            # Comprobar que la geometría corresponda al tamaño de imagen.
            tamano_calculado = (
                self.clusters_totales * self.tamano_cluster
            )

            if tamano_calculado != self.TAMANO_IMAGEN_ESPERADO:
                raise ValueError(
                    "La geometria del disco no coincide con su tamano"
                )

            # El cluster 0 contiene el superbloque.
            # Los siguientes clusters están reservados para el directorio.
            if 1 + self.clusters_directorio >= self.clusters_totales:
                raise ValueError(
                    "La distribucion de clusters del disco es invalida"
                )

            print("FiUnamFS validado correctamente")
            print("Version:", version.decode("ascii"))
            print("Tamano del cluster:", self.tamano_cluster)
            print("Clusters del directorio:", self.clusters_directorio)
            print("Clusters totales:", self.clusters_totales)

    def cerrar(self):
        """Cierra la imagen de forma segura."""

        with self.lock:

            if self.archivo is not None:

                try:
                    if not self.archivo.closed:
                        self.archivo.flush()

                finally:
                    self.archivo.close()
                    self.archivo = None
