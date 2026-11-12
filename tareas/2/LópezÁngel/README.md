# Obteniendo información de un directorio

Autor: López Vizcarra Ángel David

## Lenguaje y entorno
El programa está hecho con lenguaje C utilizando cabeceras como `diferent.h` para leer las entradas del directorio, o `<sys/stat.h>` para obtener permisos y fechas de modificación.

## Ejecución
Desde la terminal:

```bash
gcc archivos_recientes.c -o archivos_recientes
```


Elegí C porque permite trabajar directamente con las funciones del sistema operativo para consultar directorios, archivos y sus atributos, sin ejecutar programas externos.


## Ejemplo de ejecución

Este es un resultado de la salida usando la ruta de mi captea de documentos de mi computadora, con parametro de 7 dias.

```text
angel@MaquinaDeChamba:~/sistop/tarea2$ ~/sistop/tarea2/archivos_recientes "/mnt/c/Users/angel/Documents" 7

Nombre                         Modificacion        Modo    Tamano (bytes)
============================================================================
LabCGEHC                       2026-11-03 22:09:01  040777  512
Mis imágenes                   2026-11-08 14:15:23  040777  512
Mis vídeos                     2026-11-07 06:36:24  040777  512
ProyectoFinalGrafica            2026-11-07 01:14:44  040777  512
SQL Server Management Studio   2026-11-07 22:21:50  040777  512
septimo                        2026-11-08 15:15:45  040777  512
```