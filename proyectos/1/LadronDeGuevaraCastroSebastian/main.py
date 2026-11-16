#!/usr/bin/env python3
"""
Interfaz del proyecto FiUnamFS, Sistemas Operativos (sistop-2027-1)
Sebastián Ladrón de Guevara Castro

Menú de texto para listar los archivos de una imagen FiUnamFS y copiarlos
a la computadora. Por ahora todo corre en un solo hilo, la interfaz llama
directamente a los métodos de FiUnamFS.

Se ejecuta con python3 main.py [imagen], si no se le pasa la imagen busca
fiunamfs.img en la carpeta actual.
"""

import os
import sys

from fiunamfs import FiUnamFS, ErrorFiUnamFS, LARGO_NOMBRE, formatear_fecha


def dibujar_barra(hecho, total, ancho=30):
    llenos = ancho * hecho // total if total else ancho
    porcentaje = 100 * hecho // total if total else 100
    print(f'\r  [{"#" * llenos}{"." * (ancho - llenos)}] {porcentaje:3d}%  {hecho:,} de {total:,} bytes',
          end='', flush=True)


class Interfaz:
    def __init__(self, fs):
        self.fs = fs

    def con_avance(self, operacion, *argumentos):
        """Ejecuta una copia mostrando la barra de progreso."""
        operacion(*argumentos, avance=dibujar_barra)
        print()

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

    def elegir_archivo(self, accion):
        """Muestra el listado y regresa el archivo que elija el usuario, o None."""
        entradas = self.mostrar_listado()
        if not entradas:
            return None
        while True:
            opcion = input(f'\n  Número del archivo a {accion} (Enter para cancelar): ').strip()
            if not opcion:
                return None
            if opcion.isdigit() and 1 <= int(opcion) <= len(entradas):
                return entradas[int(opcion) - 1]
            print(f'  Escribe un número del 1 al {len(entradas)}')

    def copiar_hacia_computadora(self):
        entrada = self.elegir_archivo('copiar')
        if entrada is None:
            return
        carpeta = limpiar_ruta(input('  Carpeta de destino (Enter para la carpeta actual): ')) or '.'
        if not os.path.isdir(carpeta):
            print(f'  "{carpeta}" no es una carpeta')
            return
        destino = os.path.join(carpeta, entrada.nombre)
        if os.path.exists(destino) and not confirmar(f'  "{destino}" ya existe, ¿lo reemplazo?'):
            return
        self.con_avance(self.fs.exportar, entrada.nombre, destino)
        print(f'  Listo, se copió a {os.path.abspath(destino)}')

    def menu(self):
        opciones = {
            '1': ('Listar los contenidos', self.mostrar_listado),
            '2': ('Copiar un archivo de FiUnamFS a la computadora', self.copiar_hacia_computadora),
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


def limpiar_ruta(texto):
    """
    Al arrastrar un archivo a la terminal, macOS y Linux escriben la ruta
    entre comillas o con los espacios escapados, aquí se deja como ruta normal.
    """
    texto = texto.strip()
    if len(texto) >= 2 and texto[0] == texto[-1] and texto[0] in '\'"':
        texto = texto[1:-1]
    else:
        texto = texto.replace('\\ ', ' ')
    return os.path.expanduser(texto)


def confirmar(pregunta):
    return input(f'{pregunta} (s/n): ').strip().lower() in ('s', 'si', 'sí')


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
