# Proyecto 1: (Micro) sistema de archivos multihilos — FiUnamFS

Sistemas Operativos, Facultad de Ingeniería, UNAM — Semestre 2027-1

## Autores

- Bermejo Flores José Tristán — 321016719
- Hernández Reyes Rebeca Sarai — 321491864

## Descripción

`fiunamfs.py` es un programa que lee y modifica una imagen del sistema de
archivos **FiUnamFS** (versión `27-1`), un micro sistema de archivos plano de
1440 KB que simula un diskette. Permite:

1. Listar el contenido del directorio.
2. Copiar un archivo de FiUnamFS hacia el equipo local.
3. Copiar un archivo del equipo local hacia FiUnamFS.
4. Eliminar un archivo de FiUnamFS.
5. Operar con dos hilos concurrentes que se comunican mediante mecanismos de
   sincronización (ver más abajo).

## Entorno y dependencias

- Lenguaje: Python 3.12 (desarrollado y probado con 3.12.3; debería funcionar
  desde 3.8).
- Módulos: únicamente biblioteca estándar (`os`, `queue`, `shlex`, `struct`,
  `sys`, `threading`, `datetime`). No hay nada que instalar.
- Sistema operativo: cualquiera con Python 3 (Linux, macOS, Windows).
- Un archivo de imagen FiUnamFS 27-1 (por ejemplo `fiunamfs.img`).

## Uso

Menú guiado (no requiere conocer ninguna orden):

```
python3 fiunamfs.py fiunamfs.img
```

```
==== FiUnamFS: Disco de Gunnar ====
  1. Ver los archivos del disco
  2. Copiar un archivo del disco a mi equipo
  3. Copiar un archivo de mi equipo al disco
  4. Eliminar un archivo del disco
  5. Información del disco
  0. Salir
Elige una opción:
```

El menú va preguntando lo necesario:

- **Opciones 2 y 4:** muestran los archivos numerados y basta con escribir el
  número. Eliminar pide confirmación (`s/n`).
- **Opción 2:** pregunta con qué nombre guardar el archivo (Enter usa el mismo
  nombre; también se puede dar una carpeta). Nunca sobrescribe archivos locales.
- **Opción 3:** pide la ruta del archivo de tu equipo y el nombre que tendrá en
  el disco (Enter usa el nombre original). Si el nombre no es válido, explica
  por qué y pide otro.
- Enter en cualquier pregunta cancela la operación y regresa al menú.

### Modo de una sola orden

Para guiones o uso rápido, se puede dar la orden directamente:

| Orden | Qué hace |
|---|---|
| `ls` | Lista los archivos (nombre, tamaño, cluster inicial, fechas) |
| `get <nombre> [destino]` | Copia de FiUnamFS al equipo; no sobrescribe archivos locales |
| `put <ruta> [nombre]` | Copia del equipo a FiUnamFS (el nombre por omisión es el del archivo local) |
| `rm <nombre>` | Elimina un archivo de FiUnamFS |
| `info` | Muestra los datos del superbloque |

### Ejemplos

```
$ python3 fiunamfs.py fiunamfs.img ls
$ python3 fiunamfs.py fiunamfs.img put foto.png
Copiado 'foto.png' -> FiUnamFS como 'foto.png' (5000 bytes, cluster 209).
$ python3 fiunamfs.py fiunamfs.img get foto.png copia.png
Copiado 'foto.png' -> 'copia.png' (5000 bytes).
$ python3 fiunamfs.py fiunamfs.img rm foto.png
Eliminado 'foto.png'.
```

## Estrategia

- **Validación:** antes de operar se comprueba que los bytes 0–7 del
  superbloque sean `FiUnamFS` y los bytes 10–13 sean `27-1`. Si no, el programa
  se niega a continuar y no modifica la imagen. También se verifica que la
  imagen tenga al menos el tamaño que declara el superbloque.
- **Estructuras:** enteros de 32 bits *little endian* con `struct` (`<I`);
  cadenas en ASCII. El tamaño de cluster, el tamaño del directorio y el total
  de clusters se leen del superbloque, no están fijos en el código.
- **Directorio:** clusters 1 a 4, entradas de 64 bytes. Una entrada está libre
  si su tipo es `-` o su nombre es un marcador de vacío (`#..............`, como
  dice la especificación, o `##############`, como aparece en el disco de
  ejemplo). Al eliminar, la entrada se reescribe byte por byte igual que las
  vacías del disco de ejemplo (los datos no se borran del área de datos). Los
  huecos del directorio se reutilizan; no se compacta.
- **Asignación contigua (first-fit):** `put` calcula los clusters necesarios y
  busca el primer hueco contiguo entre los archivos existentes en el área de
  datos. Si no hay uno suficientemente grande, informa que el disco está lleno
  o fragmentado. Se escriben primero los datos y al final la entrada del
  directorio.
- **Fechas:** al copiar un archivo, creación y modificación se fijan a la hora
  actual con formato `AAAAMMDDHHMMSS`.

## Sincronización

El programa usa dos hilos:

- **Hilo de interfaz (principal):** muestra el menú, lee lo que elige el usuario
  y crea una `Solicitud` por cada operación (productor).
- **Hilo `hilo-fs`:** es el único que accede a la imagen; toma solicitudes de
  la cola y las ejecuta (consumidor).

Mecanismos empleados:

| Mecanismo | Para qué |
|---|---|
| `queue.Queue` | Cola productor/consumidor. El `hilo-fs` se bloquea en `get()` cuando no hay trabajo, sin espera activa. Enviar `None` lo hace terminar. |
| `threading.Event` (`Solicitud.terminada`) | El `hilo-fs` lo activa al concluir una operación; el hilo de interfaz espera en `wait()` y después lee el resultado o el error. Así se comunica el estado entre hilos. |
| `threading.Lock` (`FiUnamFS.candado`) | Exclusión mutua sobre la imagen: la secuencia leer directorio → buscar hueco → escribir datos → escribir entrada es una sección crítica. |

Cualquier excepción en el `hilo-fs` se guarda en la solicitud y se activa el
`Event` de todos modos (bloque `finally`), por lo que la interfaz nunca queda
bloqueada esperando.

## Supuestos y limitaciones

- El disco de ejemplo guarda los nombres con 14 caracteres rellenos con
  espacios y un byte nulo en la posición 15 (la especificación habla de 15 bytes
  de nombre). Se imita ese formato al escribir y al leer se ignoran espacios y
  nulos finales.
- Un archivo de tamaño 0 ocupa 1 cluster.
- Los nombres deben ser ASCII imprimible, de 1 a 14 caracteres, y no pueden
  estar formados solo por `#` y `.`.
- `put` no sobrescribe un nombre existente; `get` no sobrescribe un archivo
  local existente.
- Por ser asignación contigua, el disco puede fragmentarse; no hay
  desfragmentación.

## Pruebas realizadas

Con el disco de ejemplo `fiunamfs.img` (sobre una copia): listado, extracción
de sus tres archivos (`README.org`, `logo.png`, `mensaje.jpg`), copia de un
archivo nuevo hacia el disco y de regreso (idéntico, verificado con `cmp`),
eliminación (el directorio queda byte por byte igual al original tras un
`put` seguido de `rm`) y reutilización de huecos. También se probaron nombres
duplicados, nombres demasiado largos, archivos inexistentes, destinos locales
ya existentes e imágenes que no son FiUnamFS.
