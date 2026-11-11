LISTA DE ARCHIVOS

Descripción
Programa en Python que lista los archivos de un directorio cuya última modificación haya ocurrido hace N días o menos. Usa solo la biblioteca estándar y no llama a ningún programa externo.

Uso
python3 lista_archivos.py <directorio> <dias>

Parámetros
directorio  Ruta del directorio a procesar.
dias        Número entero mayor o igual a 0.

Ejemplo
python3 lista_archivos.py /home/usuario/documentos 7

Salida
Una línea por archivo, ordenada lexicográficamente por nombre, con campos separados por tabuladores:
nombre, longitud en bytes, fecha de última modificación (AAAA-MM-DD HH:MM:SS) y modo (permisos al estilo de ls -l, por ejemplo -rw-r--r--).


Funciones de la biblioteca estándar utilizadas
os.scandir(ruta)    Abre el directorio e itera sus entradas. Usada en lista_archivos.py.
os.listdir(ruta)    Devuelve los nombres de las entradas del directorio. Usada en lista_archivos_listdir.py.
os.lstat(ruta)      Obtiene tamaño, fecha de modificación y modo de un archivo sin seguir ligas simbólicas. Usada en lista_archivos_listdir.py; en la otra versión se obtiene con entrada.stat().
stat.S_ISREG(modo)  Indica si la entrada es un archivo regular.
time.strftime  Da formato legible a la fecha de modificación.