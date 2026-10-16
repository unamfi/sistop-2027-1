"""Pruebas de invariantes concurrentes. Ejecutar: python3 -m unittest -v"""
import unittest
from santa_claus import TallerSanta


class PruebasSanta(unittest.TestCase):
    def verificar(self, num_elfos, semilla):
        # Escala pequeña para no hacer esperar durante las pruebas.
        datos = TallerSanta(num_elfos, escala=0.015, semilla=semilla, mostrar=False).ejecutar()
        grupos = datos["grupos"]
        atendidos = [elfo for grupo in grupos for elfo in grupo]
        pedidos = datos["solicitudes"]
        cancelados = datos["cancelados"]
        self.assertTrue(datos["viaje"])
        self.assertEqual(set(datos["abordados"]), set(range(1, 10)))
        self.assertEqual(len(datos["abordados"]), 9)
        self.assertTrue(all(len(grupo) == 3 for grupo in grupos))
        self.assertEqual(len(atendidos), len(set(atendidos)))
        self.assertEqual(set(pedidos), set(atendidos) | set(cancelados))
        self.assertFalse(set(atendidos) & set(cancelados))
        self.assertEqual(len(pedidos), len(set(pedidos)))
        self.assertLessEqual(len(pedidos), num_elfos)
        self.assertEqual(atendidos, pedidos[:len(atendidos)])        #fifo, el orden de los atendidos respeta el de la cola de solicitudes.

    def test_cero_elfos(self):
        self.verificar(0, 1)

    def test_un_elfo(self):
        self.verificar(1, 2)

    def test_dos_elfos(self):
        self.verificar(2, 3)

    def test_tres_elfos(self):
        self.verificar(3, 4)

    def test_doce_elfos(self):
        self.verificar(12, 42)

    def test_treinta_elfos(self):
        self.verificar(30, 7)

    def test_carga_varias_semillas(self):
        for semilla in range(10):
            with self.subTest(semilla=semilla):
                self.verificar(25, semilla)


if __name__ == "__main__":
    unittest.main()
