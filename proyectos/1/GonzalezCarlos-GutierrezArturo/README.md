# Proyecto 1: (Micro) sistema de archivos multihilos — FiUnamFS

**Autores:**

- Carlos Gonzalez
- Arturo Gutierrez

Programa en Python para trabajar con imágenes del sistema de archivos
FiUnamFS versión `27-1`. Desde un menú de texto permite:

1. Listar los contenidos del directorio.
2. Copiar un archivo de FiUnamFS hacia nuestro equipo.
3. Copiar un archivo de nuestro equipo hacia FiUnamFS.
4. Eliminar un archivo de FiUnamFS.

Todas las operaciones sobre la imagen las hace un hilo aparte, que se
comunica con el hilo del menú mediante mecanismos de sincronización (ver
la sección de [Sincronización](#sincronización)).

## Entorno y requisitos

- Python 3.10 o posterior (lo probamos con Python 3.13). Se necesita
  mínimo la 3.10 porque usamos anotaciones del tipo `Exception | None`.
- Solo se usa la biblioteca estándar (`struct`, `threading`, `queue`,
  `pathlib`, `dataclasses`, `datetime`), así que **no hay que instalar
  nada** con pip.
- Funciona igual en Windows y en Linux. En Windows el comando
  normalmente es `python` en lugar de `python3`.

## Estructura

| Archivo        | Contenido                                                                 |
|----------------|---------------------------------------------------------------------------|
| `fiunamfs.py`  | Clase `SistemaFiUnamFS`: lee el superbloque y el directorio, y hace las cuatro operaciones sobre la imagen. |
| `interfaz.py`  | Menú de texto. Pide los datos al usuario y muestra los resultados.        |
| `main.py`      | Arranca el programa, crea el hilo trabajador (`hilo-disco`) y lo conecta con el menú. |

## Cómo ejecutarlo

Desde la carpeta del proyecto. Recomendamos trabajar sobre una **copia** de
la imagen del profesor, para no modificar el `fiunamfs.img` que está en el
repositorio (las copias `*.img` dentro de nuestra carpeta están en el
`.gitignore`):

```bash
cd proyectos/1/GonzalezCarlos-GutierrezArturo
cp ../fiunamfs.img prueba.img        # en PowerShell: copy ..\fiunamfs.img prueba.img
python3 main.py prueba.img
```

Si no se le pasa ninguna ruta, el programa abre `../fiunamfs.img`
(la imagen original de `proyectos/1`).

## Uso

Al arrancar aparece el menú:

```
 Administrador FiUnamFS 
1. Listar archivos de la imagen
2. Copiar un archivo de la imagen a mi equipo
3. Copiar un archivo de mi equipo a FiUnamFS
4. Eliminar un archivo de FiUnamFS
0. Salir
Elige una opción:
```

- **Opción 2:** se escribe el nombre del archivo tal como sale en la
  lista. Como destino se puede dar una carpeta, una ruta completa, o
  simplemente presionar Enter para guardarlo en `extraidos/`.
- **Opción 3:** se pega la ruta del archivo local (con o sin comillas).
  Si no se escribe otro nombre, se usa el mismo. El nombre debe ser ASCII
  y de máximo 15 caracteres.
- **Opción 4:** se escribe el nombre exacto del archivo a borrar.

Cada operación imprime mensajes de los dos hilos (`[MainThread]` y
`[hilo-disco]`) para que se vea cómo se pasan el trabajo.

## Ejemplos de uso

Listar el disco de muestra:

```
Elige una opción: 1
[MainThread] Solicitud enviada: listar_archivos.
[hilo-disco] Ejecutando listar_archivos.
[hilo-disco] Operación terminada; notificando al menú.
[MainThread] Respuesta recibida.

Archivos en FiUnamFS:
Nombre               Tamaño  Cluster  Última modificación
---------------------------------------------------------
README.org            31126        6  2026-11-05 16:31:24
logo.png             126423       22  2026-11-05 16:31:24
mensaje.jpg          254484       84  2026-11-05 16:31:24
```

Extraer un archivo a la carpeta por defecto:

```
Elige una opción: 2
...
Nombre exacto del archivo que quieres copiar con todo y extensión: mensaje.jpg
Carpeta o ruta destino (Enter para guardarlo en extraidos/):
...
El archivo extraído en: .../GonzalezCarlos-GutierrezArturo/extraidos/mensaje.jpg
```

Copiar un archivo de la computadora a la imagen y luego borrar otro:

```
Elige una opción: 3
Ruta del archivo de tu equipo (puedes pegarla aquí): nota.txt
Nombre dentro de la imagen (Enter para usar el mismo nombre):
...
Copiado 'nota.txt': 11 bytes, cluster inicial 5.

Elige una opción: 4
...
Nombre exacto del archivo que quieres eliminar: logo.png
...
Se eliminó 'logo.png' exitosamente.
```

## Estrategia

**Validación.** Antes de hacer cualquier cosa se revisa que la imagen mida
exactamente 1440 KiB, que los bytes 0–7 digan `FiUnamFS` y que los bytes
10–13 digan `27-1`. Si algo no coincide, el programa se niega a abrirla,
para no corromper un sistema de archivos que no es el correcto.

**Superbloque.** Del cluster 0 se leen la etiqueta del volumen, el tamaño
de cluster, cuántos clusters mide el directorio y cuántos mide la unidad.
Todos los enteros se leen como 32 bits little endian con
`struct.unpack_from("<I", ...)`. No dejamos fijo el tamaño de cluster: se
usa el que dice el superbloque.

**Directorio.** Empieza en el cluster 1 y se recorre en entradas de 64
bytes. Una entrada solo cuenta como archivo si su tipo es `F` y su nombre
no empieza con `#`. Al leer el nombre se quitan los `\0` y los espacios
de relleno.

**Copiar hacia FiUnamFS (asignación contigua).** Con las entradas
existentes se arma el conjunto de clusters ocupados (cluster inicial +
clusters que necesita su tamaño). Después se busca, desde el primer
cluster de datos, el primer hueco con suficientes clusters seguidos
(*first fit*). Primero se escriben los datos y al final la entrada del
directorio, con la fecha actual como creación y modificación. Así, si algo
falla a la mitad, no queda una entrada apuntando a datos incompletos.

**Copiar desde FiUnamFS.** Se busca la entrada por nombre y se leen
`tamaño` bytes a partir de `cluster_inicial * tamaño_cluster`.

**Eliminar.** Solo se marca la entrada como libre (tipo `-` y nombre
`#..............`). Los datos no se borran, pero esos clusters ya no se
consideran ocupados y se pueden reutilizar en la siguiente copia.

## Sincronización

El programa usa dos hilos:

- **`MainThread`**: corre el menú y atiende al usuario.
- **`hilo-disco`**: es el único que toca la imagen. Lee y escribe el
  archivo `.img` cuando se lo piden.

Se comunican con un esquema **productor–consumidor**:

1. Cuando el usuario elige una opción, el menú crea un objeto `Solicitud`
   (operación + argumentos + un `threading.Event`) y lo mete en una
   `queue.Queue`. El menú es el productor.
2. `hilo-disco` está bloqueado en `cola.get()` hasta que llega una
   solicitud. La ejecuta y guarda el resultado (o la excepción) dentro de
   la misma solicitud. Es el consumidor.
3. Al terminar, el trabajador hace `solicitud.terminada.set()`. El menú,
   que estaba esperando con `solicitud.terminada.wait()`, despierta, lee el
   resultado y lo muestra. Si hubo un error en el hilo trabajador, la
   excepción se vuelve a lanzar en el hilo del menú para mostrarla ahí.
4. Para salir, el menú mete `None` a la cola como señal de fin. El
   trabajador termina su ciclo y el programa espera a que acabe con
   `cola.join()` y `hilo_disco.join()`.

¿Por qué así? La `Queue` ya es segura entre hilos, y como **solo un hilo
escribe en la imagen**, las operaciones nunca se enciman: no puede pasar
que se esté borrando una entrada mientras otra operación lee el
directorio. El `Event` sirve para avisar que el estado cambió (la
operación terminó) sin hacer espera activa. El `time.sleep(1)` en el
trabajador es solo para que se alcance a ver en pantalla el intercambio de
mensajes entre los dos hilos.

## Contenido del disco de muestra

La imagen `fiunamfs.img` que dejó el profesor tiene la etiqueta
**"Disco de Gunnar"**, clusters de 2048 bytes, un directorio de 4
clusters y 720 clusters en total. Contiene tres archivos:

| Archivo       | Tamaño (bytes) | Cluster inicial | Qué es |
|---------------|---------------:|----------------:|--------|
| `README.org`  | 31,126         | 6               | El planteamiento del proyecto (igual al `README.org` de `proyectos/1`). |
| `logo.png`    | 126,423        | 22              | El escudo de la Facultad de Ingeniería. |
| `mensaje.jpg` | 254,484        | 84              | Una foto con un letrero que dice: *"¡Muy bien hecho! Lograste recuperar la información del sistema de archivos FiUNAMFS. ¡Sigue adelante! :-)"* |

## Limitaciones

- Al borrar no se desfragmenta el disco, así que con muchas copias y
  borrados puede haber espacio libre pero no contiguo para un archivo
  grande. En ese caso el programa avisa que no hay espacio contiguo.
- Los nombres se comparan tal cual (distingue mayúsculas y minúsculas).
