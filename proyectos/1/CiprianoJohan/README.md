# Proyecto 1: (Micro) sistema de archivos multihilos — FiUnamFS

**Autor:** Cipriano Amador Johan Tadeo
**Materia:** Sistemas Operativos 2027-1, Facultad de Ingeniería, UNAM

Programa para listar, extraer, copiar y eliminar archivos dentro de una
imagen del sistema de archivos `FiUnamFS` (versión 27-1).

> -.- En desarrollo. La documentación completa (uso, sincronización entre
> hilos y ejemplos) se agrega al terminar la implementación.

## Entorno

- Python 3.8 o superior (CPython)
- Solo biblioteca estándar; no hay dependencias que instalar

## Estructura

| Archivo        | Contenido                                           |
|----------------|-----------------------------------------------------|
| `fiunamfs.py`  | Especificación de FiUnamFS: constantes, superbloque (lectura y validación), entradas del directorio, listado, extracción de archivos, copia hacia el volumen (asignación contigua *first fit*), eliminación, acceso a la imagen y formateo |

## Uso (provisional)

Mientras se termina la interfaz, se puede listar el contenido de una imagen
y copiar archivos entre ella y el equipo:

```bash
python fiunamfs.py ../fiunamfs.img                          # listar
python fiunamfs.py ../fiunamfs.img extraer README.org extraidos/
python fiunamfs.py prueba.img copiar notas.txt               # equipo → FiUnamFS
python fiunamfs.py prueba.img eliminar notas.txt
```

Al copiar hacia FiUnamFS se valida que el nombre sea US-ASCII de máximo 15
caracteres y que no exista ya; el archivo se coloca en el primer hueco de
clusters contiguos que alcance. Eliminar solo marca la entrada como libre
(`-` y `#..............`); sus clusters quedan disponibles para nuevos archivos.
