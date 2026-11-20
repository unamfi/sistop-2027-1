#!/usr/bin/env python3
"""
Interfaz y manejo de hilos del proyecto FiUnamFS, Sistemas Operativos
(sistop-2027-1)
Sebastián Ladrón de Guevara Castro

El programa trabaja con dos hilos.

- El hilo principal (interfaz) muestra el menú, le pregunta al usuario qué
  hacer y arma una Solicitud con la operación.
- El hilo del disco es el único que toca la imagen, saca las solicitudes de
  una cola, las ejecuta una por una y va reportando su avance.

Se comunican con dos mecanismos de sincronización, una queue.Queue por la que
viajan las solicitudes (productor-consumidor) y una threading.Condition en
cada Solicitud, con la que el hilo del disco avisa cuánto lleva copiado y
cuándo terminó, mientras la interfaz espera dormida y dibuja la barra de
progreso cada vez que la despiertan.

Se ejecuta con python3 main.py [imagen], si no se le pasa la imagen busca
fiunamfs.img en la carpeta actual.
"""

import os
import queue
import sys
import threading

from fiunamfs import FiUnamFS, ErrorFiUnamFS, LARGO_NOMBRE, formatear_fecha, validar_nombre


class Solicitud:
    """
    Una operación que la interfaz le pide al hilo del disco. Todos sus campos
    de estado (avance, terminada, resultado, error) se leen y se escriben
    solo mientras se tiene la condición, para que la interfaz nunca vea un
    estado a medias.
    """

    def __init__(self, operacion, *argumentos):
        self.operacion = operacion
        self.argumentos = argumentos
        self.condicion = threading.Condition()
        self.hecho = 0
        self.total = 0
        self.terminada = False
        self.resultado = None
        self.error = None

    def reportar_avance(self, hecho, total):
        with self.condicion:
            self.hecho, self.total = hecho, total
            self.condicion.notify()

    def terminar(self, resultado=None, error=None):
        with self.condicion:
            self.resultado, self.error = resultado, error
            self.terminada = True
            self.condicion.notify()


class HiloDisco(threading.Thread):
    """
    Dueño exclusivo del objeto FiUnamFS. Como ningún otro hilo lee ni escribe
    la imagen, no hace falta un candado sobre ella, las operaciones nunca se
    pueden encimar porque se atienden en orden desde la cola.
    """

    def __init__(self, fs):
        super().__init__(name='disco')
        self.fs = fs
        self.solicitudes = queue.Queue()

    def run(self):
        while True:
            solicitud = self.solicitudes.get()
            # None es la señal de que el programa terminó
            if solicitud is None:
                break
            try:
                solicitud.terminar(resultado=self._ejecutar(solicitud))
            except Exception as e:
                # Cualquier error se le regresa a la interfaz en lugar de
                # tirar el hilo, si no la interfaz se quedaría esperando
                solicitud.terminar(error=e)
        self.fs.cerrar()

    def _ejecutar(self, solicitud):
        fs = self.fs
        argumentos = solicitud.argumentos
        if solicitud.operacion == 'listar':
            return fs.listar(), fs.espacio_libre()
        if solicitud.operacion == 'exportar':
            return fs.exportar(*argumentos, avance=solicitud.reportar_avance)
        if solicitud.operacion == 'importar':
            return fs.importar(*argumentos, avance=solicitud.reportar_avance)
        if solicitud.operacion == 'eliminar':
            return fs.eliminar(*argumentos)
        raise ValueError(f'Operación desconocida: {solicitud.operacion}')


def dibujar_barra(hecho, total, ancho=30):
    llenos = ancho * hecho // total if total else ancho
    porcentaje = 100 * hecho // total if total else 100
    print(f'\r  [{"#" * llenos}{"." * (ancho - llenos)}] {porcentaje:3d}%  {hecho:,} de {total:,} bytes',
          end='', flush=True)


class Interfaz:
    def __init__(self, fs):
        self.etiqueta = fs.etiqueta
        self.hilo_disco = HiloDisco(fs)
        self.hilo_disco.start()

    def pedir(self, operacion, *argumentos, mostrar_avance=False):
        """Manda una solicitud al hilo del disco y espera a que la termine."""
        solicitud = Solicitud(operacion, *argumentos)
        self.hilo_disco.solicitudes.put(solicitud)

        dibujado = None
        with solicitud.condicion:
            while not solicitud.terminada:
                # wait() suelta la condición mientras duerme, así el hilo del
                # disco puede tomarla para reportar el avance
                solicitud.condicion.wait()
                # El aviso de que ya terminó también la despierta, en ese caso
                # el avance es el mismo y no vale la pena redibujarlo
                if mostrar_avance and solicitud.total and solicitud.hecho != dibujado:
                    dibujar_barra(solicitud.hecho, solicitud.total)
                    dibujado = solicitud.hecho
        if mostrar_avance and solicitud.total:
            print()

        if solicitud.error:
            raise solicitud.error
        return solicitud.resultado

    def terminar(self):
        self.hilo_disco.solicitudes.put(None)
        self.hilo_disco.join()

    # ---- Pantallas ----

    def mostrar_listado(self):
        entradas, libre = self.pedir('listar')
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
        self.pedir('exportar', entrada.nombre, destino, mostrar_avance=True)
        print(f'  Listo, se copió a {os.path.abspath(destino)}')

    def copiar_hacia_fiunamfs(self):
        origen = limpiar_ruta(input('\n  Ruta del archivo a copiar (puedes arrastrarlo aquí): '))
        if not origen:
            return
        if not os.path.isfile(origen):
            print(f'  "{origen}" no es un archivo')
            return

        # Se propone el mismo nombre, pero si no cabe en los 15 caracteres o
        # tiene caracteres raros se le pide otro al usuario
        nombre = os.path.basename(origen)
        while True:
            try:
                validar_nombre(nombre)
                break
            except ErrorFiUnamFS as e:
                print(f'  {e}')
                nombre = input(f'  Nombre dentro de FiUnamFS (máximo {LARGO_NOMBRE} caracteres, Enter para cancelar): ').strip()
                if not nombre:
                    return

        self.pedir('importar', origen, nombre, mostrar_avance=True)
        print(f'  Listo, se copió como "{nombre}"')

    def eliminar(self):
        entrada = self.elegir_archivo('eliminar')
        if entrada is None:
            return
        if confirmar(f'  ¿Seguro que quieres eliminar "{entrada.nombre}"?'):
            self.pedir('eliminar', entrada.nombre)
            print(f'  Se eliminó "{entrada.nombre}"')

    def menu(self):
        opciones = {
            '1': ('Listar los contenidos', self.mostrar_listado),
            '2': ('Copiar un archivo de FiUnamFS a la computadora', self.copiar_hacia_computadora),
            '3': ('Copiar un archivo de la computadora a FiUnamFS', self.copiar_hacia_fiunamfs),
            '4': ('Eliminar un archivo de FiUnamFS', self.eliminar),
        }
        salir = str(len(opciones) + 1)
        while True:
            print(f'\n=== FiUnamFS · volumen "{self.etiqueta}" ===')
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
    if fs.solo_lectura:
        print('Aviso: la imagen no tiene permiso de escritura, solo se puede listar y copiar hacia la computadora')

    interfaz = Interfaz(fs)
    try:
        interfaz.menu()
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        interfaz.terminar()


if __name__ == '__main__':
    main()
