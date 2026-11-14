# Proyecto: (Micro) sistema de archivos multihilos

Ladrón de Guevara Castro Sebastián ([`Sebastian82879`](https://github.com/Sebastian82879)), entrega individual.

Es un programa para trabajar con imágenes del sistema de archivos `FiUnamFS` versión `27-1`. Por ahora valida el superbloque y lista el contenido del directorio, las demás operaciones las voy agregando poco a poco.

## Entorno y requisitos

Lo escribí en Python 3 (CPython) y necesita la versión 3.8 o más reciente, yo lo probé con Python 3.13. Solo usa la biblioteca estándar (`struct`, `math`, `datetime`, `dataclasses`), así que no hay que instalar nada con `pip`. Debería funcionar en cualquier sistema donde corra Python, la interfaz es de texto y se usa desde la terminal.

## Cómo ejecutarlo

Desde esta carpeta se le pasa la ruta de la imagen

```
python3 main.py ruta/a/fiunamfs.img
```

Si no se le pasa ninguna busca `fiunamfs.img` en la carpeta actual. Antes de hacer cualquier cosa revisa que la imagen diga `FiUnamFS` y que sea la versión `27-1`, si no se niega a abrirla para no dañar un archivo que no es el correcto.

## Ejemplo de uso

Todo se hace desde un menú con números. Así se ve con la imagen que nos dio el profe

```
=== FiUnamFS · volumen "Disco de Gunnar" ===
  1) Listar los contenidos
  2) Salir
Elige una opción: 1

    #  Nombre              Tamaño  Cluster  Creado               Modificado
    1  README.org          31,126        6  2026-11-05 16:31:24  2026-11-05 16:31:24
    2  logo.png           126,423       22  2026-11-05 16:31:24  2026-11-05 16:31:24
    3  mensaje.jpg        254,484       84  2026-11-05 16:31:24  2026-11-05 16:31:24

  3 archivo(s), 1,024 KB libres
```

## Pruebas con la imagen del profe

Con `fiunamfs.img` probé el listado, muestra los tres archivos con su tamaño, su cluster inicial y sus fechas. Las demás operaciones las voy a probar conforme las vaya agregando.

## Contenidos del disco

El volumen se llama `Disco de Gunnar` y trae tres archivos, `README.org` (31,126 bytes), `logo.png` (126,423 bytes) y `mensaje.jpg` (254,484 bytes). Todavía no puedo sacarlos de la imagen para ver qué son, eso viene en la siguiente etapa.

Algo curioso es que el cluster 5, el primero del área de datos, está libre porque `README.org` empieza en el 6.

## Por qué una interfaz de texto y no FUSE

La rúbrica le da la calificación más alta a un módulo de FUSE o a una navegación textual que no requiera ayuda, yo me fui por la segunda porque trabajo en una MacBook Air con chip M4.

En Mac FUSE no viene instalado, hay que bajar macFUSE. En las Mac con chip de Apple además hay que reiniciar en modo de recuperación y bajarle la seguridad a la computadora para que deje cargar extensiones del kernel, preferí no mover eso y hacerlo de una forma que funcionara sin cambiarle nada a la compu. Las versiones nuevas de macFUSE ya tienen otra forma que no pide eso, pero todavía es nueva y no soporta todo. También está FUSE-T, pero no tenía cómo asegurar que funcionara igual que en Linux, que es donde corren los ejemplos que nos enseñó el profe en clase.

Aparte así es más fácil probarlo, con FUSE quien lo corra tendría que instalar FUSE y la biblioteca de Python. El menú solo usa lo que ya trae Python, así que corre igual en Mac, Linux o Windows sin instalar nada.

Para que el menú se entienda sin leer nada las opciones están numeradas, los archivos se eligen por su número en el listado, cada pregunta dice qué se puede contestar (por ejemplo "Enter para cancelar") y si escribes algo que no va el programa te dice qué esperaba en lugar de tronar.

## Cómo está organizado

El código está en dos archivos. `fiunamfs.py` tiene la clase `FiUnamFS`, que sabe leer el superbloque e interpretar el directorio. `main.py` tiene la interfaz, es el que se ejecuta. Por ahora todo corre en un solo hilo.

## Estrategia

El superbloque está en el cluster 0, de ahí saco el tamaño del cluster, cuántos clusters mide el directorio y cuántos mide todo el disco, en lugar de dejar esos números fijos en el código. El directorio empieza en el cluster 1, cada entrada mide 64 bytes y la leo de un jalón con `struct.unpack` usando el formato `<c15sII14s14s12x`, que es justo la tabla de la especificación (tipo, nombre, tamaño, cluster inicial, las dos fechas y los 12 bytes reservados), con `<` para que los enteros sean little endian.

Una entrada cuenta como vacía si su tipo no es `F` o si su nombre es uno de los nombres reservados para entradas vacías, cualquiera de las dos cosas basta.

El directorio se parece mucho al de FAT que vimos en clase, cada entrada guarda el nombre, el cluster inicial, el tamaño y las fechas, solo que aquí mide 64 bytes en lugar de 32 y el nombre puede tener hasta 15 caracteres en lugar del formato 8.3. A diferencia de FAT el programa sí distingue mayúsculas de minúsculas, `README.org` y `readme.org` serían dos archivos distintos.

Todavía me falta copiar archivos y eliminarlos, también separar el programa en dos hilos.

## Decisiones y dudas

La imagen del profe no sigue al pie de la letra la especificación en dos cosas. La primera es que las entradas vacías llevan `##############` en el nombre y no `#..............` como dice el planteamiento, mi programa reconoce las dos formas. La segunda es que los nombres se rellenan con espacios y terminan con un byte nulo (por ejemplo `README.org    \0`), al leer quito los dos para quedarme con el nombre.
