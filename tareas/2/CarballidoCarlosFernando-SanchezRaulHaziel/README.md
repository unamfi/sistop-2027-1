# Tarea 2: Obteniendo información de un directorio

**Materia:** Sistemas Operativos  
**Profesor:** Gunnar Eyal Wolf Iszaevich  
**Grupo:** 7  
**Semestre:** 2027-1  
**Fecha de entrega:** 10 de noviembre de 2026

**Integrantes:**
- Carlos Fernando Carballido Carrillo — 320310186
- Raúl Haziel Sánchez Soperanes — 321026303

## 1. Descripción del problema

Para esta tarea desarrollamos un programa que consulta el contenido de un directorio y muestra las entradas que fueron modificadas recientemente.

El usuario debe indicar la ruta del directorio y el número de días que desea consultar. El programa revisa la información de cada entrada y presenta solamente las que cumplen con el periodo indicado.

Los resultados aparecen ordenados lexicográficamente por nombre e incluyen cuatro datos: nombre, fecha de última modificación, modo (tipo y permisos) y tamaño en bytes.

## 2. Lenguaje y entorno de desarrollo

Utilizamos Python 3 en Ubuntu/Linux, trabajando desde la terminal.

Elegimos Python porque su biblioteca estándar permite consultar directamente los atributos de archivos y directorios. No necesitamos instalar bibliotecas adicionales ni ejecutar programas externos para obtener la información.

El programa se encuentra en `archivos_recientes.py`.

## 3. Instrucciones de ejecución

Se necesita tener Python 3 instalado.

Desde la carpeta donde se encuentra el programa, ejecutamos:

```bash
python3 archivos_recientes.py <directorio> <dias>
```

Por ejemplo, para consultar los archivos modificados durante los últimos tres días en `/tmp`:

```bash
python3 archivos_recientes.py /tmp 3
```

También podemos revisar el directorio actual:

```bash
python3 archivos_recientes.py . 3
```

El programa no es interactivo: recibe ambos parámetros desde la línea de comandos.

## 4. Funcionamiento

Dividimos la solución en varias funciones para que sea más fácil entenderla y realizar modificaciones.

Primero se validan los argumentos recibidos. Después, mediante `os.scandir()`, se consulta el contenido directo del directorio.

De cada entrada obtenemos sus atributos con `stat()`, sin seguir enlaces simbólicos. Esto permite conocer su fecha de modificación, tamaño y modo.

Para filtrar los resultados utilizamos la fecha actual como referencia. Cuando el número de días es mayor que cero, se consideran periodos de 24 horas. Para el valor cero decidimos mostrar las entradas modificadas durante el día actual, según la hora local del equipo.

Finalmente, ordenamos los nombres y mostramos los resultados en una tabla con columnas alineadas. La columna del nombre ajusta su ancho para que los archivos con nombres largos no desordenen la presentación.

## 5. Pruebas realizadas

Probamos el programa en Ubuntu con distintos argumentos:

| Prueba | Resultado |
|---|---|
| `/tmp 3` | Mostró las entradas recientes del directorio. |
| `/tmp 0` | Mostró las entradas modificadas durante el día actual. |
| `/carpeta_inexistente 3` | Mostró un mensaje de error indicando que el directorio no existe. |
| Sin argumentos | Mostró las instrucciones de uso. |
| `. 3` | Identificó correctamente el propio archivo Python, incluyendo sus atributos. |

En las pruebas realizadas, las consultas terminaron correctamente y los casos inválidos mostraron mensajes explicativos.

## 6. Decisiones y limitaciones

Decidimos revisar únicamente las entradas del directorio indicado, sin recorrer sus subdirectorios. También incluimos directorios y enlaces simbólicos, además de archivos ordinarios.

Para representar el modo utilizamos la notación octal de Unix, que incluye el tipo de archivo y sus permisos.

El programa depende de los atributos que proporciona el sistema de archivos. Si alguna entrada no puede consultarse, muestra un aviso en lugar de ignorar el problema silenciosamente.

Una posible mejora sería permitir búsquedas recursivas, aunque no las implementamos porque el ejercicio solamente solicita consultar un directorio.

## 7. Archivos de la entrega

- `archivos_recientes.py`: código fuente del programa.
- `README.md`: instrucciones, funcionamiento, pruebas y decisiones tomadas.

No se necesita compilar el programa ni instalar bibliotecas externas.
