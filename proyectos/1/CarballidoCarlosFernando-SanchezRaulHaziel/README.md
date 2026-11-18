# Proyecto: (Micro) sistema de archivos multihilos — FiUnamFS

**Materia:** Sistemas Operativos  
**Profesor:** Gunnar Eyal Wolf Iszaevich  
**Grupo:** 7  
**Integrantes:**
- Carlos Fernando Carballido Carrillo
- Raúl Haziel Sánchez Soperanes

**Entrega:** 19 de noviembre de 2026

## Objetivo

Desarrollar en Python 3 un programa que permita consultar, copiar y eliminar archivos de un volumen FiUnamFS, utilizando al menos dos hilos de ejecución y mecanismos de sincronización.

## Primer avance: 14 de noviembre de 2026

En esta primera etapa implementamos la creación de una imagen de prueba y la validación del superbloque.

El programa `preparar_imagen.py` permite:

- Crear una imagen de 1,440 KiB sin sobrescribir una existente.
- Escribir el identificador `FiUnamFS` y la versión `27-1`.
- Registrar las dimensiones del volumen mediante enteros de 32 bits en formato little-endian.
- Inicializar las 128 entradas del directorio como vacías.
- Comprobar que los datos principales del superbloque sean correctos.

## Entorno y ejecución

**Lenguaje:** Python 3  
**Entorno:** Ubuntu/Linux, probado mediante WSL.  
**Dependencias:** únicamente módulos de la biblioteca estándar de Python.

Para generar y validar la imagen de prueba:

```bash
python3 preparar_imagen.py
```

La ejecución crea el archivo `fiunamfs_prueba.img` y muestra los datos del superbloque.

Si la imagen ya existe, el programa no la sobrescribe.

## Estado del proyecto

La creación y validación básica del volumen ya fueron probadas satisfactoriamente.

Las funciones de lectura del directorio, extracción, incorporación, eliminación, interfaz y sincronización entre hilos se desarrollarán en los siguientes avances.

Este programa es una herramienta preliminar de preparación y prueba, no el administrador FiUnamFS completo.

## Segundo avance: 15 de noviembre de 2026

En esta etapa implementamos la lectura del directorio de FiUnamFS mediante el programa `listar_directorio.py`.

El programa valida el superbloque y recorre las entradas de 64 bytes del directorio, identificando cuáles corresponden a archivos. Para cada archivo muestra su nombre, tamaño, clúster inicial, fecha de creación y fecha de última modificación.

La imagen se abre en modo de solo lectura para evitar modificaciones accidentales.

### Ejecución

Desde la carpeta del equipo, podemos consultar la imagen proporcionada en el repositorio:

```bash
python3 listar_directorio.py ../fiunamfs.img
```

También podemos utilizar cualquier otra imagen compatible indicando su ruta.

### Pruebas realizadas

Probamos el programa con dos imágenes.

**Imagen vacía:** el programa identificó las 128 entradas del directorio y mostró cero archivos.

**Imagen proporcionada por el profesor:** identificó correctamente tres archivos:

| Archivo | Tamaño | Clúster inicial |
|---|---:|---:|
| README.org | 31126 bytes | 6 |
| logo.png | 126423 bytes | 22 |
| mensaje.jpg | 254484 bytes | 84 |

Los tres registran como fecha de creación y modificación el 5 de noviembre de 2026, a las 16:31:24.

Con estas pruebas comprobamos que el programa puede interpretar el directorio y consultar sus archivos sin modificar el volumen.

La extracción, incorporación y eliminación de archivos, así como la sincronización entre hilos, permanecen pendientes para los siguientes avances.

## Tercer avance: 17 de noviembre de 2026

En esta etapa implementamos la extracción de archivos desde FiUnamFS hacia el sistema operativo anfitrión mediante `extraer_archivo.py`.

El programa utiliza las funciones de lectura y validación desarrolladas anteriormente. Primero localiza el archivo solicitado dentro del directorio, después calcula su desplazamiento a partir del clúster inicial y finalmente copia la cantidad exacta de bytes indicada por su tamaño.

La imagen se abre en modo de solo lectura y el programa evita sobrescribir archivos existentes en el destino.

### Ejecución

Desde la carpeta del proyecto:

```bash
python3 extraer_archivo.py ../fiunamfs.img README.org /tmp/fiunamfs_readme_extraido.org
```

### Pruebas realizadas

Utilizamos la imagen de referencia proporcionada por el profesor y extrajimos sus tres archivos:

| Archivo | Tamaño extraído |
|---|---:|
| README.org | 31126 bytes |
| logo.png | 126423 bytes |
| mensaje.jpg | 254484 bytes |

Posteriormente comparamos los bytes extraídos con los almacenados en la imagen FiUnamFS. Las tres comparaciones fueron idénticas.

Con esto comprobamos la extracción de archivos de texto e imágenes sin alterar el contenido del volumen.

Las operaciones de incorporación y eliminación de archivos, así como la sincronización entre hilos, continúan pendientes.

## Cuarto avance: incorporación y eliminación de archivos

**Fecha:** 17 de noviembre de 2026  
**Responsable de este avance:** Raúl Haziel Sánchez Soperanes.

En esta etapa implementamos las operaciones de incorporación y eliminación de archivos dentro de FiUnamFS.

### Eliminación de archivos

El programa `eliminar_archivo.py` busca el archivo solicitado en el directorio y marca su entrada como disponible.

Esta operación no borra físicamente el contenido almacenado en los clústeres, pero permite que posteriormente se reutilice ese espacio.

### Incorporación de archivos

El programa `agregar_archivo.py` permite copiar archivos desde el sistema operativo anfitrión hacia la imagen FiUnamFS.

Para realizarlo:

1. Comprueba que el nombre no exista previamente.
2. Busca una entrada libre en el directorio.
3. Identifica los clústeres ocupados.
4. Encuentra espacio libre contiguo.
5. Escribe el contenido y registra los datos del archivo en el directorio.

### Pruebas realizadas

Trabajamos sobre una copia de la imagen proporcionada por el profesor para evitar modificar el archivo original.

Primero eliminamos `logo.png` y comprobamos que el directorio pasara de tres archivos a dos.

Después incorporamos `haziel.txt`, un archivo de 3700 bytes. El programa utilizó dos clústeres consecutivos comenzando en el clúster 22, anteriormente ocupado por `logo.png`.

También realizamos las siguientes comprobaciones:

- Los archivos `README.org` y `mensaje.jpg` conservaron su contenido original.
- La eliminación de un archivo inexistente produjo un mensaje de error.
- El archivo incorporado pudo extraerse correctamente.
- El contenido extraído de `haziel.txt` resultó idéntico al archivo original mediante `cmp`.
- El programa rechazó el intento de incorporar un archivo con nombre duplicado.

### Ejecución

Para agregar un archivo:

```bash
python3 agregar_archivo.py /ruta/fiunamfs_trabajo.img /ruta/haziel.txt
```

Para eliminar un archivo:

```bash
python3 eliminar_archivo.py /ruta/fiunamfs_trabajo.img haziel.txt
```

**Nota:** las operaciones de escritura deben probarse sobre una copia de la imagen. La sincronización entre hilos queda pendiente para el siguiente avance.

## Quinto avance: interfaz multihilos y sincronización

**Fecha:** 18 de noviembre de 2026.  
**Responsable del avance:** Raúl Haziel Sánchez Soperanes.

En esta etapa integramos las operaciones principales de FiUnamFS en una interfaz de texto mediante el programa `fiunamfs.py`.

### Funcionamiento

El programa utiliza dos hilos trabajadores creados con la biblioteca `threading` de Python.

El hilo principal recibe las instrucciones del usuario y las coloca en una cola compartida (`Queue`). Los hilos trabajadores obtienen las tareas y ejecutan las operaciones correspondientes.

Para evitar que ambos hilos accedan simultáneamente a la imagen FiUnamFS, utilizamos un candado `RLock`.

También utilizamos `Event` para esperar la finalización de las tareas y `Barrier` para coordinar el inicio de ambos trabajadores durante la prueba de concurrencia.

### Menú de operaciones

El programa permite:

1. Listar los archivos del directorio.
2. Extraer archivos hacia el sistema anfitrión.
3. Incorporar archivos a FiUnamFS.
4. Eliminar archivos del directorio.
5. Ejecutar una prueba de concurrencia.
0. Salir del programa.

### Ejecución

Desde la carpeta del equipo, se recomienda utilizar una copia de la imagen original:

```bash
cp ../fiunamfs.img fiunamfs_trabajo.img
python3 fiunamfs.py fiunamfs_trabajo.img
```

### Pruebas realizadas

Ejecutamos el menú interactivo y comprobamos el listado de archivos.

Después, utilizamos la opción de concurrencia, que ejecuta tareas de lectura y escritura mediante dos hilos sobre una copia temporal de la imagen.

Durante la prueba:

- Se incorporó `HILOS.TXT`, de 5100 bytes.
- El archivo utilizó tres clústeres, comenzando en el clúster 24.
- Ambos hilos participaron en la ejecución de operaciones.
- El archivo pudo extraerse correctamente.
- El contenido recuperado resultó idéntico al original.
- La imagen de trabajo no fue modificada por la prueba de concurrencia.
- Ambos hilos finalizaron correctamente al cerrar el programa.

Las operaciones sobre la imagen se ejecutaron bajo protección del candado, evitando accesos simultáneos durante su ejecución.
