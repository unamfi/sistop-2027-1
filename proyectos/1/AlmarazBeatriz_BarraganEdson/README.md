# FiUnamFS

## Autores

- Beatriz Almaraz
- Edson Barragán

---

## Descripción

Implementación de un gestor para el sistema de archivos **FiUnamFS**, desarrollada como parte de la asignatura de Sistemas Operativos.

El proyecto permite interactuar con una imagen de disco (`.img`) que utiliza el formato FiUnamFS, proporcionando herramientas para visualizar y administrar la información almacenada en ella.

---

## Características

El sistema implementa las siguientes funcionalidades:

- Apertura de imágenes de disco FiUnamFS.
- Lectura del superbloque.
- Validación de la versión del sistema de archivos.
- Lectura de entradas de directorio.
- Visualización de archivos almacenados.
- Gestión de archivos dentro de la imagen.
- Operaciones de administración definidas por la especificación del proyecto.

---

## Estructura del Proyecto

```text
AlmarazBeatriz_BarraganEdson/
│
├── build/
│
├── include/
│   ├── DirectoryEntry.h
│   ├── FiUnamFS.h
│   ├── Operation.h
│   ├── SuperBlock.h
│   ├── ThreadManager.h
│   └── Utils.h
│
├── src/
│   ├── DirectoryEntry.cpp
│   ├── FiUnamFS.cpp
│   ├── ThreadManager.cpp
│   ├── Utils.cpp
│   └── main.cpp
│
├── tests/
│
├── Makefile
├── README.md
└── fiunamfs.img
```

---

## Requisitos

### Ubuntu / Debian

Instalar las herramientas de compilación:

```bash
sudo apt update
sudo apt install build-essential
```

Verificar instalación:

```bash
g++ --version
make --version
```

### Windows

Se recomienda utilizar:

- Visual Studio Code
- MinGW-w64
- Extensión C/C++ para Visual Studio Code

Verificar instalación:

```powershell
g++ --version
```

---

## Compilación

### Utilizando Makefile

Desde la raíz del proyecto:

```bash
make
```

Se generará el ejecutable:

```text
fiunamfs.exe
```

### Compilación manual

```bash
g++ src/main.cpp src/FiUnamFS.cpp src/Utils.cpp -Iinclude -o fiunamfs.exe
```

---

## Ejecución

### Windows

```powershell
.\fiunamfs.exe
```

### Ubuntu / Debian

```bash
./fiunamfs
```

---

## Uso desde Visual Studio Code

1. Abrir la carpeta raíz del proyecto.
2. Abrir una terminal integrada.
3. Compilar el proyecto:

```bash
make
```

4. Ejecutar el programa:

```powershell
.\fiunamfs.exe
```

o en Linux:

```bash
./fiunamfs
```

---

## Funcionalidades

### Lectura del Superbloque

El sistema obtiene y muestra la información general del volumen FiUnamFS.

Información obtenida:

- Nombre del sistema de archivos.
- Versión.
- Etiqueta del volumen.
- Tamaño de cluster.
- Número de clusters destinados al directorio.
- Número total de clusters.

Ejemplo de salida:

```text
=== SUPERBLOQUE ===

Sistema: FiUnamFS
Version: 27-1
Etiqueta: Disco de Gunnar
Tamano de cluster: 2048 bytes
Clusters de directorio: 4
Clusters totales: 720
```

---

### Lectura del Directorio

El programa analiza las entradas almacenadas en los clusters de directorio definidos por la especificación de FiUnamFS.

Durante esta operación:

- Se identifican archivos válidos.
- Se ignoran entradas vacías.
- Se almacena la información en memoria para futuras operaciones.

---

### Listado de Archivos

Permite visualizar los archivos detectados dentro de la imagen de disco.

Información mostrada:

- Nombre del archivo.
- Tamaño en bytes.
- Cluster inicial.

---

### Exportación de Archivos

Permite copiar archivos desde la imagen FiUnamFS hacia el sistema operativo anfitrión.

Proceso general:

1. Seleccionar un archivo almacenado.
2. Leer su contenido desde la imagen.
3. Crear una copia en el sistema de archivos local.

---

### Importación de Archivos

Permite copiar archivos desde el sistema anfitrión hacia la imagen FiUnamFS.

Proceso general:

1. Seleccionar un archivo externo.
2. Buscar espacio disponible dentro de la imagen.
3. Registrar una nueva entrada de directorio.
4. Escribir los datos correspondientes.

---

### Eliminación de Archivos

Permite eliminar archivos almacenados dentro del sistema FiUnamFS mediante el mecanismo definido por la especificación.

---

### Monitoreo Concurrente

El sistema incorpora hilos para cumplir los requerimientos de concurrencia establecidos en el proyecto.

Los hilos permiten:

- Ejecutar operaciones simultáneamente.
- Reportar el estado de las operaciones.
- Mantener un registro de actividades realizadas sobre la imagen.

---

## Limpieza del Proyecto

Para eliminar los archivos generados durante la compilación:

```bash
make clean
```

---

## Evidencias y Pruebas

Las siguientes secciones están destinadas a la inclusión de capturas de pantalla que demuestren el correcto funcionamiento del sistema.

### Validación del Superbloque



![Validación del Superb bloque](evidencias\Captura de pantalla 2026-11-16 202608.png)

---

### Lectura del Directorio

![Lectura del Directorio](evidencias\Captura de pantalla 2026-11-16 211532.png)

---

### Listado de Archivos

![Listado de Archivos](evidencias\Captura de pantalla 2026-11-19 224007.png)

---

### Exportación de Archivos


![Exportación de Archivos](evidencias\commit_5)

---

### Importación de Archivos


![Importación de Archivos (TXT y PNG)](commit_6\capturas\01_comparacion_hashes.png)

---

### Eliminación de Archivos


![Eliminación de Archivos](evidencias\commit_7)

---

### Monitoreo Concurrente

![Monitoreo Concurrente](evidencias\commit_7)