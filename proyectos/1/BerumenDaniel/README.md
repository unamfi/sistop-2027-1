# FiUnamFS: micro sistema de archivos multihilos

Proyecto final de Sistemas Operativos, Facultad de Ingeniería, UNAM.

Programa que lee y modifica imágenes del sistema de archivos `FiUnamFS`
(versión `27-1`), un sistema de archivos plano de asignación contigua que
cabe en un diskette de 1440 KiB.

## Autor

- Daniel Berumen Valdez

## Funcionalidad

- [ ] Listar los contenidos del directorio
- [ ] Copiar un archivo de FiUnamFS hacia el equipo
- [ ] Copiar un archivo del equipo hacia FiUnamFS
- [ ] Eliminar un archivo de FiUnamFS
- [ ] Dos o más hilos concurrentes sincronizados

## Entorno y dependencias

- Python 3.10 o superior (CPython)
- Solo biblioteca estándar (`struct`, `threading`, `queue`, `os`, `datetime`)
- Probado en Linux

No requiere instalar paquetes adicionales.

## Estructura del proyecto

```
.
├── README.md
├── .gitignore
├── fiunamfs.py       Acceso a la imagen: validación, directorio, lectura y escritura
├── hilos.py          Hilos de trabajo y mecanismos de sincronización
├── main.py           Interfaz de menú en texto
└── crear_imagen.py   Genera una imagen vacía para pruebas
```

## Formato de FiUnamFS

| Zona        | Clusters | Contenido                                   |
|-------------|----------|---------------------------------------------|
| Superbloque | 0        | Identificación, versión, etiqueta, tamaños  |
| Directorio  | 1 a 4    | 128 entradas de 64 bytes                    |
| Datos       | 5 en adelante | Archivos en clusters contiguos         |

- Sector: 512 bytes; cluster: 4 sectores (2048 bytes)
- Enteros de 32 bits, little endian
- Cadenas ASCII de 8 bits

## Uso

_Pendiente._

## Estrategia de asignación

_Pendiente._

## Sincronización

_Pendiente._

## Ejemplos

_Pendiente._

## Contenido del disco de ejemplo

_Pendiente: la imagen `fiunamfs.img` aún no se publica._
