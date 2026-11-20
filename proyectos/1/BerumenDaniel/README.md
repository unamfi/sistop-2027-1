# FiUnamFS: micro sistema de archivos multihilos

Proyecto final de Sistemas Operativos, Facultad de Ingeniería, UNAM.

Es un programa que monta imágenes del sistema de archivos `FiUnamFS`
(versión `27-1`) usando FUSE, para poder usarlas como si fueran una carpeta
normal con `ls`, `cp` y `rm`.

## Autor

- Daniel Berumen Valdez

## Funcionalidad

El programa puede:

1. Listar los contenidos del directorio
2. Copiar un archivo de FiUnamFS hacia el equipo
3. Copiar un archivo del equipo hacia FiUnamFS
4. Eliminar un archivo de FiUnamFS
5. Trabajar con varios hilos al mismo tiempo, sincronizados

## Entorno y dependencias

- Linux (lo probé en Ubuntu dentro de WSL2)
- Python 3.8 o superior
- python-fuse (fuse-python) 1.0.x, la misma biblioteca que se usó en clase
- fuse3 (para tener `fusermount`)

Para instalar en Debian / Ubuntu:

```
sudo apt update
sudo apt install python3-fuse fuse3
```

Si no está el paquete `python3-fuse` se puede instalar con pip, pero hay que
compilarlo:

```
sudo apt install libfuse-dev pkg-config gcc python3-dev python3-venv fuse3
python3 -m venv ~/venv-fiunamfs
source ~/venv-fiunamfs/bin/activate
pip install fuse-python
```

Ojo: fusepy es otra biblioteca que también se importa como `fuse`, pero no
sirve para este programa. Si es la que encuentra, el programa avisa.

## Estructura del proyecto

- `fiunamfs.py`: lee y escribe la imagen (superbloque, directorio y datos)
- `fiunamfs_fuse.py`: la parte de FUSE y los hilos
- `crear_imagen.py`: genera una imagen vacía para pruebas
- `README.md` y `.gitignore`

## Formato de FiUnamFS

El disco se divide en tres partes:

1. Superbloque (cluster 0): identificación, versión, etiqueta y tamaños
2. Directorio (clusters 1 a 4): 128 entradas de 64 bytes
3. Datos (del cluster 5 en adelante): los archivos, cada uno en clusters seguidos

Otros datos:

- Sector de 512 bytes y cluster de 4 sectores (2048 bytes)
- Enteros de 32 bits en little endian
- Cadenas en ASCII de 8 bits

## Uso

Primero se necesita una imagen. Se puede usar la del profe (`fiunamfs.img`) o
crear una de prueba con:

```
python3 crear_imagen.py
```

Te pregunta el nombre de la imagen, la etiqueta y si quieres que le meta unos
archivos de ejemplo.

Para usarlo se necesitan dos terminales abiertas al mismo tiempo. Esto es
porque el programa se queda corriendo todo el tiempo que la imagen está
montada (es el que contesta cuando alguien usa la carpeta), entonces esa
terminal ya no se puede usar para otra cosa.

### Terminal 1: montar la imagen

Aquí se corre el programa y se deja abierto:

```
mkdir -p ~/montaje
python3 fiunamfs_fuse.py fiunamfs.img ~/montaje
```

(Si se instaló con pip, antes hay que hacer `source ~/venv-fiunamfs/bin/activate`.)

`mkdir` solo se necesita la primera vez, crea la carpeta vacía donde se va a
"conectar" la imagen. Si la imagen no es FiUnamFS 27-1 el programa no la monta.

Si todo sale bien aparece esto y la terminal ya no regresa al prompt:

```
Montando fiunamfs.img en /home/daniel/montaje
Para desmontar: fusermount -u /home/daniel/montaje (o Ctrl+C aquí)
```

Así se tiene que quedar. Aquí van a ir saliendo los mensajes de la bitácora
cada vez que se haga algo en la carpeta.

### Terminal 2: usar la carpeta

Se abre otra terminal (otra pestaña) y ahí se usan los comandos normales de
Linux sobre `~/montaje`. En esta no hace falta activar nada:

```
ls -l ~/montaje                 # listar
cp ~/montaje/logo.png ~/        # copiar de FiUnamFS a la computadora
cp algo.txt ~/montaje/          # copiar de la computadora a FiUnamFS
rm ~/montaje/README.org         # eliminar
```

Mientras se hace esto, en la terminal 1 van apareciendo los mensajes de lo que
pasó.

### Desmontar

1. En la terminal 2 salirse de la carpeta con `cd ~` (si no, Linux dice que
   la carpeta está ocupada y no deja desmontar).
2. En la terminal 1 presionar Ctrl+C. Debe salir `Imagen desmontada` y
   regresar al prompt.

Si Ctrl+C no funciona, se puede desmontar desde la terminal 2 con
`fusermount -u ~/montaje`.

Los cambios se guardan directo en el archivo `.img`, así que si se vuelve a
montar siguen ahí. Para no echar a perder la imagen original conviene hacer
una copia y montar la copia (`cp fiunamfs.img prueba.img`).

También se puede correr `python3 fiunamfs.py` sin FUSE. Tiene un menú para
listar, copiar y borrar, y lo usé para ir probando mientras lo hacía.

## Cómo funciona

Para leer un archivo se va a `cluster_inicial * 2048` y se leen solo los bytes
que dice el tamaño, porque lo que sobra del último cluster es basura.

Para escribir, como la asignación es contigua, saco una lista de los clusters
que están ocupados, la ordeno y busco el primer hueco donde quepa el archivo
completo (first fit). Escribo primero los datos y luego la entrada del
directorio, para que si algo falla el directorio no apunte a algo incompleto.

Para borrar solo marco la entrada como vacía (`-` y `#..............`). No
borro los datos porque ese espacio ya queda libre al no usarlo ninguna entrada.

Un problema que tuve con FUSE es que cuando haces `cp` te manda el archivo en
pedazos, y como el espacio tiene que ser contiguo no puedo saber dónde ponerlo
hasta saber cuánto mide. Lo que hice fue juntar los pedazos en memoria (en el
diccionario `pendientes`) y guardarlo en la imagen hasta que se cierra el
archivo (en `flush`). Si se sobrescribe un archivo y el nuevo no cabe, se
vuelve a poner el viejo.

## Sincronización

python-fuse atiende cada operación en un hilo diferente (está en modo
multihilo por defecto), entonces si haces dos `cp`
al mismo tiempo los dos pueden estar escribiendo en la imagen a la vez. Eso
puede hacer que los dos encuentren el mismo hueco libre y uno pise al otro.
Para evitarlo usé un `threading.Lock` (`self.candado`) y todo lo que lee o
modifica la imagen va dentro de `with self.candado:`.

Además hay un hilo que hice yo, el hilo bitácora. Los hilos de FUSE le mandan
mensajes de lo que hacen por medio de una `queue.Queue` y la bitácora los va
sacando e imprimiendo. Es el esquema de productor/consumidor: los hilos de FUSE
producen mensajes y la bitácora los consume. Cuando se desmonta, el hilo
principal manda `None` a la cola para que la bitácora sepa que tiene que
terminar, y la espera con `join()`.

En cada mensaje se ve el número del hilo que hizo la operación, así se nota que
son hilos diferentes.

## Ejemplos

Con la imagen del profe montada:

```
$ ls -l ~/montaje
-rw-r--r-- 1 daniel daniel  31126 Nov  5 16:31 README.org
-rw-r--r-- 1 daniel daniel 126423 Nov  5 16:31 logo.png
-rw-r--r-- 1 daniel daniel 254484 Nov  5 16:31 mensaje.jpg

$ cp ~/montaje/logo.png ~/
$ cp fiunamfs.py ~/montaje/
$ rm ~/montaje/README.org

$ ls -l ~/montaje
-rw-r--r-- 1 daniel daniel  11301 Nov 18 23:40 fiunamfs.py
-rw-r--r-- 1 daniel daniel 126423 Nov  5 16:31 logo.png
-rw-r--r-- 1 daniel daniel 254484 Nov  5 16:31 mensaje.jpg
```

Lo que sale en la terminal donde se montó:

```
[bitácora] 23:40:01 (hilo 170) listar directorio (3 archivos)
[bitácora] 23:40:01 (hilo 170) leer logo.png (126423 bytes)
[bitácora] 23:40:01 (hilo 170) crear fiunamfs.py
[bitácora] 23:40:01 (hilo 169) guardar fiunamfs.py (11301 bytes)
[bitácora] 23:40:01 (hilo 170) eliminar README.org
```

Algunos errores:

```
$ cp foto.jpg ~/montaje/nombre_demasiado_largo.jpg
cp: cannot create regular file '/home/daniel/montaje/nombre_demasiado_largo.jpg': File name too long

$ cp archivo_de_2MB.bin ~/montaje/
cp: failed to close '/home/daniel/montaje/archivo_de_2MB.bin': No space left on device

$ mkdir ~/montaje/carpeta
mkdir: cannot create directory '/home/daniel/montaje/carpeta': Function not implemented
```

## Contenido del disco de ejemplo

La imagen del profe tiene la etiqueta `Disco de Gunnar`, clusters de 2048
bytes, 4 clusters de directorio y 720 clusters en total.

Tiene 3 archivos, todos creados el 2026-11-05 a las 16:31:24:

- `README.org` (31126 bytes, cluster 6): es el planteamiento de este proyecto.
- `logo.png` (126423 bytes, cluster 22): el escudo de la Facultad de Ingeniería.
- `mensaje.jpg` (254484 bytes, cluster 84): una foto de una persona con una
  hoja que dice "¡Muy bien hecho! Lograste recuperar la información del
  sistema de archivos FiUNAMFS. ¡Sigue adelante! :-)"

Algo que noté es que en la imagen del profe los nombres vienen rellenados con
espacios y con un `\0` al final, y al principio mi programa no los encontraba
por eso. Ya lo arreglé.

## Limitaciones

- No hay subdirectorios.
- No se pueden renombrar archivos.
- Los nombres son de máximo 15 caracteres ASCII.
- Puede que haya espacio libre pero no quepa un archivo si el espacio está
  separado en pedazos, porque no hice desfragmentación.

## Uso de IA

Usé un LLM (Claude) para resolver errores durante el desarrollo: instalar WSL
y python-fuse, el problema con los nombres de la imagen del profesor, que
venían rellenados con espacios y `\0`, y que Ctrl+C no desmontara. También me
ayudó a diseñar cómo guardar los archivos que llegan en pedazos desde FUSE
(`write`, `truncate` y `flush` en `fiunamfs_fuse.py`).
