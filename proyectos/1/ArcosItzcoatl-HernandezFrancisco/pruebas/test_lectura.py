"""Pruebas de la geometría del disco y lectura segura del directorio."""

from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fiunamfs import ErrorFiUnamFS, FiUnamFS, TAMANIO_CLUSTER
from crear_imagen_demo import crear_imagen


class PruebasLectura(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ruta = Path(self.temporal.name) / "demo.img"
        crear_imagen(self.ruta)
        self.disco = FiUnamFS(self.ruta)

    def cambiar(self, posicion: int, datos: bytes):
        with self.ruta.open("r+b") as imagen:
            imagen.seek(posicion)
            imagen.write(datos)

    def test_superbloque(self):
        meta = self.disco.leer_superbloque()
        self.assertEqual(meta.etiqueta, "DEMO_FIUNAMFS")
        self.assertEqual(meta.tamanio_cluster, 2048)
        self.assertEqual(meta.clusters_directorio, 4)
        self.assertEqual(meta.clusters_totales, 720)

    def test_archivos_y_directorio(self):
        archivos = self.disco.listar_archivos()
        self.assertEqual([a.nombre for a in archivos], ["HOLA.TXT", "DATOS.BIN"])
        self.assertEqual([a.cluster_inicial for a in archivos], [5, 6])
        self.assertEqual([a.tamanio for a in archivos], [21, 256])

    def test_datos_binarios_demo(self):
        with self.ruta.open("rb") as imagen:
            imagen.seek(6 * TAMANIO_CLUSTER)
            self.assertEqual(imagen.read(256), bytes(range(256)))

    def test_rechaza_firma_incorrecta(self):
        self.cambiar(0, b"NoUnamFS")
        with self.assertRaises(ErrorFiUnamFS):
            self.disco.leer_superbloque()

    def test_rechaza_version_incorrecta(self):
        self.cambiar(10, b"26-2")
        with self.assertRaises(ErrorFiUnamFS):
            self.disco.leer_superbloque()

    def test_rechaza_geometria_incorrecta(self):
        self.cambiar(40, struct.pack("<I", 1024))
        with self.assertRaises(ErrorFiUnamFS):
            self.disco.leer_superbloque()

    def test_rechaza_tamanio_incorrecto(self):
        with self.ruta.open("r+b") as imagen:
            imagen.truncate(1000)
        with self.assertRaises(ErrorFiUnamFS):
            self.disco.leer_superbloque()

    def test_rechaza_cluster_fuera_de_disco(self):
        self.cambiar(TAMANIO_CLUSTER + 20, struct.pack("<I", 720))
        with self.assertRaises(ErrorFiUnamFS):
            self.disco.listar_archivos()

    def test_rechaza_solapamiento(self):
        self.cambiar(TAMANIO_CLUSTER + 64 + 20, struct.pack("<I", 5))
        with self.assertRaises(ErrorFiUnamFS):
            self.disco.listar_archivos()

    def test_rechaza_fecha_invalida(self):
        self.cambiar(TAMANIO_CLUSTER + 24, b"20261304180000")
        with self.assertRaises(ErrorFiUnamFS):
            self.disco.listar_archivos()

    def test_rechaza_nombre_no_ascii(self):
        self.cambiar(TAMANIO_CLUSTER + 1, b"\xff")
        with self.assertRaises(ErrorFiUnamFS):
            self.disco.listar_archivos()

    def test_rechaza_nombres_repetidos(self):
        self.cambiar(TAMANIO_CLUSTER + 64 + 1, b"HOLA.TXT".ljust(15, b"\x00"))
        with self.assertRaises(ErrorFiUnamFS):
            self.disco.listar_archivos()


if __name__ == "__main__":
    unittest.main()
