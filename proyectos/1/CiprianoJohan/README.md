# Proyecto 1: (Micro) sistema de archivos multihilos — FiUnamFS

**Autor:** Cipriano Amador Johan Tadeo
**Materia:** Sistemas Operativos 2027-1, Facultad de Ingeniería, UNAM

Programa para trabajar con imágenes del sistema de archivos `FiUnamFS`
(versión 27-1). Permite:

1. Listar los contenidos del directorio
2. Copiar un archivo de FiUnamFS hacia el equipo
3. Copiar un archivo del equipo hacia FiUnamFS
4. Eliminar un archivo de FiUnamFS
5. Todo lo anterior con tres hilos concurrentes que se comunican su estado
   mediante mecanismos de sincronización

## Contenido del disco de ejemplo

El volumen `fiunamfs.img` del planteamiento (etiqueta *Disco de Gunnar*)
contiene tres archivos:

| Nombre       | Tamaño (bytes) | Cluster inicial |
|--------------|---------------:|----------------:|
| `README.org` |         31 126 |               6 |
| `logo.png`   |        126 423 |              22 |
| `mensaje.jpg`|        254 484 |              84 |

## Entorno y requisitos

- **Lenguaje:** Python 3, implementación CPython, versión 3.8 o superior
  (se usa `threading.Condition.wait_for` y f-strings).
- **Dependencias:** ninguna; solo biblioteca estándar (`struct`, `threading`,
  `queue`, `datetime`, `os`, `sys`). No hay nada que instalar.
- **Probado en:** Windows 11 (Git Bash) y Linux.

## Uso

Desde la carpeta `proyectos/1/CiprianoJohan`:

```bash
python main.py ../fiunamfs.img
```

En **Git Bash para Windows** conviene anteponer `winpty`, que le da a Python
una consola real (entrada interactiva y `Ctrl+C` funcionan como se espera):

```bash
winpty python main.py ../fiunamfs.img
```

Si no se indica la imagen, el programa la pregunta y propone
`../fiunamfs.img`. Aparece un menú:

```
=== FiUnamFS · 'Disco de Gunnar' · 3 archivo(s) · 512 clusters libres ===
  1. Listar el contenido
  2. Copiar de FiUnamFS a mi equipo
  3. Copiar de mi equipo a FiUnamFS
  4. Eliminar un archivo
  5. Información del volumen y bitácora
  0. Salir
```

Cada opción pide lo que necesita: los archivos se eligen por número o por
nombre, la carpeta destino por omisión es `extraidos/`, se puede arrastrar
un archivo a la terminal para dar su ruta y antes de eliminar se pide
confirmación. Si el nombre de un archivo no cabe en FiUnamFS (más de 15
caracteres o caracteres fuera de US-ASCII), se pide uno nuevo.

> **Recomendación:** para probar operaciones que modifican el volumen,
> trabaja sobre una copia y deja intacto el disco original del repositorio:
> `cp ../fiunamfs.img prueba.img && python main.py prueba.img`
> (los archivos `*.img` y la carpeta `extraidos/` están en el `.gitignore`).

### Ejemplo de sesión

```
Opción: 2
   #  Nombre              Tamaño Cluster  Modificación
  ----------------------------------------------------------------
   1  README.org           31126       6  2026-11-05 16:31:24
   2  logo.png            126423      22  2026-11-05 16:31:24
   3  mensaje.jpg         254484      84  2026-11-05 16:31:24
Número o nombre del archivo a copiar a tu equipo (Enter cancela): 3
Carpeta destino [extraidos]:
✓ Copiado a extraidos/mensaje.jpg
```

### Modo de línea de comandos

`fiunamfs.py` también se puede usar directamente, sin hilos, para
operaciones sueltas:

```bash
python fiunamfs.py prueba.img                          # listar
python fiunamfs.py prueba.img extraer logo.png extraidos/
python fiunamfs.py prueba.img copiar notas.txt
python fiunamfs.py prueba.img eliminar notas.txt
```

## Estrategia

| Archivo           | Contenido |
|-------------------|-----------|
| `fiunamfs.py`     | Todo lo que depende de la especificación: constantes, superbloque, entradas del directorio y operaciones sobre la imagen |
| `concurrencia.py` | Hilos «disco» y «bitácora», cola de solicitudes y estado compartido sincronizado |
| `main.py`         | Interfaz de texto (menú) |

- **Validación:** antes de tocar la imagen se verifica que el superbloque diga
  `FiUnamFS` y versión `27-1`; cualquier otra imagen se rechaza para no
  corromperla. La geometría (tamaño de cluster, clusters del directorio y
  totales) se lee del superbloque.
- **Enteros:** se leen y escriben como 32 bits *little endian* con
  `struct.pack("<I")` / `struct.unpack("<I")`.
- **Ocupación del disco:** como toda la información de los archivos está en
  el directorio, el mapa de clusters ocupados se reconstruye a partir de las
  entradas; no hace falta un mapa de bits aparte.
- **Copiar hacia FiUnamFS:** asignación contigua con *first fit*: el archivo se
  coloca en el primer hueco de clusters libres consecutivos que alcance. Se
  escriben primero los datos y al final la entrada, para que una falla a la
  mitad no deje el directorio apuntando a datos incompletos.
- **Eliminar:** la entrada se marca libre (tipo `-` y nombre
  `#..............`); sus clusters vuelven a estar disponibles.

## Hilos y sincronización

```
  interfaz (principal)          disco                         bitácora
  ────────────────────          ─────                         ────────
  Solicitud ──► Queue ───────►  ejecuta en la imagen
  espera Event ◄──────────────  Event.set()
                                publica estado ──Condition──► registra operación
  lee estado (instantánea) ◄──  (con candado)                 y clusters libres
```

- **Interfaz** (hilo principal): nunca toca la imagen. Cada operación se
  convierte en una `Solicitud` que se deposita en una `queue.Queue`.
- **disco:** es el único hilo que lee y escribe la imagen. Consume la cola
  (patrón productor–consumidor), así que las operaciones quedan serializadas
  y el directorio no puede quedar inconsistente aunque varios hilos pidan
  cosas a la vez. Al terminar una solicitud la marca con un
  `threading.Event`, por el que la interfaz espera sin sondear. Si la
  operación falla, el error viaja en la misma solicitud y se muestra en la
  interfaz.
- **bitácora:** espera con una `threading.Condition` a que el hilo disco
  publique una versión nueva del estado (archivos y clusters libres) y la
  registra. Se puede ver con la opción 5 del menú.
- **Estado compartido:** el hilo disco lo modifica con el candado de la
  `Condition` tomado y despierta a los interesados con `notify_all()`. La
  interfaz lee una copia consistente del mismo estado para el encabezado del
  menú, sin pasar por la cola.
- **Cierre:** al salir se encola un centinela (`None`); el hilo disco cierra la
  imagen y termina, después se cierra el estado y termina la bitácora.

## Nota sobre la especificación

El ejemplo del planteamiento indica que `1234567890` se representa con los
bytes `210, 2, 150, 7`; el valor correcto en *little endian* es
`210, 2, 150, 73` (`0x499602D2`). La implementación usa `struct`, por lo que
produce el valor correcto.
