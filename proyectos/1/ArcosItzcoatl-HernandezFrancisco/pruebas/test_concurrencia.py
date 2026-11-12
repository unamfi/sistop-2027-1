
"""Pruebas de concurrencia y sincronizacion de FiUnamFS."""

import queue
import threading
import time
import tempfile
import unittest
from pathlib import Path

from crear_imagen_demo import crear_imagen

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fiunamfs import FiUnamFS
from interfaz import InterfazFiUnamFS


class PruebasConcurrencia(unittest.TestCase):

    def setUp(self):
        """Crea una imagen y dos trabajadores para cada prueba."""
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.carpeta = Path(self.temporal.name)
        self.imagen = self.carpeta / "concurrencia.img"
        crear_imagen(self.imagen)

        # Se crea el objeto sin abrir una ventana de Tkinter.
        self.interfaz = InterfazFiUnamFS.__new__(
            InterfazFiUnamFS
        )

        self.interfaz.solicitudes = queue.Queue()
        self.interfaz.resultados = queue.Queue()
        self.interfaz.bloqueo = threading.Lock()
        self.interfaz.condicion = threading.Condition()
        self.interfaz.siguiente_turno = 0

        self.trabajadores = []

        for numero in range(1, 3):
            hilo = threading.Thread(
                target=self.interfaz.trabajador,
                name=f"Trabajador-{numero}",
                daemon=True
            )
            hilo.start()
            self.trabajadores.append(hilo)

    def tearDown(self):
        """Finaliza los trabajadores de cada prueba."""
        for _ in self.trabajadores:
            self.interfaz.solicitudes.put(None)

        for hilo in self.trabajadores:
            hilo.join(timeout=3)
            self.assertFalse(hilo.is_alive())

    def solicitar(self, numero, operacion, dato=None):
        self.interfaz.solicitudes.put(
            (numero, operacion, str(self.imagen), dato)
        )

    def esperar_resultados(self, cantidad):
        return [
            self.interfaz.resultados.get(timeout=5)
            for _ in range(cantidad)
        ]

    def test_dos_trabajadores_procesan_solicitudes(self):
        """Comprueba que los dos hilos atienden trabajo real."""

        # Detener temporalmente el acceso al disco permite
        # que cada trabajador tome una solicitud.
        self.interfaz.bloqueo.acquire()

        try:
            self.solicitar(0, "listar")
            self.solicitar(1, "listar")

            limite = time.monotonic() + 3

            while (
                not self.interfaz.solicitudes.empty()
                and time.monotonic() < limite
            ):
                time.sleep(0.01)

            self.assertTrue(
                self.interfaz.solicitudes.empty()
            )

        finally:
            self.interfaz.bloqueo.release()

        resultados = self.esperar_resultados(2)

        self.assertEqual(
            [resultado[0] for resultado in resultados],
            [0, 1]
        )

        nombres_hilos = {
            resultado[2] for resultado in resultados
        }

        self.assertEqual(
            nombres_hilos,
            {"Trabajador-1", "Trabajador-2"}
        )

        self.assertTrue(
            all(resultado[3] is None for resultado in resultados)
        )

    def test_importar_eliminar_y_reutilizar(self):
        """Comprueba operaciones consecutivas sincronizadas."""

        primero = self.carpeta / "PRIMERO.TXT"
        segundo = self.carpeta / "SEGUNDO.TXT"

        primero.write_bytes(b"Primer archivo concurrente")
        segundo.write_bytes(b"Segundo archivo concurrente")

        self.solicitar(0, "importar", str(primero))
        self.solicitar(1, "eliminar", "PRIMERO.TXT")
        self.solicitar(2, "importar", str(segundo))

        resultados = self.esperar_resultados(3)

        self.assertEqual(
            [resultado[0] for resultado in resultados],
            [0, 1, 2]
        )

        self.assertTrue(
            all(resultado[3] is None for resultado in resultados)
        )

        disco = FiUnamFS(self.imagen)
        archivos = disco.listar_archivos()

        nombres = [archivo.nombre for archivo in archivos]

        self.assertNotIn("PRIMERO.TXT", nombres)
        self.assertIn("SEGUNDO.TXT", nombres)

        nuevo = next(
            archivo for archivo in archivos
            if archivo.nombre == "SEGUNDO.TXT"
        )

        self.assertEqual(nuevo.cluster_inicial, 7)

        recuperado = self.carpeta / "recuperado.txt"
        disco.exportar_archivo("SEGUNDO.TXT", recuperado)

        self.assertEqual(
            recuperado.read_bytes(),
            segundo.read_bytes()
        )

    def test_error_no_detiene_los_trabajadores(self):
        """Un error no debe impedir atender otra solicitud."""

        self.solicitar(0, "eliminar", "NO_EXISTE.TXT")
        self.solicitar(1, "listar")

        resultados = self.esperar_resultados(2)

        self.assertIsNotNone(resultados[0][3])
        self.assertIsNone(resultados[1][3])

        self.assertEqual(len(resultados[1][5]), 2)

    def test_importacion_duplicada(self):
        """Dos solicitudes no deben crear nombres repetidos."""

        origen = self.carpeta / "REPETIDO.TXT"
        origen.write_bytes(b"Prueba de nombre duplicado")

        self.solicitar(0, "importar", str(origen))
        self.solicitar(1, "importar", str(origen))

        resultados = self.esperar_resultados(2)

        self.assertIsNone(resultados[0][3])
        self.assertIsNotNone(resultados[1][3])

        disco = FiUnamFS(self.imagen)

        nombres = [
            archivo.nombre
            for archivo in disco.listar_archivos()
        ]

        self.assertEqual(
            nombres.count("REPETIDO.TXT"),
            1
        )


if __name__ == "__main__":
    unittest.main()
