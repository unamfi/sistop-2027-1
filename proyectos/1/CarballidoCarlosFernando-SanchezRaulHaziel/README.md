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
