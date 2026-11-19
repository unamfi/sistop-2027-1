# Tarea 2: Obteniendo información de un directorio

**Alumno:** Casas Pérez Rodrigo Imanol  
**Materia:** Sistemas Operativos  
**Semestre:** 2027-1  
**Lenguaje:** C

## Descripción

Programa desarrollado en C que muestra información de los archivos y directorios modificados durante un número determinado de días.

La información se presenta ordenada lexicográficamente por nombre e incluye la fecha de última modificación, el modo y el tamaño en bytes.

## Compilación

Desde la carpeta de entrega:

```bash
gcc -Wall -Wextra -std=c11 archivos_recientes.c -o archivos_recientes
```

## Ejecución

```bash
./archivos_recientes <directorio> <dias>
```

Ejemplo:

```bash
./archivos_recientes /tmp 3
```

## Implementación

Se utilizan funciones de C y POSIX como `opendir()`, `readdir()`, `stat()`, `closedir()` y `qsort()`.

No se ejecutan programas externos para obtener la información.