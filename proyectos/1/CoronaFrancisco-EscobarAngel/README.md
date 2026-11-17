# Proyecto 1: (Micro) sistema de archivos multihilos

- Autores: Angel Escobar y Francisco Corona
- Materia: Sistemas Operativos
- Grupo: 7
- Profesor: DR. GUNNAR EYAL WOLF ISZAEVICH
- Facultad de Ingeniería, UNAM

El programa abre una imagen de `FiUnamFS` y desde un menú deja listar el directorio, copiar un archivo del disco a la computadora, copiar un archivo de la computadora al disco y eliminar archivos.

## Entorno y cómo se corre

Lo hicimos en Python 3 (CPython) y sólo usa la biblioteca estándar: `os`, `struct`, `sys`, `threading` y `time`. No hay que instalar nada. Lo probamos con Python 3.13 en Windows; necesita por lo menos Python 3.7 porque usamos `str.isascii()`. Se corre pasándole la imagen:

    python3 fiunamfs.py <imagen de FiUnamFS>

Desde esta carpeta, con la imagen de ejemplo del profesor:

    python3 fiunamfs.py ../fiunamfs.img

Recomendamos trabajar sobre una copia de la imagen, porque las opciones 3 y 4 la modifican.

Al arrancar se ve el nombre del volumen y el menú. Se escribe el número de la opción y el programa pregunta lo que le falta:

    Volumen: Disco de Gunnar (720 clusters de 2048 bytes)

    1) Listar  2) Copiar a mi equipo  3) Copiar a FiUnamFS  4) Eliminar  5) Salir
    Opción: 1
    Nombre            Tamaño Cluster  Creación          Modificación
    ====================================================================
    README.org         31126       6  2026-11-05 16:31  2026-11-05 16:31
    logo.png          126423      22  2026-11-05 16:31  2026-11-05 16:31
    mensaje.jpg       254484      84  2026-11-05 16:31  2026-11-05 16:31

    3 archivos

    Opción: 2
    Archivo de FiUnamFS: mensaje.jpg
    Guardar como [mensaje.jpg]:
    Se copió mensaje.jpg a mensaje.jpg (254484 bytes)

    Opción: 3
    Archivo de tu equipo: notas.txt
    Se copió notas.txt a FiUnamFS en el cluster 5

    Opción: 4
    Archivo a eliminar: logo.png
    ¿Seguro que quieres borrar logo.png? (s/n): s
    Se eliminó logo.png

Al copiar hacia el equipo, si se deja vacío el nombre se guarda con el mismo nombre en la carpeta actual; también se puede dar una carpeta. No sobreescribimos archivos que ya existan en la computadora. Con la opción 5, Ctrl+D o Ctrl+C el programa termina.

## Cómo lo hicimos

Antes de hacer cualquier cosa leemos el superbloque y revisamos que diga `FiUnamFS` y la versión `27-1`; si no, el programa se sale sin abrir la imagen para escritura. Del superbloque sacamos el tamaño del cluster, cuántos clusters mide el directorio y cuántos mide el disco, así que no los dejamos fijos en el código.

El directorio lo leemos de 64 en 64 bytes y nos quedamos con las entradas de tipo `F`. Todos los enteros se leen y escriben con `struct` en formato `<I`. En la imagen de ejemplo los nombres vienen rellenos con espacios y terminan en `\0`, y las entradas vacías tienen `-` como tipo y `##############` como nombre, así que escribimos igual las nuevas y las borradas. Por eso los nombres pueden medir hasta 14 caracteres y tienen que ser ASCII.

Para copiar hacia el disco buscamos el primer hueco donde quepa el archivo completo, porque la asignación es contigua: ordenamos los archivos por su cluster inicial y vemos el espacio que queda entre uno y otro, y al final el que queda después del último. Si no hay hueco, avisamos y no se escribe nada. La fecha de creación es la hora en que se copia y la de modificación es la del archivo original. Eliminar sólo marca la entrada como vacía; los datos se quedan ahí hasta que otro archivo ocupe ese espacio, como en los sistemas de archivos de verdad.

## Hilos y sincronización

El programa tiene dos hilos: la interfaz (el hilo principal, que muestra el menú) y el hilo del disco, que es el único que abre la imagen. Así nunca hay dos operaciones escribiendo en el directorio al mismo tiempo.

Se comunican como en el ejemplo de productores y consumidores de clase. La interfaz mete el pedido (la operación y sus datos) en la lista `pedidos` y hace `release()` sobre el semáforo `hay_pedido`. El hilo del disco está dormido en ese semáforo; cuando despierta saca el pedido, hace la operación y deja el resultado en la lista `respuestas`, y avisa con `hay_respuesta`. Mientras tanto la interfaz espera en `hay_respuesta` y luego imprime lo que le regresaron. Las dos listas están protegidas con el semáforo `mutex`. Si la operación falla (no existe el archivo, no hay espacio, etc.) el hilo del disco regresa el mensaje de error en vez de morirse, y la interfaz lo muestra igual que cualquier otra respuesta. Para salir, la interfaz manda un pedido `None`; el hilo del disco lo ve, cierra la imagen y termina, y el principal lo espera con `join()`.

## ¿Qué tiene el disco de ejemplo?

Tiene tres archivos: `README.org`, que es el mismo enunciado del proyecto; `logo.png`, el escudo de la Facultad de Ingeniería; y `mensaje.jpg`, una foto con un letrero que dice "¡Muy bien hecho! Lograste recuperar la información del sistema de archivos FiUNAMFS. ¡Sigue adelante! :-)".
