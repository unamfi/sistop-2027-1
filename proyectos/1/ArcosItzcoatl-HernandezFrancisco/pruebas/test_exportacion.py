"""Pruebas de exportacion de archivos FiUnamFS."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fiunamfs import ErrorFiUnamFS, FiUnamFS
from crear_imagen_demo import crear_imagen


class PruebasExportacion(unittest.TestCase):

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        carpeta = Path(self.temporal.name)
        self.imagen = carpeta / "demo.img"
        self.destino = carpeta / "extraido.bin"

        crear_imagen(self.imagen)
        self.disco = FiUnamFS(self.imagen)

    def test_exportar_binario(self):
        self.disco.exportar_archivo("DATOS.BIN", self.destino)
        self.assertEqual(
            self.destino.read_bytes(), bytes(range(256))
        )

    def test_exportar_texto(self):
        self.disco.exportar_archivo("HOLA.TXT", self.destino)
        self.assertEqual(
            self.destino.read_bytes(), b"Hola desde FiUnamFS!\n"
        )

    def test_archivo_inexistente(self):
        with self.assertRaises(ErrorFiUnamFS):
            self.disco.exportar_archivo("NO_EXISTE.TXT", self.destino)

        self.assertFalse(self.destino.exists())

    def test_no_sobrescribir(self):
        self.destino.write_bytes(b"Archivo original")

        with self.assertRaises(FileExistsError):
            self.disco.exportar_archivo("DATOS.BIN", self.destino)

        self.assertEqual(
            self.destino.read_bytes(), b"Archivo original"
        )

    def test_imagen_sin_modificaciones(self):
        contenido_original = self.imagen.read_bytes()

        self.disco.exportar_archivo("DATOS.BIN", self.destino)

        self.assertEqual(
            self.imagen.read_bytes(), contenido_original
        )


if __name__ == "__main__":
    unittest.main()