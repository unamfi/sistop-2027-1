#!/usr/bin/env python3
"""
Interfaz del proyecto FiUnamFS, Sistemas Operativos (sistop-2027-1)
Sebastián Ladrón de Guevara Castro

Menú de texto para listar los archivos de una imagen FiUnamFS. Por ahora
todo corre en un solo hilo, la interfaz llama directamente a los métodos de
FiUnamFS.

Se ejecuta con python3 main.py [imagen], si no se le pasa la imagen busca
fiunamfs.img en la carpeta actual.
"""

import sys

from fiunamfs import FiUnamFS, ErrorFiUnamFS, LARGO_NOMBRE, formatear_fecha


class Interfaz:
    def __init__(self, fs):
        self.fs = fs

    # ---- Pantallas ----

    def mostrar_listado(self):
        entradas = self.fs.listar()
        libre = self.fs.espacio_libre()
        print()
        if not entradas:
            print('  El disco está vacío')
        else:
            print(f'  {"#":>3}  {"Nombre":<{LARGO_NOMBRE}}  {"Tamaño":>9}  {"Cluster":>7}  '
                  f'{"Creado":<19}  {"Modificado":<19}')
            for numero, e in enumerate(entradas, start=1):
                print(f'  {numero:>3}  {e.nombre:<{LARGO_NOMBRE}}  {e.tamano:>9,}  {e.cluster:>7}  '
                      f'{formatear_fecha(e.creado):<19}  {formatear_fecha(e.modificado):<19}')
        print(f'\n  {len(entradas)} archivo(s), {libre // 1024:,} KB libres')
        return entradas

    def menu(self):
        opciones = {
            '1': ('Listar los contenidos', self.mostrar_listado),
        }
        salir = str(len(opciones) + 1)
        while True:
            print(f'\n=== FiUnamFS · volumen "{self.fs.etiqueta}" ===')
            for tecla, (texto, _) in opciones.items():
                print(f'  {tecla}) {texto}')
            print(f'  {salir}) Salir')
            opcion = input('Elige una opción: ').strip()
            if opcion == salir:
                return
            if opcion not in opciones:
                print(f'  Opción no válida, escribe un número del 1 al {salir}')
                continue
            try:
                opciones[opcion][1]()
            except (ErrorFiUnamFS, OSError) as e:
                print(f'\n  Error: {e}')


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else 'fiunamfs.img'
    try:
        fs = FiUnamFS(ruta)
    except ErrorFiUnamFS as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

    try:
        Interfaz(fs).menu()
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        fs.cerrar()


if __name__ == '__main__':
    main()
