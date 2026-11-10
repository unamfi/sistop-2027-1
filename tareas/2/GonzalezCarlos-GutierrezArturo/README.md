# Tarea 2: Obteniendo información de un directorio

Autores: Carlos González y Arturo Gutiérrez

## Lenguaje y entorno

El programa está escrito en Python 3. Solo usa la biblioteca estándar (`os`, `sys`, `time` y `datetime`) y no llama a ningún programa externo, como pide la tarea.

## Qué hace

Recibe dos parámetros por línea de comando: la ruta de un directorio y un número de días. Abre el directorio e imprime los archivos cuya última modificación fue hace ese número de días o menos, ordenados por nombre. Por cada uno muestra el nombre, la fecha de modificación, el modo (permisos) en octal y el tamaño en bytes.

## Ejecución

    python archivos_recientes.py <directorio> <días>

Si se ejecuta sin los dos parámetros, muestra el mensaje de invocación.

## Ejemplo de ejecución

    python archivos_recientes.py tareas/2 5
    Nombre                         Modificación     Modo   Tamaño
    ==============================================================
    GonzalezCarlos-GutierrezArturo 2026-11-10 17:16 040777 0
    README.md                      2026-11-10 17:16 100666 3560

## Nota sobre los modos

La prueba se hizo en Windows, que no maneja permisos Unix. Por eso los modos salen como `100666` (archivo) y `040777` (directorio) en lugar de valores como `100644`. En Linux o macOS salen los permisos reales.