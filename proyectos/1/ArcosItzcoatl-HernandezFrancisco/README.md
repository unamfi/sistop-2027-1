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

Actualmente, la implementación permite validar imágenes FiUnamFS 27-1, consultar su directorio, exportar archivos hacia el sistema operativo, importar archivos locales y eliminar archivos del volumen. Para las pruebas de escritura se utilizan imágenes de prueba, conservando la imagen original proporcionada por el profesor.

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
| `fiunamfs.py` | Lectura, validación, exportación, importación y eliminación de archivos |
| `main.py` | Interfaz de consola para listar, importar, exportar y eliminar archivos |
| `pruebas/crear_imagen_demo.py` | Generación de una imagen artificial |
| `pruebas/test_lectura.py` | Pruebas de lectura y validación |
| `pruebas/test_exportacion.py` | Pruebas de exportación e integridad |
| `pruebas/test_importacion.py` | Pruebas de importación y asignación de espacio |
| `pruebas/test_eliminacion.py` | Pruebas de eliminación y reutilización de clusters |
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

La exportación permite copiar un archivo almacenado en FiUnamFS hacia una carpeta de la computadora.

Primero se localiza el archivo en el directorio. Después, a partir del cluster inicial y el tamaño registrado, se calcula su posición dentro de la imagen.

Mediante `seek()` se establece la posición de lectura y con `read()` se recupera exactamente la cantidad de bytes correspondiente al archivo.

Finalmente, el contenido se escribe en un nuevo archivo utilizando el modo binario `xb`, que impide sobrescribir un archivo existente.

Durante esta operación, la imagen FiUnamFS se mantiene en modo de lectura.

### Importación de archivos

La importación permite incorporar archivos de la computadora al sistema FiUnamFS.

Antes de realizar la escritura, el programa verifica que el archivo exista, que su nombre cumpla las restricciones del sistema y que no se encuentre registrado previamente en el directorio.

Posteriormente, calcula la cantidad de clusters necesarios de acuerdo con el tamaño del archivo y busca una secuencia de clusters libres y contiguos.

Una vez encontrado el espacio disponible, prepara los datos del archivo y una entrada de directorio de 64 bytes que contiene su nombre, tamaño, cluster inicial y fechas de creación y modificación.

Para reducir el riesgo de corrupción, las modificaciones se realizan primero sobre una imagen temporal. Después de validar su estructura, esta reemplaza a la imagen de trabajo.

Este procedimiento permite incorporar archivos sin sobrescribir los clusters utilizados por otros archivos existentes.

### Eliminación de archivos

La eliminación permite retirar un archivo del directorio de FiUnamFS y liberar el espacio que tenía asignado.

Primero se busca el archivo solicitado dentro del directorio. Si no existe, el programa rechaza la operación sin modificar la imagen.

Cuando se encuentra el archivo, se localiza su entrada de 64 bytes y se marca como disponible mediante el carácter `-` y la marca correspondiente a una entrada libre.

La eliminación es lógica, por lo que no es necesario borrar físicamente los datos almacenados en los clusters. Al desaparecer el registro del directorio, estos clusters dejan de considerarse ocupados y pueden reutilizarse en futuras importaciones.

Al igual que en la importación, los cambios se realizan sobre una imagen temporal que se valida antes de reemplazar la imagen de trabajo.

Este procedimiento permite eliminar archivos y recuperar espacio sin modificar los registros de los demás archivos existentes.

## 4. Ejecución del programa

El proyecto utiliza Python y bibliotecas estándar del lenguaje, por lo que no requiere instalar paquetes adicionales mediante `pip`.

**Entorno utilizado:**
- Windows 11
- Python 3.13.15
- Git Bash
- Visual Studio Code

### Lectura del directorio

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

### Exportación de archivos

Primero se prepara la carpeta de salida:

```bash
mkdir -p salidas
```

Posteriormente se ejecuta:

```bash
py main.py fiunamfs_prueba.img --exportar logo.png --destino salidas/logo.png
```

El archivo se almacena en la carpeta `salidas`. Si ya existe otro archivo con ese nombre, la operación se rechaza para evitar sobrescribirlo.

### Importación de archivos

Para probar la importación se utiliza una imagen artificial:

```bash
py pruebas/crear_imagen_demo.py demo_importacion.img
```

Se crea un archivo de texto:

```bash
printf "Prueba de importacion\n" > salidas/EJEMPLO.TXT
```

Después se incorpora a FiUnamFS:

```bash
py main.py demo_importacion.img --importar salidas/EJEMPLO.TXT
```

Para comprobar que aparece en el directorio:

```bash
py main.py demo_importacion.img
```

El programa muestra el nombre, tamaño, cluster inicial y fechas del archivo importado. Si se intenta importar nuevamente el mismo nombre, se rechaza la operación para evitar duplicados.

### Eliminación de archivos

Para probar la eliminación se utiliza una imagen artificial independiente:

```bash
py pruebas/crear_imagen_demo.py demo_eliminacion.img
```

Se crea el archivo que será eliminado:

```bash
printf "Contenido que vamos a eliminar\n" > salidas/BORRAR.TXT
```

Después se incorpora al sistema de archivos:

```bash
py main.py demo_eliminacion.img --importar salidas/BORRAR.TXT
```

Para eliminarlo:

```bash
py main.py demo_eliminacion.img --eliminar BORRAR.TXT
```

Finalmente, se consulta nuevamente el directorio:

```bash
py main.py demo_eliminacion.img
```

El archivo eliminado ya no aparece en el listado. Los archivos restantes continúan registrados y el espacio liberado queda disponible para futuras importaciones.

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

### Resultados de importación

Para comprobar la escritura se utilizó una imagen artificial que inicialmente contenía dos archivos: `HOLA.TXT` y `DATOS.BIN`.

Posteriormente se incorporaron dos archivos de texto desde Windows:

| Archivo | Tamaño (bytes) | Cluster asignado |
|---|---:|---:|
| PRUEBA.TXT | 36 | 7 |
| NUEVO.TXT | 30 | 8 |

Después de ambas importaciones, el directorio contenía cuatro archivos. Los archivos originales permanecieron registrados en sus clusters correspondientes.

También se verificó la integridad de `NUEVO.TXT` mediante una prueba de importación y exportación. El archivo recuperado fue comparado con el original utilizando `cmp` y SHA-256, obteniendo resultados idénticos.

Las pruebas adicionales permitieron comprobar el comportamiento del programa ante archivos duplicados, nombres inválidos, archivos vacíos, falta de espacio y directorios llenos.

### Resultados de eliminación

Para comprobar la eliminación se utilizó una imagen artificial que inicialmente contenía `HOLA.TXT` y `DATOS.BIN`, almacenados en los clusters 5 y 6, respectivamente.

Posteriormente se incorporó `BORRAR.TXT`, de 31 bytes, al cluster 7.

Al ejecutar la eliminación, el programa retiró su entrada del directorio. Una nueva consulta mostró únicamente los archivos originales:

| Archivo | Tamaño (bytes) | Cluster inicial |
|---|---:|---:|
| HOLA.TXT | 21 | 5 |
| DATOS.BIN | 256 | 6 |

Para comprobar la reutilización del espacio se importó `NUEVO.TXT`, de 30 bytes. El programa volvió a asignar el cluster 7, que había sido liberado al eliminar `BORRAR.TXT`.

Finalmente, también se comprobó la eliminación de `NUEVO.TXT` desde la interfaz de consola, verificando nuevamente que solo permanecieran los dos archivos originales.

Las pruebas adicionales comprobaron que no se modifica la imagen al intentar eliminar archivos inexistentes o previamente eliminados, que los archivos restantes conservan su contenido y que el tamaño total del disco permanece sin cambios.

### Pruebas automáticas

Para comprobar el funcionamiento del programa se utilizó el módulo `unittest` de Python.

Se ejecutaron **33 pruebas automáticas**, divididas de la siguiente manera:

- **12 pruebas de lectura y validación:** interpretación del superbloque, lectura del directorio, nombres, fechas, límites del disco y detección de clusters superpuestos.

- **5 pruebas de exportación:** extracción de archivos binarios y de texto, manejo de archivos inexistentes, prevención de sobrescrituras y conservación de la imagen original.

- **10 pruebas de importación:** incorporación de archivos de texto y binarios, archivos vacíos, nombres inválidos o duplicados, espacio insuficiente, directorio lleno y preservación de los archivos existentes.

- **6 pruebas de eliminación:** eliminación de archivos, reutilización de clusters, manejo de archivos inexistentes, rechazo de una segunda eliminación, conservación de los datos existentes y verificación del tamaño del disco.

Las pruebas se ejecutaron mediante:

```bash
py -m unittest discover -s pruebas -v
```

**Resultado obtenido:**

```text
Ran 33 tests in 1.303s

OK
```

Todas las pruebas finalizaron correctamente, sin errores ni fallos.

## 6. Referencia

Especificación oficial del proyecto FiUnamFS, Sistemas Operativos 2027-1, Facultad de Ingeniería, UNAM.

https://github.com/unamfi/sistop-2027-1/blob/main/proyectos/1/README.org