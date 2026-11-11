# Tarea 2 - Obteniendo información de un directorio

**Materia:** Sistemas Operativos  
**Integrantes:** Beatriz Almaraz y Edson Barragán  
**Lenguaje:** C++
**Fecha de entrega:** 10 de noviembre de 2026

## ¿De qué trata el programa?

Para esta tarea realizamos un programa en C++ que permite consultar los archivos que se encuentran dentro de una carpeta y mostrar cuáles han sido modificados recientemente.

La idea es que el usuario pueda indicar una ruta y una cantidad de días para que el programa busque los archivos que cumplen con ese tiempo.

Además de mostrar sus nombres, también presenta algunos datos como la fecha de modificación, los permisos y el tamaño de cada archivo.

## ¿Cómo funciona?

El programa recibe dos datos desde la terminal:

- **Ruta del directorio:** La carpeta que queremos revisar.
- **Número de días:** El tiempo que se tomará en cuenta para buscar archivos modificados recientemente.

Con estos datos, el programa revisa los archivos del directorio, consulta su información y muestra los resultados en una tabla.

Para hacerlo utilizamos algunas funciones como `opendir()`, `readdir()` y `stat()`, que nos permiten acceder al contenido de las carpetas y obtener información de los archivos.

También utilizamos `sort()` para ordenar los resultados y facilitar su lectura.

## Archivos de la tarea

- `archivosRecientes.cpp`: Contiene el código fuente del programa.
- `Capturas/`: Contiene las evidencias de las pruebas realizadas.

## ¿Cómo compilarlo?

Para compilar el programa utilizamos el compilador `g++` desde la terminal de Visual Studio Code (previamente instalado g++).

```bash
g++ archivosRecientes.cpp -o archivos_recientes.exe
```

Para el caso de un SO Linux de Ubuntu/Debian:

Se debe de contar con g++

```bash
sudo apt update
sudo apt install build-essential
```

Posteriormente se debe de entrar al directorio del programa y posterior a eso, compilar el archivo `archivosRecientes.cpp`

```bash
g++ -std=c++17 -Wall -Wextra -pedantic archivosRecientes.cpp -o archivos_recientes
```

Si todo sale bien, se genera el archivo ejecutable y ya podemos probarlo.

## ¿Cómo ejecutarlo?

Para ejecutar el programa debemos indicar la ruta de la carpeta y el número de días que queremos consultar.

Por ejemplo, para buscar archivos modificados durante los últimos 7 días:

```powershell
.\archivos_recientes.exe "C:\Users\ingen\Downloads" 7
```

También podemos cambiar el número de días según lo que necesitemos.

## Pruebas realizadas

Para comprobar que el programa funcionara, realizamos tres ejecuciones utilizando el programa, utilizando distintos días y distintas carpetas para comprobar su ejecución satisfactoria. Tanto Beatriz como Edson hicieron sus pruebas individuales desde su computadora, y los resultados se encuentran en la carpeta "Capturas/".

## ¿Qué información muestra?

El programa organiza los resultados en cuatro columnas:

| Columna | Descripción |
|---|---|
| Nombre | Nombre del archivo encontrado |
| Modificación | Fecha y hora de su última modificación |
| Modo | Información sobre los permisos del archivo |
| Tamaño | Tamaño del archivo en bytes |

De esta manera podemos revisar la información de varios archivos sin tener que abrir sus propiedades uno por uno.

## Conclusión

Con esta tarea pudimos entender un poco mejor cómo se puede obtener información de los archivos y directorios mediante un programa en C++, utilizando conceptos revisados en clase, usamos funciones para recorrer carpetas y consultar sus propiedades, además de trabajar argumentos desde la propia terminal (sin una interfaz gráfica). Algo bastante importante a resaltar es que, en la columna de modo, trabajamos con el modo octal crudo (ya que en terminales de linux tenemos otra forma de verlo como 'rwxr-xr-x'), y esa fue una de las dificultades durante el desarrollo de esta tarea.

