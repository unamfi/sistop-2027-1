# Proyecto 1 · FiUnamFS multihilo

**Autor** — Rodrigo Imanol Casas Pérez  
**Materia** — Sistemas Operativos, Facultad de Ingeniería, UNAM

Este programa sirve para listar, extraer, importar y borrar archivos de
una imagen de FiUnamFS. Tiene un menú en la terminal y usa un segundo hilo
para atender las operaciones del disco.

## Qué necesitas

Lo probé en Ubuntu con CPython 3.12.3. Todo lo que usa viene con Python,
así que no hay que instalar paquetes extra. La imagen del profe ya viene
en el repo, en `proyectos/1/fiunamfs.img`.

## Cómo probarlo

Desde la raíz del repo, haz una copia de la imagen para que puedas
agregar y borrar archivos sin tocar la original.

```bash
cp proyectos/1/fiunamfs.img /tmp/fiunamfs-prueba.img
python3 proyectos/1/CasasRodrigo/fiunamfs.py /tmp/fiunamfs-prueba.img
```

| Opción | Qué hace |
| --- | --- |
| 1 | Muestra los archivos del disco |
| 2 | Copia un archivo del disco a tu compu |
| 3 | Copia un archivo de tu compu al disco |
| 4 | Borra un archivo del disco |
| 5 | Espera a que terminen las operaciones y muestra sus resultados |
| 0 | Termina las operaciones pendientes y cierra el programa |

Por ejemplo, para sacar `logo.png`, elige `2`, escribe `logo.png` y
pon `/tmp/logo-extraido.png` como destino. Elige una ruta donde todavía
no exista un archivo con ese nombre. Si el resultado sigue pendiente,
puedes usar la opción `5` para verlo.

## Cómo funciona por dentro

Primero reviso el superbloque para confirmar que la imagen sea de
`FiUnamFS`, que tenga la versión `27-1` y que los tamaños cuadren.
Después leo el directorio, donde cada entrada ocupa 64 bytes.

Para extraer un archivo, multiplico su clúster inicial por el tamaño
del clúster. Eso me da la posición donde empiezan sus datos. Desde
ahí leo la cantidad de bytes que dice el directorio.

Para meter un archivo, busco una entrada libre y un tramo de clústeres
seguidos donde quepa. Escribo los datos y luego registro el archivo en
el directorio. Para borrarlo, marco su entrada como libre. Así, esos
clústeres se pueden usar en otra importación.

## Cómo se coordinan los hilos

El hilo principal se encarga del menú. Cuando eliges una operación,
la pone en una cola de `queue.Queue`. El trabajador espera solicitudes
con `get()`, las atiende en el orden en que llegaron y manda cada
resultado por una segunda cola.

Así puedes pedir una importación y luego un listado sin esperar a
que aparezca el primer resultado. El trabajador termina la importación
antes de listar, porque atiende una operación a la vez. Cuando eliges
salir, el hilo principal pone `None` al final de la cola y espera con
`join()` a que el trabajador termine.

## Qué traía el disco del profe

| Archivo | Tamaño en bytes | Clúster inicial |
| --- | ---: | ---: |
| `README.org` | 31126 | 6 |
| `logo.png` | 126423 | 22 |
| `mensaje.jpg` | 254484 | 84 |

En una copia del disco importé `prueba.txt`, lo borré y lo volví a
importar. Las dos veces quedó en el clúster 5, así que pude comprobar
que el espacio se reutilizó.

También mandé cuatro órdenes seguidas desde el menú: borrar, importar,
listar y extraer. Se ejecutaron en ese orden y usé `cmp` para comprobar
que el archivo extraído era idéntico al original.
