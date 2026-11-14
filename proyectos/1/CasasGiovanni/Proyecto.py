#!/usr/bin/python3

import argparse
import struct
import sys
from datetime import datetime

NOMBRE_FS = b"FiUnamFS"
VERSION_FS = b"27-1"
TAM_ENTRADA = 64
TIPO_ARCHIVO = b"F"     


class ErrorFiUnamFS(Exception):  #Nos da una excepcion , en caso de que no se pueda leer el disco
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


class FiUnamFS: #Se crea clase y sus atributos/ 
    def __init__(self, ruta_disco):
        self.archivo = open(ruta_disco, "rb")
        try:
            self.leer_superbloque()  #llamada al metodo leer y obtiene los atributos self.tam_cluster, self.clusters_dir, self.clusters_total
        except Exception:
            # Si el superbloque es inválido, no se deja el archivo abierto
            self.archivo.close()
            raise

    def __enter__(self):  
        return self

    def __exit__(self, *_):
        self.archivo.close()


    def leer_superbloque(self): #En esta funcion compara para ver si pertence al disco y nos da el volumen
        self.archivo.seek(0) #Recorre todo el disco desde el inicio
        sb = self.archivo.read(64)  #Lo hace en forma de bytes 
        if len(sb) < 64 or sb[0:8] != NOMBRE_FS:  #Comparacion si archivo es muy corto o bytes [0,8] no dicen Fiunam
            raise ErrorFiUnamFS("el/los archivo(s) no pertenece(n) a sistema FiUnamFS")
        if sb[10:14] != VERSION_FS:
            raise ErrorFiUnamFS("Esta version no esta soportada: %r (se requiere %s)"
                                % (sb[10:14], VERSION_FS.decode()))
        self.etiqueta = sb[20:36].rstrip(b"\0 ").decode("ascii", "replace")  #Lee los datos y los guarda como argumentos de objeto Fiunam 
        (self.tam_cluster,
         self.clusters_dir,
         self.clusters_total) = struct.unpack("<III", sb[40:52])




    def num_entradas(self):
        return self.clusters_dir * self.tam_cluster // TAM_ENTRADA

    def leer_directorio(self): #Regresa en forma de lista todas las entradas ocupadas de la ruta
        self.archivo.seek(self.tam_cluster)          # El directorio empieza en el cluster 1
        bytes_directorio = self.archivo.read(self.clusters_dir * self.tam_cluster) #bytes sin interpretar
        ocupadas = [] #Aqui es donde se guardan las entradas que contienen archivos
        for i in range(self.num_entradas()):
            bloque = bytes_directorio[i * TAM_ENTRADA:(i + 1) * TAM_ENTRADA] #Va "cortando " en bloques de 64 
            if bloque[0:1] != TIPO_ARCHIVO:
                continue                             
            nombre = bloque[1:16].rstrip(b"\0 ").decode("ascii", "replace") #Quita los cerod antes y despues ,ademas de esapcios y lo convierte a texto
            tamano, cluster = struct.unpack("<II", bloque[16:24])  #Devuelve los 2 numeros (que se toman de bytes 16-23) y devuelve 2 numeros 
            ocupadas.append(Entrada(i, nombre, tamano, cluster,
                                    bloque[24:38].decode("ascii", "replace"),
                                    bloque[38:52].decode("ascii", "replace")))
        return ocupadas


    def listar(self):  #Regresa la lista y tambien la ordena 
        return sorted(self.leer_directorio(), key=lambda entrada: entrada.nombre)

def crear_parser(): #"Es donde podemos decir que hacer desde cmd , es decir:leer, extraer, etc"
    p = argparse.ArgumentParser(description="Manejo de un disco FiUnamFS 27-1") #Se crea p , que sirve para leer el disco
    p.add_argument("disco", help="ruta de la imagen del disco (p. ej. fiunamfs.img)")
    sub = p.add_subparsers(dest="comando", required=True)

    sub.add_parser("listar", help="lista el contenido del directorio")
    return p


def main():
    args = crear_parser().parse_args() # se llama a funcion Recibe que seleccion se quiere hacer y lo guarda
    try:
        with FiUnamFS(args.disco) as fs: #Compara que si sea disco FiUnam
            if args.comando == "listar": #Una vez seleccionado listar muestra lo siguiente 
                print("Volumen: %s" % fs.etiqueta)
                print("%-15s %10s %8s  %-19s %-19s" %
                      ("Nombre", "Tamaño", "Cluster", "Creación", "Modificación"))
                print("=" * 76)
                for entrada in fs.listar():
                    print("%-15s %10d %8d  %-19s %-19s" %
                          (entrada.nombre, entrada.tamano, entrada.cluster,
                           formato_fecha(entrada.creacion), formato_fecha(entrada.modificacion)))
    except (ErrorFiUnamFS, OSError) as error:  #Si no es valido o asi , salta el mensaje de error
        print("Error: %s" % error, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()