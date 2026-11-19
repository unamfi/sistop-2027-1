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

El menú permite listar los archivos y copiar uno de FiUnamFS al equipo. Para extraer un archivo, escribe su nombre tal como aparece en la lista y luego una ruta destino completa, incluyendo el nombre del archivo.

Por ejemplo:

```text
C:\Users\Carlos\Documents\logo.png
```

Si ya existe un archivo en la ruta destino, la extracción se cancela para evitar sobrescribirlo.
