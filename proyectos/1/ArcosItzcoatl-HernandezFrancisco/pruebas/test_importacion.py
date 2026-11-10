"""Pruebas de importación de archivos a una imagen FiUnamFS."""

from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fiunamfs import (ErrorFiUnamFS, FiUnamFS, TAMANIO_CLUSTER,
                      TAMANIO_DISCO, TAMANIO_ENTRADA)
from crear_imagen_demo import crear_imagen


class PruebasImportacion(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.carpeta = Path(self.temporal.name)
        self.imagen = self.carpeta / "demo.img"
        crear_imagen(self.imagen)
        self.disco = FiUnamFS(self.imagen)

    def origen(self, nombre, contenido):
        ruta = self.carpeta / nombre
        ruta.write_bytes(contenido)
        return ruta

    def test_importar_texto(self):
        ruta = self.origen("NUEVO.TXT", b"Prueba de importacion\n")
        archivo = self.disco.importar_archivo(ruta)
        self.assertEqual((archivo.nombre, archivo.cluster_inicial),
                         ("NUEVO.TXT", 7))
        self.assertIn("NUEVO.TXT", [a.nombre for a in self.disco.listar_archivos()])

    def test_importar_binario_de_varios_clusters(self):
        contenido = bytes(range(256)) * 17
        archivo = self.disco.importar_archivo(self.origen("DATOS2.BIN", contenido))
        self.assertEqual(archivo.tamanio, len(contenido))
        with self.imagen.open("rb") as imagen:
            imagen.seek(archivo.cluster_inicial * TAMANIO_CLUSTER)
            self.assertEqual(imagen.read(archivo.tamanio), contenido)

    def test_importar_archivo_vacio(self):
        archivo = self.disco.importar_archivo(self.origen("VACIO.TXT", b""))
        self.assertEqual(archivo.tamanio, 0)
        self.assertEqual(archivo.cluster_inicial, 0)
        self.assertEqual(len(self.disco.listar_archivos()), 3)

    def test_rechazar_nombre_duplicado_sin_cambiar_imagen(self):
        original = self.imagen.read_bytes()
        with self.assertRaises(ErrorFiUnamFS):
            self.disco.importar_archivo(self.origen("HOLA.TXT", b"Duplicado"))
        self.assertEqual(self.imagen.read_bytes(), original)

    def test_rechazar_nombre_no_ascii(self):
        with self.assertRaises(ErrorFiUnamFS):
            self.disco.importar_archivo(self.origen("cancionñ.txt", b"x"))

    def test_rechazar_nombre_demasiado_largo(self):
        with self.assertRaises(ErrorFiUnamFS):
            self.disco.importar_archivo(self.origen("NOMBRE_DEMASIADO_LARGO.TXT", b"x"))

    def test_rechazar_archivo_inexistente(self):
        with self.assertRaises(ErrorFiUnamFS):
            self.disco.importar_archivo(self.carpeta / "INEXISTENTE")

    def test_rechazar_falta_de_espacio_sin_cambiar_imagen(self):
        original = self.imagen.read_bytes()
        ruta = self.origen("ENORME.BIN", b"Z" * TAMANIO_DISCO)
        with self.assertRaises(ErrorFiUnamFS):
            self.disco.importar_archivo(ruta)
        self.assertEqual(self.imagen.read_bytes(), original)

    def test_preservar_datos_existentes(self):
        original = self.imagen.read_bytes()
        self.disco.importar_archivo(self.origen("NUEVO.TXT", b"datos nuevos"))
        actual = self.imagen.read_bytes()
        self.assertEqual(actual[5*TAMANIO_CLUSTER:7*TAMANIO_CLUSTER],
                         original[5*TAMANIO_CLUSTER:7*TAMANIO_CLUSTER])
        self.assertEqual([a.nombre for a in self.disco.listar_archivos()],
                         ["HOLA.TXT", "DATOS.BIN", "NUEVO.TXT"])

    def test_rechazar_directorio_lleno(self):
        with self.imagen.open("r+b") as imagen:
            for indice in range(2, 128):
                nombre = f"F{indice:03}.TXT".encode("ascii")
                registro = (b"F" + nombre.ljust(15, b"\x00")
                            + struct.pack("<II", 0, 0)
                            + b"20261106100000" * 2 + b"\x00" * 12)
                imagen.seek(TAMANIO_CLUSTER + indice * TAMANIO_ENTRADA)
                imagen.write(registro)
        original = self.imagen.read_bytes()
        with self.assertRaises(ErrorFiUnamFS):
            self.disco.importar_archivo(self.origen("EXTRA.TXT", b"hola"))
        self.assertEqual(self.imagen.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
