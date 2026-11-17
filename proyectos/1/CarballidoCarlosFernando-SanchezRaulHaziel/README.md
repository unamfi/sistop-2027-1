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
