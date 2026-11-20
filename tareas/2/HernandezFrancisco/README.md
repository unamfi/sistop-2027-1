# Tarea 2 - Obteniendo información de un directorio

- **Alumno:** Francisco Hernández Moguel
- **Materia:** Sistemas Operativos
- **Profesor:** Gunnar Wolf
- **Semestre:** 2027-1
## Descripción

El programa permite consultar los archivos y directorios modificados recientemente dentro de una ruta indicada. Recibe como argumentos la ubicación del directorio y el número de días que se desea consultar.

Los resultados se ordenan alfabéticamente y muestran el nombre, fecha de última modificación, permisos y tamaño en bytes.

## Implementación

El programa fue desarrollado en Python utilizando únicamente bibliotecas estándar:

- `os`: para abrir el directorio y obtener información de los archivos.
- `sys`: para recibir los argumentos de la terminal.
- `time`: para calcular el periodo de modificación.
- `datetime`: para presentar las fechas en un formato legible.

Se utilizó `os.scandir()` para recorrer los elementos del directorio y `stat()` para consultar sus propiedades.

Después de filtrar los resultados por fecha, se ordenan por nombre y se presentan en una tabla.

## Ejecución

Desde la carpeta donde se encuentra el programa:

```bash
python archivos_recientes.py <directorio> <dias>
```

Ejemplo:

```bash
python archivos_recientes.py . 7
```

La ejecución anterior consulta los elementos modificados durante los últimos siete días dentro del directorio actual.

El programa no requiere interacción adicional ni ejecuta programas externos para obtener información.

## Pruebas realizadas

Se realizaron las siguientes comprobaciones desde Git Bash:

1. Consulta del directorio actual con un periodo de siete días: se obtuvo una tabla de elementos recientes.
2. Ejecución sin argumentos: se mostró el formato de invocación esperado.
3. Ejecución con un número de días no válido (`hola`): se mostró un mensaje de error.

## Uso de inteligencia artificial

Para desarrollar esta tarea utilicé ChatGPT, de OpenAI, como apoyo para elaborar la implementación inicial en Python, organizar las funciones, revisar los requisitos y preparar la documentación.

También revisé el funcionamiento del programa mediante ejecuciones en Git Bash, comprobando que recibe los parámetros correctamente, presenta la información solicitada y detecta argumentos incorrectos.