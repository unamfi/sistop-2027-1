# Proyecto 1: (Micro) sistema de archivos multihilos

Sistemas Operativos — Facultad de Ingeniería, UNAM (semestre 2027-1)

## Autores

- NOMBRE COMPLETO DEL ALUMNO (número de cuenta) — *(cambiar por tus datos)*

## Descripción

Programa en Python que trabaja sobre una imagen de disco con el sistema de
archivos **FiUnamFS** (versión `27-1`) y permite:

1. Listar el contenido del directorio.
2. Copiar un archivo del FiUnamFS hacia mi computadora.
3. Copiar un archivo de mi computadora hacia el FiUnamFS.
4. Eliminar un archivo del FiUnamFS.
5. Operar con varios hilos que se comunican mediante mecanismos de sincronización.

## Entorno y dependencias

- Lenguaje: **Python 3** (probado con Python 3.12; no se usa nada exclusivo de
  versiones recientes).
- Módulos utilizados: únicamente la biblioteca estándar (`os`, `sys`, `struct`,
  `threading`, `datetime`). **No hay que instalar nada con pip.**
- Sistema operativo: probado en Linux; no se usan funciones específicas de
  ningún sistema, así que debe funcionar también en Windows y macOS.

## Archivos del proyecto

| Archivo | Para qué sirve |
|---|---|
| `fiunamfs.py` | El programa principal |
| `crear_disco_prueba.py` | Genera una imagen FiUnamFS de prueba (el disco de ejemplo del profesor aún no estaba disponible cuando desarrollé el proyecto) |
| `.gitignore` | Evita subir imágenes de disco, la bitácora y archivos temporales de Python |

## Cómo ejecutarlo

```
python3 crear_disco_prueba.py          # opcional: crea fiunamfs.img de prueba
python3 fiunamfs.py fiunamfs.img       # abre el disco con el menú
```

Si no se indica la imagen, se usa `fiunamfs.img` en la carpeta actual.
El programa **valida** que el nombre sea `FiUnamFS` y que la versión sea `27-1`;
si no coincide, se niega a abrir el archivo para no dañarlo.

## Uso (menú textual)

El programa muestra un menú y va pidiendo, paso a paso, los datos que necesita
(no hace falta memorizar comandos):

```
======== FiUnamFS ========
1) Listar el contenido del disco
2) Copiar un archivo del FiUnamFS a mi computadora
3) Copiar un archivo de mi computadora al FiUnamFS
4) Eliminar un archivo del FiUnamFS
5) Informacion del disco
0) Salir
```

### Ejemplos

Listar:

```
Elige una opcion: 1
Nombre          Tamano(bytes)  Cluster  Creacion             Modificacion
----------------------------------------------------------------------------------
hola.txt                  32        5  2026-10-28 18:26:00  2026-10-28 18:26:00
README.txt              5600        6  2026-10-28 18:26:00  2026-10-28 18:26:00
Total: 2 archivo(s)
```

Copiar un archivo del FiUnamFS a mi computadora (la opción 2 primero muestra la
lista para ver los nombres):

```
Elige una opcion: 2
...
Nombre del archivo a copiar: hola.txt
Carpeta o ruta destino (Enter = carpeta actual): /tmp
Listo: 'hola.txt' (32 bytes) copiado a '/tmp/hola.txt'
```

Copiar un archivo de mi computadora al FiUnamFS:

```
Elige una opcion: 3
Ruta del archivo de tu computadora: /home/alumno/tarea.txt
Listo: 'tarea.txt' (1204 bytes) guardado desde el cluster 11
```

Eliminar:

```
Elige una opcion: 4
...
Nombre del archivo a eliminar: tarea.txt
¿Seguro que quieres eliminar 'tarea.txt'? (s/n): s
Listo: 'tarea.txt' eliminado
```

## Estrategia de diseño

- Todas las cifras (tamaño de cluster = 2048 bytes, directorio en los clusters
  1 a 4, entradas de 64 bytes, etc.) salen de la especificación. Los enteros de
  32 bits se leen/escriben en *little endian* con `struct` y el formato `<I`.
- **Directorio plano**: al leer, se recorren las 128 entradas de 64 bytes. Una
  entrada está libre si su nombre es `#...............` (o su tipo es `-`).
- **Asignación contigua**: al copiar un archivo hacia el FiUnamFS se calcula
  cuántos clusters necesita y se busca un hueco contiguo con la estrategia de
  *primer ajuste* (el primer hueco donde quepa, empezando en el cluster 5).
  Primero se escriben los datos y hasta el final la entrada del directorio, para
  no dejar una entrada apuntando a datos que no se escribieron.
- **Eliminar** solo marca la entrada como vacía (igual que FAT); los datos
  siguen en el disco pero ya nadie los referencia y el espacio se puede reusar.
- Los nombres de archivo se validan: máximo 15 caracteres y sólo ASCII de 7 bits.
  Si ya existe un archivo con ese nombre, no se sobrescribe (se avisa).

## Sincronización entre hilos

El programa usa **tres hilos**:

| Hilo | Qué hace |
|---|---|
| **Interfaz** (hilo principal) | Muestra el menú, lee lo que escribe el usuario y arma una `Solicitud` |
| **Trabajador** | Es el único que accede a la imagen de disco; atiende las solicitudes |
| **Bitácora** | Escribe en `fiunamfs.log` un registro de lo que hizo el trabajador |

Se comunican con el esquema clásico **productor–consumidor**:

- `BufferAcotado` es un buffer de capacidad fija protegido con un **mutex**
  (`threading.Lock`) y dos **semáforos** (`threading.Semaphore`): uno cuenta los
  espacios libres (bloquea al productor si el buffer está lleno) y otro cuenta
  los elementos disponibles (bloquea al consumidor si está vacío).
- Hay dos buffers: *interfaz → trabajador* (capacidad 5) y
  *trabajador → bitácora* (capacidad 10).
- Cada `Solicitud` trae un **`threading.Event`**. El hilo de interfaz se queda
  esperando en el evento y el trabajador lo activa al terminar; así el usuario
  ve el resultado de una operación antes de que le aparezca el menú otra vez.
- Para cerrar, la interfaz manda una solicitud `salir`; el trabajador avisa a la
  bitácora con un `None` y ambos hilos terminan; el principal hace `join()`.

Como un solo hilo (el trabajador) modifica el disco, nunca hay dos hilos
escribiendo el directorio al mismo tiempo, y por eso no hay condiciones de
carrera sobre la imagen.

## Limitaciones conocidas

- No hay desfragmentación: por la asignación contigua puede haber
  fragmentación externa, y un archivo grande puede no caber aunque en total
  haya espacio libre (el programa lo avisa).
- No se manejan subdirectorios (la especificación no los contempla).
- Nombres de archivo con acentos o ñ no están soportados (sólo US-ASCII).
