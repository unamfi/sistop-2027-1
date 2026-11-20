
"""Pruebas de eliminacion de archivos en FiUnamFS."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fiunamfs import FiUnamFS, ErrorFiUnamFS
from crear_imagen_demo import crear_imagen


class PruebasEliminacion(unittest.TestCase):

    def setUp(self):
        """Prepara una imagen independiente para cada prueba."""
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.carpeta = Path(self.temporal.name)
        self.imagen = self.carpeta / "demo.img"

        crear_imagen(self.imagen)
        self.disco = FiUnamFS(self.imagen)

        self.fuente = self.carpeta / "BORRAR.TXT"
        self.fuente.write_bytes(b"Contenido de prueba\n")

    def test_eliminar_archivo(self):
        self.disco.importar_archivo(self.fuente)
        eliminado = self.disco.eliminar_archivo("BORRAR.TXT")

        nombres = [a.nombre for a in self.disco.listar_archivos()]

        self.assertEqual(eliminado.nombre, "BORRAR.TXT")
        self.assertNotIn("BORRAR.TXT", nombres)
        self.assertEqual(len(nombres), 2)

    def test_reutilizar_cluster(self):
        primero = self.disco.importar_archivo(self.fuente)
        self.disco.eliminar_archivo("BORRAR.TXT")

        nuevo = self.carpeta / "NUEVO.TXT"
        nuevo.write_bytes(b"Archivo nuevo\n")

        segundo = self.disco.importar_archivo(nuevo)

        self.assertEqual(
            primero.cluster_inicial,
            segundo.cluster_inicial
        )

        recuperado = self.carpeta / "recuperado.txt"
        self.disco.exportar_archivo("NUEVO.TXT", recuperado)

        self.assertEqual(recuperado.read_bytes(), nuevo.read_bytes())

    def test_eliminar_archivo_inexistente(self):
        imagen_original = self.imagen.read_bytes()

        with self.assertRaises(ErrorFiUnamFS):
            self.disco.eliminar_archivo("NO_EXISTE.TXT")

        self.assertEqual(self.imagen.read_bytes(), imagen_original)

    def test_no_eliminar_dos_veces(self):
        self.disco.importar_archivo(self.fuente)
        self.disco.eliminar_archivo("BORRAR.TXT")

        imagen_original = self.imagen.read_bytes()

        with self.assertRaises(ErrorFiUnamFS):
            self.disco.eliminar_archivo("BORRAR.TXT")

        self.assertEqual(self.imagen.read_bytes(), imagen_original)

    def test_conservar_archivos_existentes(self):
        antes = self.carpeta / "antes.bin"
        despues = self.carpeta / "despues.bin"

        self.disco.exportar_archivo("DATOS.BIN", antes)

        self.disco.importar_archivo(self.fuente)
        self.disco.eliminar_archivo("BORRAR.TXT")

        self.disco.exportar_archivo("DATOS.BIN", despues)

        self.assertEqual(antes.read_bytes(), despues.read_bytes())

        nombres = [a.nombre for a in self.disco.listar_archivos()]
        self.assertIn("HOLA.TXT", nombres)
        self.assertIn("DATOS.BIN", nombres)

    def test_mantener_tamanio_del_disco(self):
        tamanio_original = self.imagen.stat().st_size

        self.disco.importar_archivo(self.fuente)
        self.disco.eliminar_archivo("BORRAR.TXT")

        self.assertEqual(
            self.imagen.stat().st_size,
            tamanio_original
        )


if __name__ == "__main__":
    unittest.main()
