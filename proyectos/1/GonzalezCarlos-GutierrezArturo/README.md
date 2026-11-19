# Proyecto FiUnamFS

**Integrantes:** Carlos Gonzalez y Arturo Gutierrez

Programa en Python para leer imágenes del sistema de archivos FiUnamFS versión 27-1.

## Requisitos

- Python 3.10 o posterior.
- No requiere instalar paquetes externos.
- La imagen `fiunamfs.img` se busca en `proyectos/1`, un nivel arriba de la carpeta del equipo.

## Ejecución

Desde una terminal, en esta carpeta:

```text
python main.py
```

El menú permite listar, extraer un archivo de FiUnamFS y copiar un archivo local hacia FiUnamFS. Para extraer, escribe el nombre del archivo y una ruta destino completa. Para agregar, escribe la ruta local; el nombre dentro del volumen debe tener como máximo 15 caracteres ASCII.

Por ejemplo:

```text
C:\Users\Carlos\Documents\logo.png
```

Si ya existe un archivo en la ruta de extracción, la operación se cancela para evitar sobrescribirlo.

## Probar sin alterar la imagen original

La opción de copiar modifica la imagen. Para probarla, trabaja sobre una copia:

```bash
cp ../fiunamfs.img prueba.img
python main.py prueba.img
```

El archivo `prueba.img` está excluido del repositorio por `.gitignore`.
