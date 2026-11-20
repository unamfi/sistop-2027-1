# Proyecto Final: (Micro) sistema de archivos multihilos - FiUnamFS

* **Autor:** Carlos Martínez
* **Materia:** Sistemas Operativos (sistop-2027-1)

---

## 1. Descripción y Contenidos del Disco Muestra
Implementación completa en Python para administrar imágenes de disco bajo la especificación **FiUnamFS (versión 27-1)** de 1440 KiB, con asignación continua y directorio plano.

Al inspeccionar el sistema de archivos muestra proporcionado (`fiunamfs.img`), se identificaron los siguientes tres archivos almacenados:

| Nombre | Tamaño (Bytes) | Clúster Inicial | Fecha de Creación | Última Modificación |
| :--- | :--- | :--- | :--- | :--- |
| `README.org` | 31,126 | 6 | 2026-11-05 16:31:24 | 2026-11-05 16:31:24 |
| `logo.png` | 126,423 | 22 | 2026-11-05 16:31:24 | 2026-11-05 16:31:24 |
| `mensaje.jpg` | 254,484 | 84 | 2026-11-05 16:31:24 | 2026-11-05 16:31:24 |

## 2. Entorno y Dependencias
* **Lenguaje:** Python 3 (probado en Python 3.9+ / macOS y Linux).
* **Dependencias externas:** Ninguna. Emplea exclusivamente módulos de la biblioteca estándar (`struct`, `os`, `sys`, `math`, `threading`, `queue`, `datetime`).

## 3. Instrucciones de Ejecución
Desde la terminal, ejecuta el programa pasando como argumento la ruta a la imagen `.img`:
```zsh
python3 main.py <ruta_a_la_imagen.img>

