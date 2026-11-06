# FiUnamFS 27-1 — Proyecto final de Sistemas Operativos

**Universidad:** Universidad Nacional Autónoma de México  
**Facultad:** Facultad de Ingeniería  
**Asignatura:** Sistemas Operativos 2027-1  
**Profesor:** Gunnar Wolf

**Integrantes:**
- Itzcoatl Ayax Arcos Garduño
- Francisco Hernández Moguel

## 1. Descripción del proyecto

El proyecto consiste en desarrollar un programa en Python capaz de interpretar y administrar un sistema de archivos denominado FiUnamFS, proporcionado como parte de la asignatura de Sistemas Operativos.

FiUnamFS simula una unidad de almacenamiento de 1,440 KiB mediante un archivo binario. Su estructura incluye un superbloque, un directorio plano y una región destinada al almacenamiento de archivos.

El programa completo deberá permitir consultar, copiar, incorporar y eliminar archivos, además de utilizar hilos de ejecución y mecanismos de sincronización.

La implementación actual permite leer y validar el sistema de archivos, así como mostrar el contenido de su directorio.

## 2. Estructura del sistema de archivos

FiUnamFS utiliza sectores de 512 bytes y clusters de cuatro sectores, equivalentes a 2,048 bytes.

La organización del disco es la siguiente:

| Región | Ubicación | Descripción |
|---|---|---|
| Superbloque | Cluster 0 | Identificación, versión y características del sistema |
| Directorio | Clusters 1 al 4 | Información de los archivos almacenados |
| Datos | Clusters 5 al 719 | Contenido de los archivos |

El directorio contiene 128 entradas de 64 bytes. Cada entrada registra información como el nombre del archivo, su tamaño, el cluster inicial y las fechas de creación y modificación.

Los archivos se almacenan utilizando asignación contigua, por lo que cada archivo ocupa una secuencia consecutiva de clusters.

## 3. Organización del programa

El proyecto se encuentra dividido en los siguientes archivos:

| Archivo | Función |
|---|---|
| `fiunamfs.py` | Lectura de estructuras binarias, validaciones e interpretación del directorio |
| `main.py` | Ejecución del programa y presentación de la información |
| `pruebas/crear_imagen_demo.py` | Generación de una imagen de prueba |
| `pruebas/test_lectura.py` | Pruebas automáticas de lectura y validación |
| `.gitignore` | Exclusión de archivos temporales e imágenes de prueba |

Esta separación permite mantener la lógica del sistema de archivos independiente de la presentación de resultados.

### Lectura del superbloque

El programa comienza leyendo el primer cluster del disco y comprobando que su identificador sea `FiUnamFS` y su versión sea `27-1`.

Para interpretar los valores numéricos se utiliza el módulo `struct` de Python, específicamente el formato `<I`, que representa enteros sin signo de 32 bits en orden *little endian*.

También se comprueban las características físicas del disco, como el tamaño de cluster y el número total de clusters.

### Lectura del directorio

Después de validar el superbloque, el programa examina las entradas del directorio e identifica los archivos existentes.

Durante este proceso se realizan comprobaciones para detectar nombres incorrectos, fechas inválidas, posiciones fuera de los límites del disco y clusters ocupados por más de un archivo.

Estas validaciones permiten identificar inconsistencias antes de utilizar la información almacenada.

## 4. Ejecución del programa

El programa fue desarrollado en Python y utiliza bibliotecas estándar del lenguaje.

**Entorno utilizado:**
- Windows 11
- Python 3.13.15
- Git Bash
- Visual Studio Code

Desde la carpeta del proyecto, se puede generar una imagen artificial para realizar pruebas:

```bash
py pruebas/crear_imagen_demo.py demo_fiunamfs.img
```

Para consultar su contenido:

```bash
py main.py demo_fiunamfs.img
```

También se puede utilizar la imagen proporcionada por el profesor, ubicada en el directorio superior.

Primero se crea una copia para las pruebas:

```bash
cp ../fiunamfs.img fiunamfs_prueba.img
```

Posteriormente se ejecuta:

```bash
py main.py fiunamfs_prueba.img
```

En esta versión, la imagen se abre en modo lectura binaria (`rb`), por lo que el programa no modifica su contenido.

## 5. Resultados obtenidos

La lectura de la imagen oficial permitió identificar el volumen denominado **Disco de Gunnar**, que contiene los siguientes archivos:

| Nombre | Tamaño (bytes) | Cluster inicial |
|---|---:|---:|
| README.org | 31,126 | 6 |
| logo.png | 126,423 | 22 |
| mensaje.jpg | 254,484 | 84 |

Los tres archivos presentan la fecha de creación y modificación `20261105163124`, correspondiente al 5 de noviembre de 2026 a las 16:31:24.

La lectura se realizó correctamente y permitió identificar las ubicaciones de los archivos sin modificar el contenido de la imagen.

### Pruebas automáticas

Para comprobar el funcionamiento del programa se utilizó el módulo `unittest` de Python.

Las pruebas se ejecutaron mediante:

```bash
py -m unittest discover -s pruebas -v
```

Se realizaron **12 pruebas, todas exitosas**.

Entre las comprobaciones realizadas se encuentran:

- Lectura del superbloque y del directorio.
- Interpretación de datos binarios.
- Detección de firmas y versiones incompatibles.
- Validación de nombres y fechas.
- Detección de clusters fuera de los límites del disco.
- Identificación de archivos con nombres repetidos o clusters superpuestos.

**Resultado de la ejecución:**

```text
Ran 12 tests in 4.331s

OK
```

## 6. Referencia

Especificación oficial del proyecto FiUnamFS, Sistemas Operativos 2027-1, Facultad de Ingeniería, UNAM.

https://github.com/unamfi/sistop-2027-1/blob/main/proyectos/1/README.org