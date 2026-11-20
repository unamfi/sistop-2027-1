# Proyecto 1: (Micro) sistema de archivos multihilos

Sistemas Operativos — Facultad de Ingeniería, UNAM (semestre 2027-1)

## Autores

- Brayan López Ramírez — NÚMERO DE CUENTA *(cambiar)*

## Descripción

Programa en Python que trabaja sobre una imagen de disco con el sistema de
archivos **FiUnamFS** (versión `27-1`) y permite:

1. Listar el contenido del directorio.
2. Copiar un archivo del FiUnamFS hacia mi computadora.
3. Copiar un archivo de mi computadora hacia el FiUnamFS.
4. Eliminar un archivo del FiUnamFS.
5. Operar con varios hilos que se comunican mediante mecanismos de sincronización.

## Entorno y dependencias

- Lenguaje: **Python 3** (versión mayor 3), implementación CPython.
  Versión con la que se probó: **Python 3.15.0a3** en Windows 11. Se
  puede consultar la versión instalada con `python --version`.
- Módulos utilizados: únicamente la biblioteca estándar (`os`, `sys`, `struct`,
  `threading`, `datetime`). **No hay que instalar nada con pip.**
- Sistema operativo: desarrollado y probado en Windows 11. No se usan
  funciones específicas de ningún sistema.
- En Windows el comando para ejecutar es `python`.

## Archivos del proyecto

| Archivo | Para qué sirve |
|---|---|
| `fiunamfs.py` | El programa principal |
| `crear_disco_prueba.py` | Genera una imagen FiUnamFS de prueba (el disco de ejemplo del profesor aún no estaba disponible cuando desarrollé el proyecto) |
| `.gitignore` | Evita subir imágenes de disco, la bitácora y archivos temporales de Python |

## Cómo ejecutarlo

```
python crear_disco_prueba.py          # opcional: crea fiunamfs.img de prueba
python fiunamfs.py fiunamfs.img       # abre el disco con el menú
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
hola.txt                   32        5  2026-10-28 18:26:00  2026-10-28 18:26:00
README.txt               5600        6  2026-10-28 18:26:00  2026-10-28 18:26:00
Total: 2 archivo(s)
```

Copiar un archivo del FiUnamFS a mi computadora (la opción 2 primero muestra la
lista para ver los nombres):

```
Elige una opcion: 2
...
Nombre del archivo a copiar: hola.txt
Carpeta o ruta destino (Enter = carpeta actual):
Listo: 'hola.txt' (32 bytes) copiado a 'hola.txt'
```

Copiar un archivo de mi computadora al FiUnamFS:

```
Elige una opcion: 3
Ruta del archivo de tu computadora: prueba.txt
Listo: 'prueba.txt' (17 bytes) guardado desde el cluster 11
```

Eliminar:

```
Elige una opcion: 4
...
Nombre del archivo a eliminar: prueba.txt
¿Seguro que quieres eliminar 'prueba.txt'? (s/n): s
Listo: 'prueba.txt' eliminado
```

Ejemplos de errores que el programa maneja sin cerrarse:

```
Error: No existe el archivo 'noexiste.txt' en tu computadora
Error: Ya existe un archivo llamado 'prueba.txt' en el FiUnamFS
Error: No hay 800 clusters contiguos libres (fragmentacion externa o disco lleno)
```

## Estrategia de diseño

- Todas las cifras (tamaño de cluster = 2048 bytes, directorio en los clusters
  1 a 4, entradas de 64 bytes, etc.) salen de la especificación. Los enteros de
  32 bits se leen/escriben en *little endian* con `struct` y el formato `<I`.
- La clase `SistemaArchivos` encapsula todo el acceso al disco: lee y valida el
  superbloque (`cargar_superbloque`), lee el directorio (`obtener_directorio`) y
  ofrece las operaciones (`ver_lista`, `sacar_archivo`, `meter_archivo`,
  `quitar_archivo`, `ver_info`).
- **Directorio plano**: al leer, se recorren las 128 entradas de 64 bytes. Una
  entrada está libre si su nombre es `#...............` (o su tipo es `-`).
- **Asignación contigua**: al copiar un archivo hacia el FiUnamFS se calcula
  cuántos clusters necesita (`calcular_clusters`) y se busca un hueco contiguo
  con la estrategia de *primer ajuste* (`hallar_hueco`: el primer hueco donde
  quepa, empezando en el cluster 5). Primero se escriben los datos y hasta el
  final la entrada del directorio, para no dejar una entrada apuntando a datos
  que no se escribieron.
- **Eliminar** solo marca la entrada como vacía (igual que FAT); los datos
  siguen en el disco pero ya nadie los referencia y el espacio se puede reusar.
- Los nombres de archivo se validan (`revisar_nombre`): máximo 15 caracteres y
  sólo ASCII de 7 bits. Si ya existe un archivo con ese nombre, no se
  sobrescribe (se avisa).
- Los errores propios del sistema de archivos se lanzan como `ErrorSistema` y se
  muestran al usuario sin cerrar el programa.

## Sincronización entre hilos

El programa usa **tres hilos**:

| Hilo | Función | Qué hace |
|---|---|---|
| **Interfaz** (hilo principal) | `menu_usuario` | Muestra el menú, lee lo que escribe el usuario y arma una `Tarea` |
| **Trabajador** | `worker_principal` | Es el único que accede a la imagen de disco; atiende las tareas en orden |
| **Bitácora** | `worker_log` | Escribe en `fiunamfs.log` un registro de lo que hizo el trabajador |

Se comunican con el esquema clásico **productor–consumidor**:

- `ColaSegura` es una cola de capacidad fija protegida con un **mutex**
  (`threading.Lock`, llamado `candado`) y dos **semáforos**
  (`threading.Semaphore`): `lugares_vacios` cuenta los espacios libres
  (bloquea al productor si la cola está llena) y `lugares_llenos` cuenta los
  elementos disponibles (bloquea al consumidor si está vacía).
- Hay dos colas: *interfaz → trabajador* (capacidad 5) y
  *trabajador → bitácora* (capacidad 10).
- Cada `Tarea` trae un **`threading.Event`** (`terminado`). El hilo de interfaz
  se queda esperando en el evento (`mandar_tarea`) y el trabajador lo activa al
  terminar; así el usuario ve el resultado de una operación antes de que le
  aparezca el menú otra vez.
- Para cerrar, la interfaz manda una tarea `salir`; el trabajador avisa a la
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
