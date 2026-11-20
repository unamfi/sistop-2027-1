# FiUnamFS

**Autor:** Perez Baez Jessica Estefani

**Lenguaje:** Python

**Versión utilizada:** Python 3.15.2

## ¿De qué trata el proyecto?

En este proyecto estoy trabajando con Python para crear un programa que permita realizar diferentes operaciones con FiUnamFS.

La idea es poder consultar los archivos que contiene el disco, copiar archivos desde FiUnamFS a la computadora, agregar archivos desde la computadora al disco y también eliminarlos.

Además, como parte de la práctica, estoy trabajando con varios hilos para que las operaciones se puedan ejecutar mediante un hilo trabajador y otro que se encarga de recibir los cambios de estado.

Para organizar mejor el trabajo, fui separando el código en diferentes archivos, de manera que cada uno se encargue de una parte del programa.

Durante el desarrollo también he realizado mejoras para validar la imagen del disco, revisar las entradas del directorio, controlar el espacio disponible y evitar problemas al momento de copiar o agregar archivos.

## Archivos y carpetas

- **main.py:** es donde comienza el programa. Aquí se muestra el menú y se selecciona la operación que se quiere realizar.
- **filesystem.py:** se encarga de abrir la imagen del disco y revisar sus datos principales para comprobar que corresponda a FiUnamFS.
- **directory.py:** permite leer el directorio, mostrar los archivos que contiene y obtener información sobre ellos. También revisa las entradas, detecta nombres duplicados y controla las posiciones al escribir.
- **operations.py:** contiene las operaciones para copiar archivos desde FiUnamFS a la computadora, agregar archivos al disco y eliminarlos. También realiza comprobaciones de espacio, clústeres ocupados y escritura de datos.
- **threads.py:** contiene la parte relacionada con los hilos. Tiene un hilo trabajador que realiza las operaciones y otro que recibe los cambios de estado.
- **disco/:** aquí se guardan las imágenes del disco que utiliza el programa.
- **archivos/:** aquí se guardan los archivos que se copian desde FiUnamFS a la computadora y los archivos que se utilizan para realizar pruebas.

## Requisitos

Para ejecutar el proyecto se necesita:

- Tener Python instalado.
- Se desarrolló y probó utilizando Python 3.15.2.
- Tener la imagen de FiUnamFS proporcionada para la práctica.
- Contar con una terminal para ejecutar el programa.

No se necesitan instalar librerías externas, ya que se utilizan módulos que vienen incluidos con Python, como `os`, `threading`, `queue`, `datetime`, `math` y `tempfile`.

## ¿Cómo ejecutar el programa?

Primero hay que descargar o clonar el repositorio.

Después, abrir la carpeta del proyecto desde VS Code o una terminal.

### 1. Preparar la imagen del disco

Este paso es importante porque las imágenes `.img` no están incluidas en el repositorio.

El archivo `.gitignore` ignora las imágenes que se encuentran dentro de `disco/`, por lo que al clonar el proyecto esa carpeta puede no contener la imagen necesaria.

Se debe conseguir la imagen proporcionada por el profesor y colocarla dentro de la carpeta `disco/`.

El programa utiliza por defecto el siguiente nombre:

`fiunamfs.img`

También se puede utilizar una imagen con otro nombre, indicando su ubicación al ejecutar el programa.

### 2. Abrir la terminal

Hay que asegurarse de estar dentro de la carpeta principal del proyecto, donde se encuentra `main.py`.

### 3. Ejecutar el programa

Si la imagen se llama `fiunamfs.img`, escribir:

```powershell
py main.py
```

También se puede ejecutar con:

```powershell
python main.py
```

Si se quiere utilizar una imagen con otro nombre, como la que utilicé para las pruebas, se puede indicar su ruta:

```powershell
py main.py "disco/fiunamfs prueba.img"
```

Si todo está en su lugar, el programa revisará la imagen del disco y mostrará el menú principal.

## Opciones del programa

Al ejecutar el programa aparece un menú con cinco opciones:

1. **Mostrar contenido del directorio:** permite consultar los archivos que se encuentran dentro de FiUnamFS, mostrando su nombre, tamaño, clúster inicial y fechas.
2. **Copiar archivo de FiUnamFS a la computadora:** permite escribir el nombre de un archivo que se encuentra en el disco para copiarlo a la carpeta `archivos/`.
3. **Copiar archivo de la computadora a FiUnamFS:** permite agregar un archivo que se encuentre en la computadora. Para esto se debe proporcionar su ruta.
4. **Eliminar archivo de FiUnamFS:** permite escribir el nombre de un archivo para eliminarlo del disco.
5. **Salir:** cierra el programa y finaliza los hilos.

## ¿Cómo se utilizan los hilos?

Para cumplir con la parte de concurrencia de la práctica, se agregaron dos hilos.

El primero se llama **hilo trabajador**. Es el encargado de realizar las operaciones que se solicitan desde el menú, como copiar archivos, agregarlos o eliminarlos.

El segundo se llama **hilo supervisor**. Su función es recibir los mensajes que indican cuándo comienza una operación, cuándo termina o si ocurrió algún error.

Para que puedan comunicarse se utilizan colas (`Queue`). El trabajador envía los cambios de estado y el supervisor los recibe.

También se utiliza `threading.Event` para avisar al menú cuando una operación terminó. De esta manera, el menú puede esperar el resultado antes de continuar.

Además, se utiliza un bloqueo compartido (`RLock`) en el acceso al disco para evitar que dos hilos lean o modifiquen la imagen al mismo tiempo de manera incorrecta.

Los mensajes del supervisor se guardan en una cola y después se muestran desde `main.py`. Esto ayuda a que no se mezclen con el contenido del directorio o con las opciones del menú.

## Contenido del disco utilizado en las pruebas

La imagen proporcionada para la práctica contiene originalmente tres archivos:

| Archivo | Tamaño | Clúster inicial | Contenido |
|---|---:|---:|---|
| README.org | 31,126 bytes | 6 | Planteamiento del proyecto y descripción de la práctica. |
| logo.png | 126,423 bytes | 22 | Escudo de la Facultad de Ingeniería. |
| mensaje.jpg | 254,484 bytes | 84 | Fotografía que contiene el mensaje «¡Muy bien hecho!». |

Estos archivos forman parte del contenido original de la imagen y permiten identificar la información almacenada en el disco.

Durante las pruebas utilicé una copia de la imagen original para evitar modificar el disco proporcionado.

## Algunas pruebas que he realizado

Durante el desarrollo he estado probando las diferentes opciones para comprobar que funcionen correctamente.

Entre las pruebas realizadas están:

- Mostrar los archivos que contiene el directorio.
- Copiar archivos desde FiUnamFS a la computadora.
- Agregar archivos desde la computadora al disco.
- Eliminar archivos y comprobar que ya no aparezcan en el directorio.
- Agregar y copiar un archivo vacío.
- Intentar agregar un archivo con un nombre demasiado largo.
- Intentar agregar un archivo que ya existe.
- Intentar eliminar o copiar archivos que no se encuentran en el disco.
- Comprobar que se pueda volver a utilizar el espacio de un archivo eliminado.
- Revisar los mensajes que se envían entre los dos hilos.
- Comprobar que los hilos finalicen correctamente al cerrar el programa.

### Pruebas realizadas con las últimas modificaciones

Después de realizar modificaciones en `directory.py`, `main.py`, `threads.py` y `operations.py`, volví a ejecutar el programa utilizando la imagen de prueba `fiunamfs prueba.img`.

Los resultados obtenidos fueron:

- **Validación de la imagen:** el programa reconoció correctamente la firma FiUnamFS, la versión 27-1, el tamaño de clúster de 2048 bytes, los cuatro clústeres del directorio y los 720 clústeres totales.
- **Consulta del directorio:** se mostraron correctamente los archivos registrados en la imagen.
- **Agregar archivos:** se agregaron archivos de prueba desde la computadora hacia FiUnamFS.
- **Extracción de archivos:** se copiaron archivos desde FiUnamFS hacia la computadora y se verificó que el contenido coincidiera con los datos leídos del disco.
- **Detección de duplicados:** se comprobó que el sistema impide agregar un archivo cuando ya existe otro con el mismo nombre.
- **Eliminación lógica:** se eliminó un archivo y se comprobó que desapareciera del directorio.
- **Reutilización de espacio:** después de eliminar `tercero.txt`, que ocupaba el clúster 209, se agregó `cuarto.txt` y el sistema volvió a asignarle el clúster 209.
- **Archivos vacíos:** se comprobó que un archivo vacío puede registrarse y ocupar un clúster.
- **Funcionamiento de los hilos:** el hilo trabajador y el supervisor iniciaron correctamente, comunicaron el inicio y la finalización de las operaciones y terminaron correctamente al salir del programa.

También se realizó una comprobación mediante SHA-256 para comparar el archivo extraído con los datos almacenados en la imagen. Ambos contenidos coincidieron.

Para estas pruebas utilicé una copia de la imagen del disco, para no modificar la imagen original proporcionada.

## Archivos utilizados para las pruebas

Durante el desarrollo se crearon algunos archivos temporales, por ejemplo:

- `prueba.txt`
- `vacio.txt`
- `segundo.txt`
- `tercero.txt`
- `cuarto.txt`
- `archivo_demasiado_largo.txt`

Estos archivos se utilizaron para probar las operaciones del programa y no forman parte del contenido original de FiUnamFS.

Los archivos que se extraen del disco se guardan dentro de `archivos/`.

No es necesario incluir estos archivos temporales en el repositorio para ejecutar el proyecto.

