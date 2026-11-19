#!/usr/bin/python3

import argparse
import os
import struct
import sys
import threading   
from datetime import datetime

NOMBRE_FS = b"FiUnamFS"
VERSION_FS = b"27-1"
TAM_ENTRADA = 64
TIPO_ARCHIVO = b"F"     
TAM_BLOQUE = 2048   #Bytes que se copian en cada paso al extraer y al agregar
TAM_COLA = 8        
LIBRE = b"#"        #marca que se pone al inicio de una entrada libre 
MAX_NOMBRE = 14   #Maximo de letras que puede tener el nombre de un archivo en el FiUnamFS


class ErrorFiUnamFS(Exception):  #Lanza una excepcion , en caso de que no se pueda leer el disco
    """"""

#creamos clase estrada 
class Entrada:     #Creamos el molde  de la clase
    def __init__(self, indice, nombre, tamano, cluster, creacion, modificacion): #Usamnos el contructor y definimos atributos
        self.indice = indice
        self.nombre = nombre
        self.tamano = tamano
        self.cluster = cluster
        self.creacion = creacion
        self.modificacion = modificacion


def formato_fecha(texto):  #Damos formato a fecha 
    try:
        return datetime.strptime(texto, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return texto


def obtener_nombre(entrada):  #Regresa el nombre de una entrada, sirve para ordenar la lista
    return entrada.nombre


def clusters_necesarios(tamano, tam_cluster):  #Cuantos clusters ocupa un archivo (se redondea hacia arriba)
    resultado = (tamano + tam_cluster - 1) // tam_cluster
    if resultado < 1:  #Un archivo ocupa al menos un cluster, aunque este vacio
        resultado = 1
    return resultado


def ahora():  #Fecha y hora actual en el formato del disco: AAAAMMDDHHMMSS
    return datetime.now().strftime("%Y%m%d%H%M%S").encode("ascii")


def validar_nombre(nombre):  #Revisa que el nombre sea valido para el FiUnamFS
    if len(nombre) == 0 or len(nombre) > MAX_NOMBRE:
        raise ErrorFiUnamFS("el nombre debe tener de 1 a %d caracteres" % MAX_NOMBRE)
    if nombre.startswith("#"):  #Los nombres que empiezan con # se usan para marcar entradas libres
        raise ErrorFiUnamFS("el nombre no puede empezar con '#'")
    for letra in nombre:  #Solo se permiten caracteres ASCII que se puedan imprimir
        if ord(letra) < 32 or ord(letra) > 126:
            raise ErrorFiUnamFS("el nombre solo puede usar caracteres ASCII imprimibles")


def armar_entrada(nombre, tamano, cluster, fecha):  #Arma los 64 bytes de una entrada nueva del directorio
    datos = TIPO_ARCHIVO                                           #byte 0: tipo F
    datos = datos + nombre.encode("ascii").ljust(MAX_NOMBRE, b" ") #bytes 1-14: nombre
    datos = datos + b"\0"                                          #byte 15: queda en cero
    datos = datos + struct.pack("<II", tamano, cluster)            #bytes 16-23: tamano y cluster
    datos = datos + fecha + fecha                                  #bytes 24-51: creacion y modificacion
    datos = datos + b"\0" * 12                                     #bytes 52-63: sin usar
    return datos




class Canal:  #Esta clase junta todo lo que comparten los dos hilos, lista en donde estaran los pedazos , protege la lista 
    def __init__(self):
        self.buffer = []  
        self.espacios = threading.Semaphore(TAM_COLA)  
        self.elementos = threading.Semaphore(0)  
        self.mutex = threading.Semaphore(1)  
        self.cancelar = threading.Event()  
        self.errores = []  


def anadir_elemento(canal, elemento):  #El hilo lector deja un elemento en el buffer, pide un lugar libre , si no hay eerores entra , agrega elemento sale y notifica
    while True:
        if canal.espacios.acquire(timeout=0.1):  
            break
        if canal.cancelar.is_set():  
            return False
    canal.mutex.acquire()  
    canal.buffer.append(elemento)
    canal.mutex.release()  
    canal.elementos.release()  
    return True


def sacar_elemento(canal):  #El hilo escritor toma un elemento del buffer, pide el pedazo listo, entra , toma el pedazo mas viejo , sale y avisa al hilo lecyqor que hay un lugar libre
    while True:
        if canal.elementos.acquire(timeout=0.1):  
            break
        if canal.cancelar.is_set():  
            return False, None
    canal.mutex.acquire()  
    elemento = canal.buffer.pop(0)  
    canal.mutex.release()  
    canal.espacios.release()  
    return True, elemento


def leer(fuente, total, canal, mensaje_error):  #Es lo que hace el hilo lector, primer ve cuantos bytes faltan por leer , copia tam de bloque, ve si hay mas datos por leer , manda pedazo al hilo escritor y notifica que no hay nada mas por leer
    restante = total  
    try:
        while restante > 0 and not canal.cancelar.is_set():
            cantidad = min(TAM_BLOQUE, restante) 
            datos = fuente.read(cantidad)
            if not datos: 
                raise ErrorFiUnamFS(mensaje_error)
            anadir_elemento(canal, datos)  
            restante = restante - len(datos)
    except Exception as error:  #Si algo falla, se guarda el error y se avisa al otro hilo
        canal.errores.append(error)
        canal.cancelar.set()
    finally:
        if not canal.cancelar.is_set():  
            anadir_elemento(canal, None)


def escribir(destino, canal):  #Es lo que hace el hilo escritor , mientras haya datos este los obtiene . Despues si hay fallo termina , si no espera norificacion de hilo lector para decir que no hay nada mas y los escribe 
    try:
        while True:
            hay, datos = sacar_elemento(canal)
            if not hay: 
                break
            if datos is None:  #None significa que el hilo lector ya termino
                break
            destino.write(datos)
    except Exception as error:  
        canal.errores.append(error)
        canal.cancelar.set()


def copiar_datos(fuente, destino, total, mensaje_error):  #Copia el total bytes de fuente a destino usando 2 hilos
    canal = Canal()  #Lo que comparten los dos hilos

    hilo_lector = threading.Thread(target=leer, args=(fuente, total, canal, mensaje_error))
    hilo_escritor = threading.Thread(target=escribir, args=(destino, canal))
    hilo_lector.start()  
    hilo_escritor.start()
    hilo_lector.join()    
    hilo_escritor.join()

    if len(canal.errores) > 0:  #Si algun hilo fallo, el error se vuelve a lanzar aqui
        raise canal.errores[0]


class FiUnamFS: #Se crea clase y sus atributos/ 
    def __init__(self, ruta_disco, escritura):
        if escritura:  #Solo se abre para escribir si la operacion va a modificar el disco
            modo = "r+b"
        else:
            modo = "rb"
        self.archivo = open(ruta_disco, modo)
        try:
            self.leer_superbloque()  #llamada al metodo leer y obtiene los atributos self.tam_cluster, self.clusters_dir, self.clusters_total
        except Exception:
            # Si el superbloque no es valido, se cieera el archivo
            self.archivo.close()
            raise

    def cerrar(self):  #Cierra el archivo del disco
        self.archivo.close()


    def leer_superbloque(self): #En esta funcion compara para ver si pertence al disco y nos da el volumen, recorriendo solo los primeros 64 bytes
        self.archivo.seek(0) 
        sb = self.archivo.read(64)  
        if len(sb) < 64 or sb[0:8] != NOMBRE_FS:  #Comparacion si archivo es muy corto o bytes [0,8] no dicen Fiunam
            raise ErrorFiUnamFS("el/los archivo(s) no pertenece(n) a sistema FiUnamFS")
        if sb[10:14] != VERSION_FS:
            raise ErrorFiUnamFS("Esta version no esta soportada: %r (se requiere %s)"
                                % (sb[10:14], VERSION_FS.decode()))
        self.etiqueta = sb[20:36].rstrip(b"\0 ").decode("ascii", "replace")  #Aqui es donde traduce los bytes 20 a 35 (nombre del volumen), quita ceros y espacios del final y los convierte a texto.
        numeros = struct.unpack("<III", sb[40:52])  #Convierte los bytes 40 a 51 en 3 enteros de 4 bytes
        self.tam_cluster = numeros[0]
        self.clusters_dir = numeros[1]
        self.clusters_total = numeros[2]


    def num_entradas(self):
        return self.clusters_dir * self.tam_cluster // TAM_ENTRADA   #Calcula cuántas entradas caben en el directorio

    def leer_directorio(self): #Regresa en forma de lista todas las entradas ocupadas de la ruta
        self.archivo.seek(self.tam_cluster)          # El directorio empieza en el cluster 1
        bytes_directorio = self.archivo.read(self.clusters_dir * self.tam_cluster) 
        ocupadas = [] #Aqui es donde se guardan las entradas que contienen archivos
        for i in range(self.num_entradas()):
            bloque = bytes_directorio[i * TAM_ENTRADA:(i + 1) * TAM_ENTRADA] #Va "cortando " en bloques de 64 
            if bloque[0:1] == TIPO_ARCHIVO:  #Aqui es donde comparamos si es empieza con F
                nombre = bloque[1:16].rstrip(b"\0 ").decode("ascii", "replace") #Quita los cerod antes y despues ,ademas de esapcios y lo convierte a texto
                numeros = struct.unpack("<II", bloque[16:24])  #Los 2 numeros (bytes 16-23)
                tamano = numeros[0]
                cluster = numeros[1]
                creacion = bloque[24:38].decode("ascii", "replace")
                modificacion = bloque[38:52].decode("ascii", "replace")
                ocupadas.append(Entrada(i, nombre, tamano, cluster, creacion, modificacion))
        return ocupadas


    def listar(self):  #Regresa la lista y tambien la ordena 
        return sorted(self.leer_directorio(), key=obtener_nombre)

    def buscar(self, nombre): #Busca un archivo por nombre en el directorio
        for entrada in self.leer_directorio():
            if entrada.nombre == nombre:
                return entrada
        raise ErrorFiUnamFS("no existe el archivo '%s' en el directorio FiUnamFS" % nombre)

    def extraer(self, nombre, destino): #Copia un archivo del disco a la computadora
        entrada = self.buscar(nombre)
        self.archivo.seek(entrada.cluster * self.tam_cluster) #Va al cluster donde empieza el archivo
        salida = open(destino, "wb")
        try:
            # el hilo lector lee del disco y el hilo escritor escribe en la computadora
            copiar_datos(self.archivo, salida, entrada.tamano, "El archivo '%s' no esta completo  en el disco" % nombre)
        finally:
            salida.close()  #Se cierra el archivo de salida aunque haya error
        return entrada.tamano

    def buscar_entrada_libre(self): #Regresa la posicion de la primera entrada libre del directorio
        self.archivo.seek(self.tam_cluster)
        bytes_directorio = self.archivo.read(self.clusters_dir * self.tam_cluster)
        for i in range(self.num_entradas()):
            bloque = bytes_directorio[i * TAM_ENTRADA:(i + 1) * TAM_ENTRADA]
            if bloque[0:1] != TIPO_ARCHIVO:  #Si no empieza con F, esta libre
                return i
        raise ErrorFiUnamFS("Ya no queda mas espacio. El directorio esta lleno")

    def buscar_hueco(self, necesarios): #Busca dónde guardar los datos: un tramo de clusters libres y seguidos (contiguos) que alcance para el archivo.
        usados = []  #Lista donde se guardarán los tramos ocupados como pares
        for entrada in self.leer_directorio():
            inicio = entrada.cluster
            fin = entrada.cluster + clusters_necesarios(entrada.tamano, self.tam_cluster)
            usados.append((inicio, fin))
        usados.sort()  #Se ordenan de menor a mayor 
        cursor = 1 + self.clusters_dir  #Es donde se podrian guardar 
        for par in usados:
            inicio = par[0]
            fin = par[1]
            if inicio - cursor >= necesarios:  #Si entre el cursor y el siguiente archivo cabe se usa 
                return cursor
            if fin > cursor:
                cursor = fin
        if self.clusters_total - cursor >= necesarios:  #Si no, se revisa el espacio que queda al final del disco
            return cursor
        raise ErrorFiUnamFS("No hay espacio contiguo suficiente (%d clusters)" % necesarios)

    def escribir_entrada(self, indice, datos): #Escribe los 64 bytes de una entrada en el directorio
        self.archivo.seek(self.tam_cluster + indice * TAM_ENTRADA)
        self.archivo.write(datos)
        self.archivo.flush()

    def agregar(self, origen, nombre): #Copia un archivo de la computadora al disco
        if not os.path.isfile(origen):
            raise ErrorFiUnamFS("No existe el archivo '%s'" % origen)
        if nombre is None:  #Si no se escribio -n, se usa el mismo nombre del archivo
            nombre = os.path.basename(origen)
        validar_nombre(nombre)
        tamano = os.path.getsize(origen)

        for entrada in self.leer_directorio():  #No puede haber dos archivos con el mismo nombre
            if entrada.nombre == nombre:
                raise ErrorFiUnamFS("El archivo ya  existe '%s' en el Directorio FiUnamFS" % nombre)
        indice = self.buscar_entrada_libre() #Aqui se "reserva espacio"
        cluster = self.buscar_hueco(clusters_necesarios(tamano, self.tam_cluster))

        # Primero se copian los datos y hasta el final se escribe la entrada del directorio:
        # si algo falla a la mitad, el directorio no apunta a datos incompletos.
        origen_archivo = open(origen, "rb")
        try:
            self.archivo.seek(cluster * self.tam_cluster) #Va al cluster donde se va a guardar el hilo lector lee del archivo de la computadora y el hilo escritor escribe en el disco
            copiar_datos(origen_archivo, self.archivo, tamano, "El archivo '%s' no esta completo" % origen)
        finally:
            origen_archivo.close()  #Se cierra el archivo de origen aunque haya error
        self.archivo.flush()

        fecha = ahora()
        self.escribir_entrada(indice, armar_entrada(nombre, tamano, cluster, fecha))
        return tamano

    def eliminar(self, nombre): # elimina un archivo,libera su entrada del directorio, si no existe lanza error
        entrada = self.buscar(nombre)  
        libre = LIBRE + b"\0" * (TAM_ENTRADA - 1) 
        self.escribir_entrada(entrada.indice, libre)
        return entrada.tamano

def crear_parser(): #"Es donde podemos decir que hacer desde cmd , es decir:leer, extraer, etc"
    p = argparse.ArgumentParser(description="Manejo de un disco FiUnamFS 27-1") #Se crea p , que sirve para leer el disco
    p.add_argument("disco", help="ruta de la imagen del disco")
    sub = p.add_subparsers(dest="comando", required=True)

    sub.add_parser("listar", help="lista el contenido del directorio")

    s = sub.add_parser("extraer", help="copia un archivo del disco a su computadora")
    s.add_argument("nombre", help="nombre del archivo dentro del FiUnamFS")
    s.add_argument("-o", "--destino", help="ruta de salida (Si no se escribe nada queda tal cual")

    s = sub.add_parser("agregar", help="copia un archivo de su computadora al disco")
    s.add_argument("origen", help="archivo de su computadora que se va a copiar")
    s.add_argument("-n", "--nombre", help="nombre dentro del FiUnamFS (maximo 14 caracteres)")

    s = sub.add_parser("eliminar", help="elimina un archivo del disco")
    s.add_argument("nombre", help="nombre del archivo dentro del FiUnamFS")
    return p


def main():
    print(" ********************************************************************************************")
    print("Forma de uso:")  #Si faltan el disco o el comando, se explica como usarlo
    print(" python fiunamfs.py <nombre del disco> listar")
    print(" python fiunamfs.py <nombre del disco> extraer <nombre del archivo con su extension>")
    print(" python fiunamfs.py <nombre del disco> agregar <nombre de archivo con su extension> ")
    print(" python fiunamfs.py <nombre del disco> eliminar <nombre del archivo con su extension>")
    print(" ********************************************************************************************")
    args = crear_parser().parse_args() # se llama a funcion Recibe que seleccion se quiere hacer y lo guarda
    fs = None  #Todavia no hay disco abierto   *fs es nuestro objeto de clase FiUnamFs
    try:
        escritura = False  #Por omision el disco se abre solo para leer
        if args.comando == "agregar" or args.comando == "eliminar":  #Agregar y eliminar son las operaciones que modifican el disco
            escritura = True
        fs = FiUnamFS(args.disco, escritura) #Compara que si sea disco FiUnam
        if args.comando == "listar": #Una vez seleccionado listar muestra lo siguiente 
            print("Volumen: %s" % fs.etiqueta)
            print("%-15s %10s %8s  %-19s %-19s" %
                  ("Nombre", "Tamaño", "Cluster", "Creación", "Modificación"))
            print("=" * 76)
            for entrada in fs.listar():
                print("%-15s %10d %8d  %-19s %-19s" %
                      (entrada.nombre, entrada.tamano, entrada.cluster,
                       formato_fecha(entrada.creacion), formato_fecha(entrada.modificacion)))
        elif args.comando == "extraer": #Hara una copia del disco a la computadora
            if args.destino:  #Si no lo especifica se queda con el mismo nomre
                destino = args.destino
            else:  #Si no, se guarda con el mismo nombre
                destino = args.nombre
            total = fs.extraer(args.nombre, destino)
            print("Fueron Copiados %d bytes de '%s' a '%s'" % (total, args.nombre, destino))
        elif args.comando == "agregar": #Se elige agregar: copia de la computadora al disco
            total = fs.agregar(args.origen, args.nombre)
            print("Se copiaron %d bytes de '%s' al diredctorio FiUnamFS" % (total, args.origen))
        elif args.comando == "eliminar": #se elige eliminar: libera la entrada del archivo
            total = fs.eliminar(args.nombre)
            print("Se elimino '%s' del directorio FiUnamFS (%d bytes liberados)" % (args.nombre, total))
    except (ErrorFiUnamFS, OSError) as error:  #Si no es valido , salta el mensaje de error
        print("Error: %s" % error, file=sys.stderr)
        sys.exit(1)
    finally:
        if fs is not None:  #Si el disco se llego a abrir, se cierra
            fs.cerrar()


if __name__ == "__main__":
    main()