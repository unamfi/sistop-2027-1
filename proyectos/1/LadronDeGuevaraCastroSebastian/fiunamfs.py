"""
Estructuras del micro sistema de archivos FiUnamFS, proyecto de Sistemas
Operativos (sistop-2027-1)
Sebastián Ladrón de Guevara Castro

Este módulo sabe leer y escribir las tres zonas del disco, el superbloque
(cluster 0), el directorio (clusters 1 a 4) y el área de datos. No sabe nada
de hilos, de eso se encarga main.py, que crea un solo objeto FiUnamFS y lo
usa únicamente desde el hilo del disco.
"""

import math
import os
import struct
from dataclasses import dataclass
from datetime import datetime

NOMBRE_FS = b'FiUnamFS'
VERSION_FS = b'27-1'

# El directorio empieza justo después del superbloque
CLUSTER_DIRECTORIO = 1

TAM_ENTRADA = 64
LARGO_NOMBRE = 15
TIPO_ARCHIVO = b'F'
TIPO_VACIO = b'-'
# La especificación dice que las entradas vacías llevan '#..............' en
# el nombre, pero la imagen del profe usa '##############', se aceptan las dos
# y al eliminar se escribe como en la imagen
NOMBRE_VACIO = '#' * (LARGO_NOMBRE - 1)
NOMBRE_VACIO_ESPECIFICACION = '#' + '.' * (LARGO_NOMBRE - 1)
NOMBRES_RESERVADOS = (NOMBRE_VACIO, NOMBRE_VACIO_ESPECIFICACION)
FECHA_VACIA = '0' * 14
FORMATO_FECHA = '%Y%m%d%H%M%S'

# Una entrada completa del directorio. Los enteros van en little endian (<)
# y los 12 bytes del final (12x) son el espacio reservado
FORMATO_ENTRADA = '<c15sII14s14s12x'


class ErrorFiUnamFS(Exception):
    """Problema con la imagen o con alguna operación sobre ella."""


@dataclass
class Entrada:
    """Un archivo del directorio, junto con la posición que ocupa en él."""
    indice: int
    nombre: str
    tamano: int
    cluster: int
    creado: str
    modificado: str


def formatear_fecha(fecha):
    """Convierte 'AAAAMMDDHHMMSS' a 'AAAA-MM-DD HH:MM:SS' si es válida."""
    try:
        return datetime.strptime(fecha, FORMATO_FECHA).strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return fecha


def validar_nombre(nombre):
    """Lanza ErrorFiUnamFS si el nombre no se puede guardar en el directorio."""
    if not nombre:
        raise ErrorFiUnamFS('El nombre no puede estar vacío')
    if len(nombre) > LARGO_NOMBRE:
        raise ErrorFiUnamFS(f'El nombre "{nombre}" pasa de {LARGO_NOMBRE} caracteres')
    # La especificación solo permite US-ASCII de 7 bits. Además descarto los
    # caracteres de control y la diagonal, que darían problemas al copiar el
    # archivo de regreso a la computadora
    if not nombre.isascii() or any(not c.isprintable() or c == '/' for c in nombre):
        raise ErrorFiUnamFS(f'El nombre "{nombre}" tiene caracteres no permitidos (solo ASCII, sin "/")')
    # Los espacios de las orillas se pierden porque el nombre se rellena con
    # espacios y al leerlo se recortan
    if nombre != nombre.strip():
        raise ErrorFiUnamFS('El nombre no puede empezar ni terminar con espacios')
    if nombre in NOMBRES_RESERVADOS:
        raise ErrorFiUnamFS('Ese nombre está reservado para las entradas vacías')


class FiUnamFS:
    def __init__(self, ruta):
        # Si la imagen no tiene permiso de escritura se abre solo para lectura,
        # así todavía se puede listar y copiar hacia la computadora
        self.solo_lectura = False
        try:
            self.imagen = open(ruta, 'r+b')
        except PermissionError:
            self.solo_lectura = True
            self.imagen = self._abrir_solo_lectura(ruta)
        except OSError as e:
            raise ErrorFiUnamFS(f'No se pudo abrir "{ruta}": {e.strerror}')
        try:
            self._leer_superbloque()
        except Exception:
            self.imagen.close()
            raise

    @staticmethod
    def _abrir_solo_lectura(ruta):
        try:
            return open(ruta, 'rb')
        except OSError as e:
            raise ErrorFiUnamFS(f'No se pudo abrir "{ruta}": {e.strerror}')

    def _revisar_escritura(self):
        if self.solo_lectura:
            raise ErrorFiUnamFS('La imagen no tiene permiso de escritura, solo se puede listar y copiar hacia la computadora')

    def cerrar(self):
        self.imagen.close()

    def _leer_superbloque(self):
        superbloque = self.imagen.read(64)

        # Antes de cualquier otra cosa se valida que sea un FiUnamFS de la
        # versión correcta, así nunca se escribe sobre un archivo ajeno
        if superbloque[0:8] != NOMBRE_FS:
            raise ErrorFiUnamFS('La imagen no es un sistema de archivos FiUnamFS')
        if superbloque[10:14] != VERSION_FS:
            version = superbloque[10:14].decode('ascii', 'replace')
            raise ErrorFiUnamFS(f'La imagen es de la versión "{version}", este programa solo maneja la 27-1')

        self.etiqueta = superbloque[20:36].decode('ascii', 'replace').strip('\x00 ')
        (self.tam_cluster,
         self.clusters_directorio,
         self.clusters_totales) = struct.unpack_from('<III', superbloque, 40)

        if self.tam_cluster == 0 or self.tam_cluster % TAM_ENTRADA != 0:
            raise ErrorFiUnamFS(f'Tamaño de cluster inválido en el superbloque ({self.tam_cluster})')

        self.primer_cluster_datos = CLUSTER_DIRECTORIO + self.clusters_directorio
        self.total_entradas = self.clusters_directorio * self.tam_cluster // TAM_ENTRADA

    # ---- Directorio ----

    def _posicion_entrada(self, indice):
        return CLUSTER_DIRECTORIO * self.tam_cluster + indice * TAM_ENTRADA

    def _leer_directorio(self):
        """Regresa todas las entradas del directorio, ocupadas o no, en crudo."""
        self.imagen.seek(self._posicion_entrada(0))
        crudo = self.imagen.read(self.total_entradas * TAM_ENTRADA)
        return [crudo[i:i + TAM_ENTRADA] for i in range(0, len(crudo), TAM_ENTRADA)]

    @staticmethod
    def _leer_nombre(campo):
        # En la imagen del profe los nombres vienen rellenos de espacios y
        # terminan con un byte nulo, se quitan los dos para quedarse con el nombre
        return campo.decode('ascii', 'replace').strip('\x00 ')

    def _entrada_libre(self, crudo):
        # Una entrada vacía se marca con '-' en el tipo y con un nombre
        # reservado, cualquiera de las dos señales basta para ignorarla
        return crudo[0:1] != TIPO_ARCHIVO or self._leer_nombre(crudo[1:16]) in NOMBRES_RESERVADOS

    def listar(self):
        """Regresa los archivos del directorio en el orden en que aparecen."""
        entradas = []
        for indice, crudo in enumerate(self._leer_directorio()):
            if self._entrada_libre(crudo):
                continue
            _, nombre, tamano, cluster, creado, modificado = struct.unpack(FORMATO_ENTRADA, crudo)
            entradas.append(Entrada(
                indice=indice,
                nombre=self._leer_nombre(nombre),
                tamano=tamano,
                cluster=cluster,
                creado=creado.decode('ascii', 'replace'),
                modificado=modificado.decode('ascii', 'replace'),
            ))
        return entradas

    def buscar(self, nombre):
        for entrada in self.listar():
            if entrada.nombre == nombre:
                return entrada
        return None

    def _escribir_entrada(self, indice, tipo, nombre, tamano, cluster, creado, modificado):
        # El nombre se rellena igual que en la imagen del profe, con espacios
        # hasta el byte 14 y un nulo al final (si mide 15 no queda lugar para el nulo)
        campo_nombre = nombre.encode('ascii').ljust(LARGO_NOMBRE - 1, b' ')
        datos = struct.pack(FORMATO_ENTRADA, tipo, campo_nombre, tamano,
                            cluster, creado.encode('ascii'), modificado.encode('ascii'))
        self.imagen.seek(self._posicion_entrada(indice))
        self.imagen.write(datos)
        self.imagen.flush()

    # ---- Espacio ----

    def clusters_de(self, tamano):
        return math.ceil(tamano / self.tam_cluster)

    def espacio_libre(self):
        """Bytes libres en el área de datos, sin importar si están contiguos."""
        ocupados = sum(self.clusters_de(e.tamano) for e in self.listar())
        libres = self.clusters_totales - self.primer_cluster_datos - ocupados
        return max(libres, 0) * self.tam_cluster

    def _buscar_hueco(self, clusters_necesarios, entradas):
        """
        Busca un hueco con primer ajuste. Como la asignación es contigua el
        archivo necesita clusters seguidos, así que recorro los archivos
        ordenados por su cluster inicial y regreso el primer espacio entre
        ellos donde quepa.
        """
        ocupados = sorted((e.cluster, e.cluster + self.clusters_de(e.tamano))
                          for e in entradas if e.tamano > 0)
        candidato = self.primer_cluster_datos
        for inicio, fin in ocupados:
            if inicio - candidato >= clusters_necesarios:
                return candidato
            candidato = max(candidato, fin)
        if self.clusters_totales - candidato >= clusters_necesarios:
            return candidato
        return None

    # ---- Operaciones ----

    def exportar(self, nombre, destino, avance=None):
        """Copia un archivo de FiUnamFS a la ruta 'destino' de la computadora."""
        entrada = self.buscar(nombre)
        if entrada is None:
            raise ErrorFiUnamFS(f'No existe "{nombre}" en FiUnamFS')

        self.imagen.seek(entrada.cluster * self.tam_cluster)
        copiado = 0
        with open(destino, 'wb') as salida:
            # Se copia de cluster en cluster para poder reportar el avance
            while copiado < entrada.tamano:
                bloque = self.imagen.read(min(self.tam_cluster, entrada.tamano - copiado))
                if not bloque:
                    raise ErrorFiUnamFS(f'"{nombre}" dice medir más de lo que cabe en la imagen')
                salida.write(bloque)
                copiado += len(bloque)
                if avance:
                    avance(copiado, entrada.tamano)

    def importar(self, origen, nombre, avance=None):
        """Copia el archivo 'origen' de la computadora a FiUnamFS como 'nombre'."""
        self._revisar_escritura()
        validar_nombre(nombre)
        if not os.path.isfile(origen):
            raise ErrorFiUnamFS(f'"{origen}" no es un archivo')

        entradas = self.listar()
        if any(e.nombre == nombre for e in entradas):
            raise ErrorFiUnamFS(f'Ya existe "{nombre}" en FiUnamFS')

        ocupadas = {e.indice for e in entradas}
        indice = next((i for i in range(self.total_entradas) if i not in ocupadas), None)
        if indice is None:
            raise ErrorFiUnamFS('El directorio ya no tiene entradas libres')

        tamano = os.path.getsize(origen)
        necesarios = self.clusters_de(tamano)
        cluster = self._buscar_hueco(necesarios, entradas)
        if cluster is None:
            if self.espacio_libre() >= tamano:
                raise ErrorFiUnamFS('Hay espacio suficiente pero no está contiguo')
            raise ErrorFiUnamFS('No hay espacio suficiente en FiUnamFS')

        # Primero se escriben los datos y al final la entrada del directorio,
        # así si algo falla a la mitad el archivo simplemente no aparece
        self.imagen.seek(cluster * self.tam_cluster)
        copiado = 0
        with open(origen, 'rb') as entrada_pc:
            while copiado < tamano:
                bloque = entrada_pc.read(self.tam_cluster)
                if not bloque:
                    break
                self.imagen.write(bloque)
                copiado += len(bloque)
                if avance:
                    avance(copiado, tamano)

        ahora = datetime.now().strftime(FORMATO_FECHA)
        self._escribir_entrada(indice, TIPO_ARCHIVO, nombre, copiado, cluster, ahora, ahora)

    def eliminar(self, nombre):
        """
        Marca la entrada como vacía. Igual que en otros sistemas de archivos
        los datos no se borran, el espacio solo queda disponible para otro.
        """
        self._revisar_escritura()
        entrada = self.buscar(nombre)
        if entrada is None:
            raise ErrorFiUnamFS(f'No existe "{nombre}" en FiUnamFS')
        self._escribir_entrada(entrada.indice, TIPO_VACIO, NOMBRE_VACIO, 0, 0,
                               FECHA_VACIA, FECHA_VACIA)
