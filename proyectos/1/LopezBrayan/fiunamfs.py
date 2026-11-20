"""
Proyecto 1: (Micro) sistema de archivos multihilos
Sistemas Operativos - Facultad de Ingenieria, UNAM

Autor: Brayan López Ramírez    
"""

import os
import struct
import sys
import threading
from datetime import datetime

BYTES_DISCO = 1440 * 1024          
BYTES_SECTOR = 512
BYTES_CLUSTER = BYTES_SECTOR * 4     
BYTES_REGISTRO = 64                 
MAX_CHARS_NOMBRE = 15                  

FIRMA_FS = b"FiUnamFS"          
VER_FS = b"27-1"            

MARCA_ARCHIVO = b"F"             
MARCA_VACIO = b"-"                
NOMBRE_LIBRE = b"#" + b"." * 14  

class ErrorSistema(Exception):
    pass

class SistemaArchivos:
    def __init__(self, archivo_imagen):
        self.archivo_imagen = archivo_imagen
        try:
            self.archivo = open(archivo_imagen, "r+b")
        except OSError as err:
            raise ErrorSistema("No pude abrir el disco '%s': %s" % (archivo_imagen, err))
        self.cargar_superbloque()

    def salir_disco(self):
        self.archivo.close()

    def cargar_superbloque(self):
        self.archivo.seek(0)
        bloque = self.archivo.read(BYTES_CLUSTER)
        if len(bloque) < 52:
            raise ErrorSistema("El archivo es demasiado pequeño para ser un FiUnamFS.")

        if bloque[0:8] != FIRMA_FS:
            raise ErrorSistema("Este archivo no es un FiUnamFS (nombre incorrecto).")
        if bloque[10:14] != VER_FS:
            raise ErrorSistema("Version incorrecta: se esperaba '27-1' y se encontro '%s'"
                          % bloque[10:14].decode("ascii", errors="replace"))

        self.ver = bloque[10:14].decode("ascii")
        self.nombre_vol = bloque[20:36].decode("ascii", errors="replace").rstrip(" \x00")

        (self.bytes_por_cluster,
         self.num_clusters_dir,
         self.clusters_totales) = struct.unpack("<III", bloque[40:52])

        if self.bytes_por_cluster != BYTES_CLUSTER:
            raise ErrorSistema("Tamaño de cluster inesperado: %d" % self.bytes_por_cluster)
        if self.num_clusters_dir == 0 or self.clusters_totales == 0:
            raise ErrorSistema("El superbloque tiene datos invalidos.")

        peso_real = os.path.getsize(self.archivo_imagen)
        if peso_real < self.clusters_totales * self.bytes_por_cluster:
            raise ErrorSistema("El archivo mide menos de lo que dice el superbloque")

        self.limite_registros = (self.num_clusters_dir * self.bytes_por_cluster) // BYTES_REGISTRO
        self.cluster_inicio_datos = 1 + self.num_clusters_dir

    # DIRECTORIO 
    def obtener_directorio(self):
        self.archivo.seek(self.bytes_por_cluster)
        buffer_dir = self.archivo.read(self.num_clusters_dir * self.bytes_por_cluster)

        lista_registros = []
        for idx in range(self.limite_registros):
            trozo = buffer_dir[idx * BYTES_REGISTRO:(idx + 1) * BYTES_REGISTRO]
            tipo_reg = trozo[0:1]
            nombre_bytes = trozo[1:16]
            libre = (tipo_reg != MARCA_ARCHIVO) or (nombre_bytes == NOMBRE_LIBRE)

            reg = {"pos": idx, "libre": libre}
            if not libre:
                reg["nombre"] = nombre_bytes.decode("ascii", errors="replace").rstrip(" \x00")
                reg["peso"], reg["cluster_ini"] = struct.unpack("<II", trozo[16:24])
                reg["fecha_crea"] = trozo[24:38].decode("ascii", errors="replace")
                reg["fecha_mod"] = trozo[38:52].decode("ascii", errors="replace")
            lista_registros.append(reg)
        return lista_registros

    def guardar_registro(self, pos, nombre, peso, cluster_ini, fecha_crea, fecha_mod):
        nombre_txt = nombre.encode("ascii").ljust(MAX_CHARS_NOMBRE, b" ")
        trozo = (MARCA_ARCHIVO + nombre_txt
                 + struct.pack("<II", peso, cluster_ini)
                 + fecha_crea.encode("ascii") + fecha_mod.encode("ascii")
                 + bytes(12))                      
        self.archivo.seek(self.bytes_por_cluster + pos * BYTES_REGISTRO)
        self.archivo.write(trozo)
        self.archivo.flush()

    def borrar_registro(self, pos):
        trozo = MARCA_VACIO + NOMBRE_LIBRE + bytes(48)
        self.archivo.seek(self.bytes_por_cluster + pos * BYTES_REGISTRO)
        self.archivo.write(trozo)
        self.archivo.flush()

    def encontrar_archivo(self, nombre):
        for reg in self.obtener_directorio():
            if not reg["libre"] and reg["nombre"] == nombre:
                return reg
        return None

    # ASIGNACION CONTIGUA
    def calcular_clusters(self, peso):
        return (peso + self.bytes_por_cluster - 1) // self.bytes_por_cluster

    def hallar_hueco(self, cant_clusters):
        usados = []
        for reg in self.obtener_directorio():
            if not reg["libre"] and reg["peso"] > 0:
                usados.append((reg["cluster_ini"], reg["cluster_ini"] + self.calcular_clusters(reg["peso"])))
        usados.sort()

        actual = self.cluster_inicio_datos
        for ini, fin in usados:
            if ini - actual >= cant_clusters:
                return actual          
            actual = max(actual, fin)
        if self.clusters_totales - actual >= cant_clusters:
            return actual              
        return None

    # OPERACIONES PROYECTOS
    def ver_lista(self):
        lista = [reg for reg in self.obtener_directorio() if not reg["libre"]]
        if not lista:
            return "El disco no tiene archivos."

        filas = []
        filas.append("%-15s %13s %8s  %-19s  %-19s" %
                      ("Nombre", "Tamano(bytes)", "Cluster", "Creacion", "Modificacion"))
        filas.append("-" * 82)
        for reg in lista:
            filas.append("%-15s %13d %8d  %-19s  %-19s" %
                          (reg["nombre"], reg["peso"], reg["cluster_ini"],
                           formatear_fecha(reg["fecha_crea"]),
                           formatear_fecha(reg["fecha_mod"])))
        filas.append("Total: %d archivo(s)" % len(lista))
        return "
".join(filas)

    def ver_info(self):
        lista_registros = self.obtener_directorio()
        clusters_ocupados = 0
        total_archivos = 0
        for reg in lista_registros:
            if not reg["libre"]:
                total_archivos += 1
                clusters_ocupados += self.calcular_clusters(reg["peso"])
        clusters_disponibles = self.clusters_totales - self.cluster_inicio_datos - clusters_ocupados
        return ("Volumen: %s\n"
                "Version: %s\n"
                "Tamano de cluster: %d bytes\n"
                "Clusters del directorio: %d (maximo %d archivos)\n"
                "Clusters totales: %d\n"
                "Archivos: %d\n"
                "Clusters de datos libres (en total, no necesariamente juntos): %d"
                % (self.nombre_vol, self.ver, self.bytes_por_cluster,
                   self.num_clusters_dir, self.limite_registros,
                   self.clusters_totales, total_archivos, clusters_disponibles))

    def sacar_archivo(self, nombre, ruta_salida):
        reg = self.encontrar_archivo(nombre)
        if reg is None:
            raise ErrorSistema("No existe el archivo '%s' en el FiUnamFS" % nombre)

        if ruta_salida == "":
            ruta_salida = nombre
        elif os.path.isdir(ruta_salida):
            ruta_salida = os.path.join(ruta_salida, nombre)

        self.archivo.seek(reg["cluster_ini"] * self.bytes_por_cluster)
        contenido = self.archivo.read(reg["peso"])
        if len(contenido) < reg["peso"]:
            raise ErrorSistema("El archivo esta truncado dentro del disco (¿disco corrupto?).")

        with open(ruta_salida, "wb") as archivo_out:
            archivo_out.write(contenido)
        return "Listo: '%s' (%d bytes) copiado a '%s'" % (nombre, len(contenido), ruta_salida)

    def meter_archivo(self, archivo_local):
        if not os.path.isfile(archivo_local):
            raise ErrorSistema("No existe el archivo '%s' en tu computadora" % archivo_local)

        nombre = os.path.basename(archivo_local)
        self.revisar_nombre(nombre)
        if self.encontrar_archivo(nombre) is not None:
            raise ErrorSistema("Ya existe un archivo llamado '%s' en el FiUnamFS" % nombre)

        with open(archivo_local, "rb") as f_in:
            contenido = f_in.read()
        peso = len(contenido)

        # BUSCAR UNA ENTRADA LIBRE EN EL DIRECTORIO
        pos_libre = None
        for reg in self.obtener_directorio():
            if reg["libre"]:
                pos_libre = reg["pos"]
                break
        if pos_libre is None:
            raise ErrorSistema("El directorio esta lleno.")

        # BUSCAR ESPACIO CONTIGUO 
        requeridos = max(1, self.calcular_clusters(peso))
        cluster_ini = self.hallar_hueco(requeridos)
        if cluster_ini is None:
            raise ErrorSistema("No hay %d clusters contiguos libres (fragmentacion externa o disco lleno)"
                          % requeridos)

        # ESCRIBIR PRIMERO LOS DATOS 
        sobrante = requeridos * self.bytes_por_cluster - peso
        self.archivo.seek(cluster_ini * self.bytes_por_cluster)
        self.archivo.write(contenido + bytes(sobrante))

        # HASTA EL FINAL LA ENTRADA DEL DIRECTORIO
        tiempo_actual = datetime.now().strftime("%Y%m%d%H%M%S")
        self.guardar_registro(pos_libre, nombre, peso, cluster_ini, tiempo_actual, tiempo_actual)
        return "Listo: '%s' (%d bytes) guardado desde el cluster %d" % (nombre, peso, cluster_ini)

    def quitar_archivo(self, nombre):
        reg = self.encontrar_archivo(nombre)
        if reg is None:
            raise ErrorSistema("No existe el archivo '%s' en el FiUnamFS" % nombre)
      
        self.borrar_registro(reg["pos"])
        return "Listo: '%s' eliminado" % nombre

    def revisar_nombre(self, nombre):
        if len(nombre) == 0 or len(nombre) > MAX_CHARS_NOMBRE:
            raise ErrorSistema("El nombre debe medir de 1 a %d caracteres (el tuyo mide %d)"
                          % (MAX_CHARS_NOMBRE, len(nombre)))
        for letra in nombre:
            if ord(letra) > 127:
                raise ErrorSistema("El nombre solo puede tener caracteres ASCII de 7 bits")


def formatear_fecha(texto_fecha):
    if len(texto_fecha) == 14 and texto_fecha.isdigit():
        return "%s-%s-%s %s:%s:%s" % (texto_fecha[0:4], texto_fecha[4:6], texto_fecha[6:8],
                                      texto_fecha[8:10], texto_fecha[10:12], texto_fecha[12:14])
    return texto_fecha

# SINCRONIZACIÓN ENTRE HILOS
class Tarea:
    def __init__(self, accion, params=()):
        self.accion = accion
        self.params = params
        self.respuesta = ""
        self.fallo = False
        self.terminado = threading.Event()

class ColaSegura:
    def __init__(self, limite):
        self.items = []
        self.candado = threading.Lock()                
        self.lugares_vacios = threading.Semaphore(limite)  
        self.lugares_llenos = threading.Semaphore(0)         

    def meter(self, item):
        self.lugares_vacios.acquire()       
        with self.candado:
            self.items.append(item)
        self.lugares_llenos.release()     

    def sacar(self):
        self.lugares_llenos.acquire()      
        with self.candado:
            item = self.items.pop(0)
        self.lugares_vacios.release()      
        return item

# HILOS
def procesar_tarea(sistema, tarea):
    acc = tarea.accion
    pars = tarea.params
    if acc == "listar":
        return sistema.ver_lista()
    elif acc == "info":
        return sistema.ver_info()
    elif acc == "extraer":
        return sistema.sacar_archivo(pars[0], pars[1])
    elif acc == "agregar":
        return sistema.meter_archivo(pars[0])
    elif acc == "eliminar":
        return sistema.quitar_archivo(pars[0])
    else:
        raise ErrorSistema("Operacion desconocida: " + acc)

def worker_principal(sistema, cola_tareas, cola_logs):
    while True:
        item_tarea = cola_tareas.sacar()

        if item_tarea.accion == "salir":
            item_tarea.respuesta = "Cerrando el programa..."
            item_tarea.terminado.set()
            break

        try:
            item_tarea.respuesta = procesar_tarea(sistema, item_tarea)
        except ErrorSistema as err:
            item_tarea.respuesta = "Error: %s" % err
            item_tarea.fallo = True
        except OSError as err:
            item_tarea.respuesta = "Error del sistema: %s" % err
            item_tarea.fallo = True
        except Exception as err:   
            item_tarea.respuesta = "Error inesperado: %r" % err
            item_tarea.fallo = True

        estatus = "ERROR" if item_tarea.fallo else "OK"
        cola_logs.meter("%s %s -> %s" % (item_tarea.accion, list(item_tarea.params), estatus))
        item_tarea.terminado.set()         

    cola_logs.meter(None)    

def worker_log(cola_logs, archivo_log):
    with open(archivo_log, "a", encoding="utf-8") as bitacora:
        while True:
            aviso = cola_logs.sacar()
            if aviso is None:   
                break
            hora_log = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            bitacora.write("[%s] %s\n" % (hora_log, aviso))
            bitacora.flush()

# INTERFAZ DE USUSARIO
OPCIONES_MENU = """
======== FiUnamFS ========
1) Listar el contenido del disco
2) Copiar un archivo del FiUnamFS a mi computadora
3) Copiar un archivo de mi computadora al FiUnamFS
4) Eliminar un archivo del FiUnamFS
5) Informacion del disco
0) Salir
"""

def quitar_comillas(cadena):
    return cadena.strip().strip('"').strip("'")

def mandar_tarea(cola_tareas, accion, params=()):
    item_tarea = Tarea(accion, params)
    cola_tareas.meter(item_tarea)
    item_tarea.terminado.wait()
    print(item_tarea.respuesta)
    return item_tarea

def menu_usuario(cola_tareas):
    while True:
        print(OPCIONES_MENU)
        try:
            eleccion = input("Elige una opcion: ").strip()
        except EOFError:
            eleccion = "0"

        if eleccion == "1":
            mandar_tarea(cola_tareas, "listar")

        elif eleccion == "2":
            item_tarea = mandar_tarea(cola_tareas, "listar")   
            if item_tarea.fallo:
                continue
            nombre = quitar_comillas(input("Nombre del archivo a copiar: "))
            ruta_salida = quitar_comillas(input("Carpeta o ruta destino (Enter = carpeta actual): "))
            mandar_tarea(cola_tareas, "extraer", (nombre, ruta_salida))

        elif eleccion == "3":
            archivo_local = quitar_comillas(input("Ruta del archivo de tu computadora: "))
            mandar_tarea(cola_tareas, "agregar", (archivo_local,))

        elif eleccion == "4":
            item_tarea = mandar_tarea(cola_tareas, "listar")
            if item_tarea.fallo:
                continue
            nombre = quitar_comillas(input("Nombre del archivo a eliminar: "))
            seguro = input("¿Seguro que quieres eliminar '%s'? (s/n): " % nombre)
            if seguro.strip().lower() == "s":
                mandar_tarea(cola_tareas, "eliminar", (nombre,))
            else:
                print("Cancelado.")

        elif eleccion == "5":
            mandar_tarea(cola_tareas, "info")

        elif eleccion == "0":
            mandar_tarea(cola_tareas, "salir")
            break

        else:
            print("Opcion no valida, intenta de nuevo.")

# MAIN
def main():
    ruta_disco = sys.argv[1] if len(sys.argv) > 1 else "fiunamfs.img"

    try:
        fs = SistemaArchivos(ruta_disco)
    except ErrorSistema as e:
        print("Error: %s" % e)
        sys.exit(1)

    print("Disco '%s' abierto correctamente (volumen: %s)" % (ruta_disco, fs.nombre_vol))

    cola_solicitudes = ColaSegura(5)
    cola_bitacora = ColaSegura(10)

    t_trabajador = threading.Thread(target=worker_principal,
                                    args=(fs, cola_solicitudes, cola_bitacora))
    t_bitacora = threading.Thread(target=worker_log,
                                  args=(cola_bitacora, "fiunamfs.log"))
    t_trabajador.start()
    t_bitacora.start()

    menu_usuario(cola_solicitudes)      

    t_trabajador.join()
    t_bitacora.join()
    fs.salir_disco()
    print("Hasta luego.")
   
main()
 
# Implementacion de asignacion contigua y sincronizacion en FIUNAMFS 
