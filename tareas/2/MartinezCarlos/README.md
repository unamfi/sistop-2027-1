# Tarea 2: Obtención de información de un directorio

* **Autor:** Carlos Martínez
* **Materia:** Sistemas Operativos (sistop-2027-1)

---

## 1. Descripción
Programa en Python no interactivo que procesa un directorio especificado como parámetro e imprime una lista filtrada de archivos cuya última modificación haya ocurrido dentro del número de días indicado o menos.

## 2. Lenguaje y entorno de ejecución
* **Lenguaje:** Python 3 (biblioteca estándar exclusivamente: `os`, `sys`, `stat`, `time`, `datetime`).
* **Instrucciones para ejecutar:**
  ```zsh
  python3 archivos_recientes.py <directorio> <días>
python3 archivos_recientes.py /tmp 1

