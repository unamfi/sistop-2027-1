# Tarea 2. Obteniendo información de un directorio

Ladrón de Guevara Castro Sebastián (`Sebastian82879`) y Pérez Báez Jessica
Estefani (`FannyJP`), entrega en equipo.

## Qué hace el programa

`archivos_recientes.py` recibe la ruta de un directorio y un número de días,
abre el directorio e imprime los archivos cuya última modificación fue hace
ese número de días o menos. De cada uno muestra el nombre, la fecha de
modificación, el modo (los permisos) y el tamaño, ordenados
lexicográficamente por nombre.

## Lenguaje y entorno

Lo hicimos en Python 3 sobre macOS, aunque debería funcionar igual en Linux con
cualquier versión a partir de la 3.6. Solo usa la biblioteca estándar
(`os`, `sys` y `time`), así que no llama a ningún programa externo ni hace
falta instalar nada.

### Cómo ejecutarlo

    $ chmod +x archivos_recientes.py
    $ ./archivos_recientes.py <directorio> <días>

Por ejemplo

    $ ./archivos_recientes.py /tmp 1
    Nombre                         Modificación     Modo   Tamaño
    ==============================================================
    Archivo.md                     2026-11-08 19:37 100644 2
    Zdir                           2026-11-08 19:37 040755 4096
    b.txt                          2026-11-08 19:37 100644 5
    enlace                         2026-11-08 19:37 120777 5

Si se ejecuta sin los dos parámetros muestra la forma de uso, igual que en el
ejemplo del enunciado. Los días aceptan decimales, de modo que `0.5` son las
últimas doce horas.

## Cómo funciona

Primero revisamos que vengan los dos parámetros y que los días sean un número
válido. Con eso calculamos un momento límite, que es la hora actual menos los
días convertidos a segundos.

Después abrimos el directorio con `os.scandir` y le pedimos a cada entrada su
información, que es lo mismo que hace la llamada al sistema `lstat`. Nos
quedamos con las entradas cuya fecha de modificación (`st_mtime`) es igual o posterior
al límite, las ordenamos por nombre con `sorted` y las imprimimos en columnas.

El modo sale de `st_mode` impreso en octal con seis dígitos, que es como
aparece en el ejemplo del profesor.

## Decisiones que tomamos

El enunciado no dice nada de los archivos ocultos. Comparando con el ejemplo
notamos que en el `/tmp` del profesor no aparece `.X11-unix`, que casi siempre
existe y se modifica al arrancar la máquina, así que decidimos omitirlos igual
que hace `ls` sin `-a`.

Los enlaces simbólicos se describen a sí mismos y no al archivo al que
apuntan, por eso aparecen con modo `120777`.

Si el directorio no existe, no es un directorio o no hay permiso para leerlo,
el programa lo indica con un mensaje y termina con código 2 en lugar de
mostrar un error de Python.

## Complicaciones

Al principio pensábamos que el modo eran solo los permisos, así que esperábamos ver
algo como `755`. Cuando vimos `040755` en el ejemplo creímos que tenía ceros de
relleno, pero investigando sobre `st_mode` encontramos que los primeros dígitos
indican el tipo de archivo. Un directorio empieza con `04` mientras que un
archivo regular empieza con `10`, por eso el modo tiene seis dígitos.

En nuestras pruebas los directorios medían 4096 y en el ejemplo miden 0.
Pensamos que estábamos leyendo mal el tamaño, pero depende del sistema de archivos. En
`tmpfs`, donde muchas distribuciones montan `/tmp`, los directorios reportan
0 mientras que en `ext4` reportan un bloque completo. En macOS además `/tmp`
es un enlace a `/private/tmp`, así que la salida tampoco es idéntica.

No teníamos clara la diferencia entre `stat` y `lstat`. Leyendo la documentación
de `os.scandir` vimos que por defecto sigue los enlaces simbólicos, con lo que un
enlace roto provoca una excepción. Con `follow_symlinks=False` eso ya no pasa.

También nos sorprendió que `README.md` saliera antes que
`archivos_recientes.py`. Python compara las cadenas por el código de cada
carácter y las mayúsculas van antes que las minúsculas, que es justo el orden
lexicográfico que pide el enunciado.

Por último nos quedamos pensando qué pasa si un archivo se borra mientras el
programa lo revisa, algo común en `/tmp`. Para ese caso agregamos un `try` que
simplemente lo salta.

## Dudas resueltas

Varias de las complicaciones anteriores se nos aclararon repasando la
presentación de archivos y directorios.

La de `stat` contra `lstat` quedó clara con la parte de ligas simbólicas. Una
liga simbólica es un archivo especial que guarda el nombre de otro objeto, el
sistema operativo sigue esa indirección de forma transparente para el
programa, por eso al pedir la información de un enlace recibíamos la del
archivo de destino. Si el archivo referido se borra la liga se rompe, que es
justo el caso en que el programa fallaba.

Lo del tamaño de los directorios también tuvo sentido. Un subdirectorio es
simplemente un archivo de tipo especial que gestiona el sistema operativo, las
transferencias siempre se hacen en bloques completos (hoy de 4K), así que un
directorio que ocupa un bloque mide 4096. Con la parte de montaje entendimos
por qué al profesor le salía 0, cada punto de montaje puede ser un sistema de
archivos distinto, incluso uno que no es físico, por lo que `/tmp` no tiene
que reportar lo mismo que el resto del árbol.

También relacionamos `os.scandir` con las operaciones con directorios que
vimos en C. Abrir el directorio, iterar sobre sus entradas y cerrarlo es lo
mismo que hacen `opendir`, `readdir` y `closedir`, en Python el `with` se
encarga de cerrarlo. Una diferencia es que `readdir` sí entrega las entradas
`.` y `..` que existen en todo directorio, mientras que `os.scandir` ya las
omite.

Lo que no encontramos en las presentaciones fue el formato de `st_mode` ni el
orden en que Python compara las cadenas, eso lo resolvimos buscando en la
documentación.

## Dudas y posibles mejoras

La columna del nombre mide 30 caracteres fijos, por lo que un nombre más
largo descuadra la línea (en el ejemplo del enunciado pasa con los
directorios de `systemd`). Se podría calcular el ancho según el nombre más
largo, aunque entonces la salida ya no sería igual a la del ejemplo. No tenemos
claro cuál de las dos opciones sería más correcta.

Con `argparse` se podría tener un `--help` y agregar opciones sin complicar
la lectura de parámetros, por ejemplo un `-a` para mostrar también los
archivos ocultos.

El módulo `stat` tiene la función `filemode`, que convierte el modo a algo
como `drwxr-xr-x`. Se lee más fácil que el octal y podría mostrarse junto a
él. También se podrían mostrar los tamaños en KB o MB como hace `ls -h`.

Otras ideas serían recorrer los subdirectorios con `os.walk`, permitir
ordenar por fecha o por tamaño, o reescribirlo con `pathlib`, que es la forma
más moderna de manejar rutas en Python.
