# FiUnamFS: sistema de archivos multihilos

**Autor:** López Vizcarra Ángel David  
**Asignatura:** Sistemas Operativos, semestre 2027-1  
**Proyecto:** (Micro) sistema de archivos multihilos
**Semestre:** 2027-1

El programa monta una imagen FiUnamFS mediante FUSE y permite **listar, extraer,
importar y eliminar archivos** con `ls`, `cp` y `rm`. Utiliza dos hilos comunicados
mediante colas sincronizadas. Trabaja sobre una imagen existente.

## 1. Entorno y archivos

Requiere **Linux (Ubuntu nativo o WSL2), Python 3.10+, libfuse 2.9.9,
fusepy 3.0.1, `/dev/fuse` y `fusermount`**, previamente instalados. Se desarrolló
en Ubuntu 26.04.1 LTS sobre WSL2 con CPython 3.14.4. No requiere un IDE.

| Archivo | Función |
| --- | --- |
| `fiunamfs.py` | Valida la imagen y realiza las operaciones sobre archivos. Incluye comandos directos. |
| `concurrencia.py` | Administra el trabajador, las colas de comunicación y el cierre. |
| `montar_fuse.py` | Traduce las operaciones de Linux a operaciones sobre FiUnamFS. |
| `requirements-fuse.txt` | Especifica `fusepy==3.0.1`. |
| `.gitignore` | Excluye imágenes, cachés y archivos temporales de la entrega. |

## 2. Ejemplo completo de uso

### Preparar y montar

Desde `LopezAngel`, usa una terminal de Ubuntu y el Python que tenga `fusepy`.

```bash
source ~/.venvs/fiunamfs/bin/activate
```

Define la ruta de la imagen. Dentro del repositorio sistop-2027-1 será
`../fiunamfs.img`; fuera de él, sustituye ese valor por su ruta completa.
Ejecuta las líneas sin añadir `\` al final. Los pasos se encadenan con `&&`
para detenerse si alguno falla:

```bash
IMAGEN="../fiunamfs.img"
python3 -c 'import fuse' &&
test -f "$IMAGEN" &&
TRABAJO=$(mktemp -d /tmp/fiunamfs-demo.XXXXXX) &&
cp "$IMAGEN" "$TRABAJO/prueba.img" &&
MONTAJE="$TRABAJO/montaje" &&
mkdir "$MONTAJE" &&
echo "Carpeta de trabajo: $TRABAJO" &&
python3 montar_fuse.py "$TRABAJO/prueba.img" "$MONTAJE"
```

El montaje permanece activo en esta terminal, por favor no la cierre. 

### Operar y desmontar

Abre otra terminal de Ubuntu. Copia la ruta de trabajo impresa por la primera
terminal y úsala en lugar de `XXXXXX`:

```bash
TRABAJO=/tmp/fiunamfs-demo.XXXXXX
MONTAJE="$TRABAJO/montaje"

# Listar los archivos del disco.
ls -l "$MONTAJE"

# Extraer un archivo incluido en la imagen del profesor.
cp "$MONTAJE/logo.png" "$TRABAJO/logo.png"

# Crear un archivo local e importarlo al disco.
printf 'Hola desde FiUnamFS\n' > "$TRABAJO/ejemplo.txt"
cp "$TRABAJO/ejemplo.txt" "$MONTAJE/"
ls -l "$MONTAJE"

# Extraer la copia y comprobar que conserva el contenido.
cp "$MONTAJE/ejemplo.txt" "$TRABAJO/recuperado.txt"
cmp "$TRABAJO/ejemplo.txt" "$TRABAJO/recuperado.txt"

# Eliminar únicamente el archivo de prueba dentro del disco.
rm "$MONTAJE/ejemplo.txt"
ls -l "$MONTAJE"

# Desmontar después de cerrar los archivos y salir de la carpeta montada.
fusermount -u "$MONTAJE"
```

`cmp` no imprime diferencias si las copias son idénticas. Los cambios quedan en
`$TRABAJO/prueba.img`; la imagen original permanece intacta.

### Comandos directos, sin montar

Con el disco **desmontado**, también puedes ejecutar estos comandos sustituyendo
las rutas de ejemplo:

```bash
python3 fiunamfs.py /ruta/prueba.img
python3 fiunamfs.py /ruta/prueba.img --extraer logo.png --destino /ruta/logo_extraido.png
python3 fiunamfs.py /ruta/prueba.img --importar /ruta/ejemplo.txt
python3 fiunamfs.py /ruta/prueba.img --importar /ruta/ejemplo.txt --nombre otro.txt
python3 fiunamfs.py /ruta/prueba.img --eliminar ejemplo.txt
```

La extracción directa exige un destino nuevo y la importación rechaza nombres
duplicados. En FUSE, `cp` puede sobrescribir archivos existentes.

## 3. Estrategia de implementación

La imagen tiene **720 clusters de 2048 bytes**: el cluster 0 contiene el
superbloque, del 1 al 4 está el directorio y del 5 al 719 se almacenan los datos.
El directorio tiene 128 entradas de 64 bytes. Los números son enteros de 32 bits
little endian y las fechas se guardan como `AAAAMMDDHHMMSS`.

- **Validación:** comprueba firma `FiUnamFS`, versión `27-1`, geometría, fechas y
  regiones de datos; rechaza archivos superpuestos o fuera de límites.
- **Asignación:** busca una entrada libre y el primer tramo contiguo suficiente
  (*first fit*). Reserva clusters completos y extrae solo los bytes del archivo.
- **Escritura FUSE:** reconstruye el contenido según el desplazamiento recibido,
  reasigna espacio contiguo y actualiza la fecha de modificación.
- **Eliminación:** marca la entrada con `-` y `#..............`, dejando sus
  clusters disponibles. No borra físicamente los datos anteriores.
- **Guardado:** valida los cambios en memoria, escribe y sincroniza un temporal
  con `fsync`, y reemplaza la imagen mediante `os.replace`.

## 4. Hilos y sincronización

El **hilo principal** recibe las solicitudes FUSE y las coloca en una
`queue.Queue`. El **trabajador `FiUnamFS-disco`** las procesa en orden FIFO y
devuelve los estados `iniciado`, `terminado` o `error` mediante la cola de cada
solicitud, junto con el resultado o la excepción. La espera usa `get()`, sin
consultas repetidas.

Un único trabajador completa cada operación de lectura, modificación y guardado,
evitando que dos solicitudes reserven los mismos clusters. Un `Lock` coordina el
envío con el cierre; al salir se encola `None` y se espera al trabajador con
`join()`. Los errores de operación se comunican sin detenerlo.

FUSE usa `foreground=True` y `nothreads=True`: conserva un receptor FUSE y nuestro
hilo trabajador. La sincronización es interna al proceso; no se debe modificar
la misma imagen desde otro montaje o programa mientras esté en uso.

## 5. Contenido del disco de referencia

La imagen original tiene la etiqueta **Disco de Gunnar**, mide **1 474 560 bytes**
y contiene:

| Archivo | Bytes | Cluster inicial |
| --- | ---: | ---: |
| `README.org` | 31 126 | 6 |
| `logo.png` | 126 423 | 22 |
| `mensaje.jpg` | 254 484 | 84 |

## 6. Limitaciones

Los nombres admiten hasta 15 caracteres ASCII, incluida la extensión. No hay
subdirectorios, enlaces, renombrado, permisos persistentes ni desfragmentación.
Se necesita espacio **contiguo**, aunque el total libre sea mayor.  Para eliminar archivos o desmontar,
cierra primero los archivos abiertos.

## Referencias


- [fusepy](https://github.com/fusepy/fusepy) y [libfuse](https://libfuse.github.io/doxygen/structfuse__operations.html).

