# Gestor de Sistema de Archivos FiUnamFS

**Autores:**
* Peralta Rojas Jose Daniel

---

## 1. Estrategia de solución

El proyecto se dividió en dos módulos independientes para separar la manipulación binaria de bajo nivel de la interacción con el usuario:

* **`fiunamfs.py` (Lógica del sistema de archivos):** Implementa la clase `FiUnamFS`, encargada de validar la estructura del volumen y operar directamente sobre los bytes de la imagen de disco mediante los módulos estándar `struct`, `os` y `math`.
  * **Lectura de estructura:** Al instanciarse, lee los primeros 52 bytes del cluster 0 (superbloque) en formato *Little Endian* para obtener dinámicamente el tamaño de cluster (`2048` B), los clusters del directorio (`4`) y los clusters totales (`720`), verificando que el tamaño físico del archivo `.img` coincida con lo declarado.
  * **Gestión de directorio plano:** Recorre secuencialmente las 128 entradas de 64 bytes ubicadas entre los clusters 1 y 4 (`offset 2048` a `10239`). Procesa únicamente las entradas activas (`b'F'`) sin detenerse ante entradas vacías (`b'-'`), permitiendo que los registros estén intercalados.
  * **Asignación contigua:** Para insertar archivos desde el equipo local hacia `FiUnamFS`, ordena los intervalos de clusters ocupados `[inicio, fin)` y busca el primer hueco contiguo disponible a partir del cluster 5 (`data_ini_cluster`) donde quepa el archivo redondeado a múltiplos de cluster.
  * **Eliminación lógica:** Al borrar un archivo, marca su entrada de 64 bytes en el directorio como disponible (`-` seguido de `#..............` y ceros) sin necesidad de sobreescribir los clusters de datos.
* **`main.py` (Interfaz de usuario y concurrencia):** Proporciona un menú interactivo en terminal que delega todas las operaciones de entrada/salida al hilo secundario.

---

## 2. Descripción de la sincronización empleada

Para que la interfaz de usuario de las operaciones de acceso a disco evite condiciones de carrera sobre el archivo `.img`, se implementó un patrón **Productor-Consumidor** con dos hilos mediante la sincronización `queue.Queue` y `threading.Event` de la biblioteca estándar:

1. **Hilo de interfaz (Productor - hilo principal):** Captura la opción del usuario, empaqueta la petición junto con una instancia individual de `threading.Event` y un diccionario de respuestas, leva la tupla en `cola_tareas` (`queue.Queue`) y suspende su ejecución llamando a `evento_listo.wait()`.
2. **Hilo trabajador (Consumidor - `hilo_trabajador`):** Permanece bloqueado en `cola_tareas.get()` hasta recibir una tarea. Al extraerla, ejecuta la operación correspondiente, guarda el resultado y notifica al hilo principal activando `evento_listo.set()`.
3. **Terminación limpia:** Al seleccionar la opción de salir (`5`), el bloque `finally` envía una señal de parada (`None`) a la cola y espera la finalización ordenada del hilo secundario mediante `worker.join()`.

---

## 3. Requisitos de ejecución

* **Lenguaje:** Python 3.10 o superior (probado en Python 3.12).
* **Dependencias:** Ninguna biblioteca externa; utiliza únicamente módulos de la biblioteca estándar (`os`, `sys`, `math`, `struct`, `datetime`, `threading`, `queue`).
* **Sistema operativo:** Multiplataforma (Windows, Linux, macOS). En Windows configura automáticamente la salida estándar a `UTF-8` para desplegar el banner correctamente.
* **Archivo de disco:** Una imagen válida con formato `FiUnamFS` (por defecto busca `fiunamfs.img` en el directorio de trabajo).

---

## 4. Explicación acerca del uso

Ubícate en el directorio del proyecto y ejecuta `sistemaArchivos.py` desde la terminal. Puedes omitir argumentos para abrir `fiunamfs.img` por defecto, o pasar la ruta de una imagen específica como primer parámetro:

```bash
# Usando fiunamfs.img en el directorio actual
python sistemaArchivos.py

# Especificando otra imagen de disco
python sistemaArchivos.py ruta/a/mi_disco.img