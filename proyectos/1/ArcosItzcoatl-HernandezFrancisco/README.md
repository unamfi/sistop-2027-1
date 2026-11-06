# FiUnamFS 27-1 — Proyecto final de Sistemas Operativos

**Universidad:** Universidad Nacional Autónoma de México  
**Facultad:** Facultad de Ingeniería  
**Asignatura:** Sistemas Operativos 2027-1  
**Profesor:** Gunnar Wolf

**Integrantes:**
- Itzcoatl Ayax Arcos Garduño
- Francisco Hernández Moguel

## 1. Descripción del proyecto

El proyecto consiste en desarrollar un programa en Python capaz de interpretar y administrar el sistema de archivos FiUnamFS, proporcionado como parte de la asignatura de Sistemas Operativos.

FiUnamFS simula una unidad de almacenamiento de 1,440 KiB mediante un archivo binario. Su estructura incluye un superbloque, un directorio plano y una región destinada al almacenamiento de archivos.

El programa completo deberá permitir consultar, copiar, incorporar y eliminar archivos, además de utilizar hilos de ejecución y mecanismos de sincronización.

Actualmente, la implementación permite validar imágenes FiUnamFS 27-1, consultar su directorio y exportar archivos hacia el sistema operativo sin modificar la imagen original.

## 2. Estructura del sistema de archivos

FiUnamFS utiliza sectores de 512 bytes y clusters de cuatro sectores, equivalentes a 2,048 bytes.

La organización del disco es la siguiente:

| Región | Ubicación | Descripción |
|---|---|---|
| Superbloque | Cluster 0 | Identificación, versión y características del sistema |
| Directorio | Clusters 1 al 4 | Información de los archivos almacenados |
| Datos | Clusters 5 al 719 | Contenido de los archivos |

El directorio contiene 128 entradas de 64 bytes. Cada entrada registra el nombre del archivo, su tamaño, el cluster inicial y las fechas de creación y modificación.

Los archivos se almacenan mediante asignación contigua, por lo que ocupan secuencias consecutivas de clusters.

## 3. Organización y funcionamiento del programa

El proyecto se encuentra dividido en los siguientes archivos:

| Archivo | Función |
|---|---|
| `fiunamfs.py` | Lectura, validación del sistema de archivos y exportación |
| `main.py` | Interfaz de consola para listar y extraer archivos |
| `pruebas/crear_imagen_demo.py` | Generación de una imagen artificial |
| `pruebas/test_lectura.py` | Pruebas de lectura y validación |
| `pruebas/test_exportacion.py` | Pruebas de exportación e integridad |
| `.gitignore` | Exclusión de archivos temporales y de prueba |

Esta organización mantiene la lógica del sistema de archivos separada de la interfaz de consola y las pruebas.

### Lectura del superbloque

El programa comienza leyendo el primer cluster del disco y comprobando que su identificador corresponda a `FiUnamFS` y su versión a `27-1`.

Para interpretar los valores numéricos se utiliza el módulo `struct` de Python, con el formato `<I`, correspondiente a enteros sin signo de 32 bits en orden *little endian*.

También se comprueban las características del disco, como el tamaño de cluster y el número total de clusters.

### Lectura del directorio

Después de validar el superbloque, el programa examina las entradas del directorio para identificar los archivos existentes.

Durante la lectura se comprueban los nombres, las fechas, los límites de almacenamiento y las posibles superposiciones entre los clusters ocupados.

### Exportación de archivos

La exportación permite copiar un archivo almacenado en FiUnamFS hacia una carpeta de Windows.

Primero se localiza el archivo en el directorio. Después, a partir del cluster inicial y el tamaño registrado, se calcula su posición dentro de la imagen.

Mediante `seek()` se establece la posición de lectura y con `read()` se recupera exactamente la cantidad de bytes correspondiente al archivo.

Finalmente, el contenido se escribe en un nuevo archivo utilizando el modo binario `xb`, que impide sobrescribir un archivo existente.

Durante esta operación, la imagen FiUnamFS se mantiene en modo de lectura.

## 4. Ejecución del programa

El proyecto utiliza Python y bibliotecas estándar del lenguaje.

**Entorno utilizado:**
- Windows 11
- Python 3.13.15
- Git Bash
- Visual Studio Code

Desde la carpeta del proyecto se puede generar una imagen artificial:

```bash
py pruebas/crear_imagen_demo.py demo_fiunamfs.img
```

Para consultar su contenido:

```bash
py main.py demo_fiunamfs.img
```

También puede utilizarse la imagen oficial proporcionada por el profesor. Para realizar las pruebas sin modificarla, se crea una copia:

```bash
cp ../fiunamfs.img fiunamfs_prueba.img
```

Para consultar su directorio:

```bash
py main.py fiunamfs_prueba.img
```

Para exportar un archivo, primero se prepara la carpeta de salida:

```bash
mkdir -p salidas
```

Posteriormente se ejecuta:

```bash
py main.py fiunamfs_prueba.img --exportar logo.png --destino salidas/logo.png
```

El archivo se almacena en la carpeta `salidas`. Si ya existe otro archivo con ese nombre, la operación se rechaza para evitar sobrescribirlo.

## 5. Resultados obtenidos

### Lectura de la imagen oficial

La lectura de la imagen proporcionada por el profesor permitió identificar el volumen denominado **Disco de Gunnar**, con los siguientes archivos:

| Nombre | Tamaño (bytes) | Cluster inicial |
|---|---:|---:|
| README.org | 31,126 | 6 |
| logo.png | 126,423 | 22 |
| mensaje.jpg | 254,484 | 84 |

Los archivos presentan la fecha de creación y modificación `20261105163124`, correspondiente al 5 de noviembre de 2026 a las 16:31:24.

### Resultados de exportación

Se realizaron exportaciones de `logo.png` y `mensaje.jpg`, obteniendo archivos de 126,423 y 254,484 bytes, respectivamente.

Ambos archivos pudieron recuperarse desde la imagen FiUnamFS. Además, se comparó byte por byte el contenido extraído de `logo.png` con la información almacenada en el disco, obteniendo una coincidencia exacta.

### Pruebas automáticas

Para comprobar el funcionamiento del programa se utilizó el módulo `unittest` de Python.

Se ejecutaron **17 pruebas automáticas**, divididas de la siguiente manera:

- **12 pruebas de lectura y validación:** comprueban la interpretación del superbloque, la lectura del directorio, las fechas, los nombres, los límites del disco y la detección de clusters superpuestos.
- **5 pruebas de exportación:** verifican la extracción de archivos binarios y de texto, el manejo de archivos inexistentes, la prevención de sobrescrituras y la conservación de la imagen original.

Las pruebas se ejecutaron con:

```bash
py -m unittest discover -s pruebas -v
```

**Resultado obtenido:**

```text
Ran 17 tests in 2.377s

OK
```


Todas las pruebas finalizaron correctamente, sin errores ni fallos.

## 6. Referencia

Especificación oficial del proyecto FiUnamFS, Sistemas Operativos 2027-1, Facultad de Ingeniería, UNAM.

https://github.com/unamfi/sistop-2027-1/blob/main/proyectos/1/README.org