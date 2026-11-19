# Proyecto: (Micro) sistema de archivos multihilos

Ladrón de Guevara Castro Sebastián ([`Sebastian82879`](https://github.com/Sebastian82879)), entrega individual.

Es un programa para trabajar con imágenes del sistema de archivos `FiUnamFS` versión `27-1`, con él se puede listar el directorio, copiar archivos de la imagen a la computadora y de la computadora a la imagen, también eliminarlos. Por dentro trabaja con dos hilos que se comunican con mecanismos de sincronización.

## Entorno y requisitos

Lo escribí en Python 3 (CPython) y necesita la versión 3.8 o más reciente, yo lo probé con Python 3.13. Solo usa la biblioteca estándar (`struct`, `math`, `threading`, `queue`, `os`, `datetime`, `dataclasses`), así que no hay que instalar nada con `pip`. Debería funcionar en cualquier sistema donde corra Python, la interfaz es de texto y se usa desde la terminal.

## Cómo ejecutarlo

Desde esta carpeta se le pasa la ruta de la imagen

```
python3 main.py ruta/a/fiunamfs.img
```

Si no se le pasa ninguna busca `fiunamfs.img` en la carpeta actual. Antes de hacer cualquier cosa revisa que la imagen diga `FiUnamFS` y que sea la versión `27-1`, si no se niega a abrirla para no dañar un archivo que no es el correcto.

Como el programa escribe sobre la imagen conviene trabajar con una copia y dejar la original intacta. Si la imagen no tiene permiso de escritura el programa la abre de todos modos, pero solo deja listar y copiar hacia la computadora.

## Ejemplo de uso

Todo se hace desde un menú con números, para elegir un archivo se escribe su número en el listado, nunca hay que teclear su nombre. Así se ve con la imagen que nos dio el profe

```
=== FiUnamFS · volumen "Disco de Gunnar" ===
  1) Listar los contenidos
  2) Copiar un archivo de FiUnamFS a la computadora
  3) Copiar un archivo de la computadora a FiUnamFS
  4) Eliminar un archivo de FiUnamFS
  5) Salir
Elige una opción: 1

    #  Nombre              Tamaño  Cluster  Creado               Modificado
    1  README.org          31,126        6  2026-11-05 16:31:24  2026-11-05 16:31:24
    2  logo.png           126,423       22  2026-11-05 16:31:24  2026-11-05 16:31:24
    3  mensaje.jpg        254,484       84  2026-11-05 16:31:24  2026-11-05 16:31:24

  3 archivo(s), 1,024 KB libres
```

Para copiar un archivo hacia la computadora se elige la opción 2, luego el número del archivo y la carpeta de destino (con Enter se queda en la carpeta actual)

```
Elige una opción: 2
  ...
  Número del archivo a copiar (Enter para cancelar): 3
  Carpeta de destino (Enter para la carpeta actual):
  [##############################] 100%  254,484 de 254,484 bytes
  Listo, se copió a /Users/sebas/proyecto/mensaje.jpg
```

Para copiar hacia `FiUnamFS` se puede escribir la ruta o arrastrar el archivo a la terminal, si su nombre pasa de 15 caracteres el programa pide otro

```
Elige una opción: 3

  Ruta del archivo a copiar (puedes arrastrarlo aquí): '/Users/sebas/un nombre muy largo.txt'
  El nombre "un nombre muy largo.txt" pasa de 15 caracteres
  Nombre dentro de FiUnamFS (máximo 15 caracteres, Enter para cancelar): nota.txt
  [##############################] 100%  11 de 11 bytes
  Listo, se copió como "nota.txt"
```

Para eliminar se elige la opción 4, el número del archivo y se confirma con `s`.

## Pruebas con la imagen del profe

Probé las cuatro operaciones con `fiunamfs.img`, siempre sobre una copia. El listado muestra los tres archivos con su tamaño, su cluster inicial y sus fechas. Copié los tres archivos a la computadora y se abren bien, el `README.org` se lee como texto y las dos imágenes se ven completas, además coinciden en tamaño con lo que dice el directorio. Después copié un archivo de texto hacia la imagen, el programa lo acomodó en el cluster 5 (el hueco libre que hay antes del `README.org`) y al sacarlo de nuevo quedó idéntico al original. Por último eliminé un archivo y revisé con `od` que su entrada quedara marcada como vacía igual que las demás entradas vacías del disco (`-` en el tipo y `##############` en el nombre), el listado ya no lo muestra y el espacio libre aumenta.

## Contenidos del disco

El volumen se llama `Disco de Gunnar` y trae tres archivos.

`README.org` (31,126 bytes) es el mismo planteamiento del proyecto que está en el repositorio, en formato Org.

`logo.png` (126,423 bytes) es el escudo de la Facultad de Ingeniería, una imagen PNG de 354 × 425 pixeles.

`mensaje.jpg` (254,484 bytes) es una foto de 1440 × 1200 pixeles de una persona sosteniendo una hoja que dice "¡Muy bien hecho! Lograste recuperar la información del sistema de archivos FiUNAMFS. ¡Sigue adelante! :-)".

## Por qué una interfaz de texto y no FUSE

La rúbrica le da la calificación más alta a un módulo de FUSE o a una navegación textual que no requiera ayuda, yo me fui por la segunda porque trabajo en una MacBook Air con chip M4.

En Mac FUSE no viene instalado, hay que bajar macFUSE. En las Mac con chip de Apple además hay que reiniciar en modo de recuperación y bajarle la seguridad a la computadora para que deje cargar extensiones del kernel, preferí no mover eso y hacerlo de una forma que funcionara sin cambiarle nada a la compu. Las versiones nuevas de macFUSE ya tienen otra forma que no pide eso, pero todavía es nueva y no soporta todo. También está FUSE-T, pero no tenía cómo asegurar que funcionara igual que en Linux, que es donde corren los ejemplos que nos enseñó el profe en clase.

Aparte así es más fácil probarlo, con FUSE quien lo corra tendría que instalar FUSE y la biblioteca de Python. El menú solo usa lo que ya trae Python, así que corre igual en Mac, Linux o Windows sin instalar nada.

Para que el menú se entienda sin leer nada las opciones están numeradas, los archivos se eligen por su número en el listado, cada pregunta dice qué se puede contestar (por ejemplo "Enter para cancelar") y si escribes algo que no va el programa te dice qué esperaba en lugar de tronar.

## Cómo está organizado

El código está en dos archivos. `fiunamfs.py` tiene la clase `FiUnamFS`, que sabe leer el superbloque, interpretar el directorio y mover datos entre la imagen y la computadora, no sabe nada de hilos. `main.py` tiene la interfaz y los dos hilos, es el que se ejecuta.

## Estrategia

El superbloque está en el cluster 0, de ahí saco el tamaño del cluster, cuántos clusters mide el directorio y cuántos mide todo el disco, en lugar de dejar esos números fijos en el código. El directorio empieza en el cluster 1, cada entrada mide 64 bytes y la leo de un jalón con `struct.unpack` usando el formato `<c15sII14s14s12x`, que es justo la tabla de la especificación (tipo, nombre, tamaño, cluster inicial, las dos fechas y los 12 bytes reservados), con `<` para que los enteros sean little endian.

Una entrada cuenta como vacía si su tipo no es `F` o si su nombre es uno de los nombres reservados para entradas vacías, cualquiera de las dos cosas basta.

El directorio se parece mucho al de FAT que vimos en clase, cada entrada guarda el nombre, el cluster inicial, el tamaño y las fechas, solo que aquí mide 64 bytes en lugar de 32 y el nombre puede tener hasta 15 caracteres en lugar del formato 8.3. A diferencia de FAT el programa sí distingue mayúsculas de minúsculas, `README.org` y `readme.org` serían dos archivos distintos.

Como la asignación es contigua un archivo necesita clusters seguidos, para copiar uno nuevo ordeno los archivos por su cluster inicial y busco el primer hueco entre ellos donde quepa (primer ajuste). El área de datos empieza después del directorio, en el cluster 5. Primero escribo los datos y hasta el final la entrada del directorio, así si algo falla a la mitad el archivo simplemente no aparece y el directorio no queda apuntando a datos incompletos.

FiUnamFS no tiene un mapa de bits para saber qué clusters están libres, como dice la especificación toda la información de los archivos está en el directorio. Por eso para encontrar espacio reviso el directorio completo y calculo qué rango de clusters ocupa cada archivo, lo que no ocupe ninguno está libre.

Eliminar solo marca la entrada como vacía. Los datos se quedan en el disco igual que en otros sistemas de archivos, pero ese espacio ya queda libre para el siguiente archivo. Como aquí no hay ligas duras no hace falta llevar un contador de referencias como el de los inodos, en cuanto se borra la única entrada que apunta al archivo su espacio queda libre.

## Sincronización entre hilos

El programa usa dos hilos con papeles distintos.

El hilo principal es la interfaz, muestra el menú, le pregunta al usuario qué hacer y arma una `Solicitud` con la operación.

El hilo del disco (`HiloDisco`) es el único que toca la imagen, saca las solicitudes de una cola, las ejecuta una por una y va avisando cuánto lleva.

Para que se comuniquen uso dos mecanismos. El primero es una `queue.Queue`, por donde la interfaz manda las solicitudes y el hilo del disco las recibe, es el patrón productor-consumidor, si la cola está vacía el hilo del disco se queda dormido en `get()` sin gastar procesador. Para terminar el programa la interfaz mete `None` en la cola, el hilo del disco lo toma como señal para cerrar la imagen y salir, la interfaz lo espera con `join()`.

El segundo es una `threading.Condition` dentro de cada `Solicitud`. Mientras copia, el hilo del disco actualiza los bytes que lleva y hace `notify()`, la interfaz está dormida en `wait()` y cada vez que la despiertan dibuja la barra de progreso. Cuando la operación termina el hilo del disco guarda el resultado o el error, marca la solicitud como terminada y vuelve a notificar. Esos campos solo se leen o se escriben teniendo la condición, así la interfaz nunca ve un estado a medias, por ejemplo una solicitud marcada como terminada pero todavía sin su resultado.

Se nota que los dos hilos van a su propio ritmo porque la barra no siempre pasa por todos los porcentajes, si el hilo del disco avisa dos veces antes de que la interfaz alcance a despertar, la interfaz solo dibuja el último avance.

No hizo falta un candado para la imagen porque solo un hilo la usa, las operaciones nunca se pueden encimar porque se atienden en orden desde la cola. Si el hilo del disco se encuentra un error no se cae, se lo regresa a la interfaz dentro de la solicitud, si no la interfaz se quedaría esperando para siempre.

## Decisiones que tomé

Los nombres solo pueden llevar caracteres ASCII imprimibles, además no dejo usar `/` porque al copiar el archivo de regreso a la computadora se confundiría con una carpeta, tampoco dejo que empiecen o terminen con espacios porque se perderían al leerlos.

Al copiar un archivo hacia `FiUnamFS` le pongo como fecha de creación y de modificación la hora actual, igual que cuando se copia un archivo con `cp`.

Cuando hay espacio libre suficiente pero repartido en varios huecos el programa lo dice con un mensaje distinto, para que se entienda por qué no se pudo copiar aunque el listado diga que sí hay espacio.

## Complicaciones que tuve

Cuando empecé el proyecto la imagen de ejemplo todavía no estaba disponible, el planteamiento decía que aún no la publicaban. Para no esperarme armé una imagen de prueba siguiendo la especificación y con ella probé todo, ya que tuve la del profe repetí las pruebas con la suya.

Con la imagen del profe me di cuenta de que no sigue al pie de la letra la especificación en dos cosas. La primera es que las entradas vacías llevan `##############` en el nombre y no `#..............` como dice el planteamiento, mi programa reconoce las dos formas, pero al eliminar escribe como viene en la imagen. La segunda es que los nombres se rellenan con espacios y terminan con un byte nulo (por ejemplo `README.org    \0`), al leer quito los dos y al escribir relleno igual que la imagen, así lo que escribe mi programa se ve igual que lo que ya traía el disco.

La copia de la imagen que estaba usando venía sin permiso de escritura, con eso me di cuenta de que el programa no la podía abrir porque intentaba abrirla para leer y escribir de una vez. Lo cambié para que si no tiene permiso la abra solo para lectura, así todavía se puede listar y copiar hacia la computadora, las operaciones que escriben avisan en lugar de tronar.

Cuando separé el programa en dos hilos la barra de progreso se dibujaba dos veces al llegar al 100%. Pasaba porque la interfaz se despierta tanto con el último aviso de avance como con el aviso de que la operación terminó, en los dos casos dibujaba la barra. Lo arreglé guardando el último avance dibujado para redibujar solo si cambió.

Algo que también tuve que corregir fue el propio README. Al principio me enfoqué en que el código funcionara y lo descuidé un poco, en las primeras etapas solo explicaba cómo usar el programa y cómo funciona, pero no contaba las complicaciones ni las dudas que fueron saliendo. Desde la etapa anterior lo fui mejorando junto con el código, en esta agregué también la explicación de la sincronización entre hilos y los problemas que conozco, para que se entienda el proceso y no solo el resultado.

## Dudas resueltas

La primera vez que corrí el programa no entendía de dónde salía el "Disco de Gunnar" que aparece arriba del menú. Revisando la especificación vi que los bytes 20 a 35 del superbloque son la etiqueta del volumen, el nombre que el profe le puso al disco, el programa solo la lee y la muestra.

Al listar el disco me llamó la atención que `README.org` empieza en el cluster 6 y no en el 5, que es el primero del área de datos. Revisé los bytes del directorio y de verdad dice 6, el cluster 5 simplemente quedó libre. Cuando copié un archivo pequeño el primer ajuste lo acomodó justo ahí, lo que me sirvió para comprobar que la búsqueda de huecos funciona.

La especificación dice que la imagen no tiene tabla de particiones y que hospeda directamente un volumen. Con la clase de sistemas de archivos quedó clara la diferencia, una partición es solo un corte del dispositivo y un volumen es lo que ya tiene formato de un sistema de archivos, por eso aquí el superbloque está desde el byte 0 de la imagen sin nada antes.

## Problemas y mejoras

Hay algunos problemas que conozco y que no alcancé a resolver.

Si un archivo mide 0 bytes el programa le asigna como cluster inicial el primero libre aunque no ocupe ninguno, no afecta nada, pero en el listado puede parecer que comparte cluster con otro archivo.

Si el programa se cierra de golpe a la mitad de una copia hacia `FiUnamFS` (por ejemplo si se apaga la computadora) los datos que alcanzaron a escribirse se quedan en el disco. Como la entrada del directorio se escribe al final el archivo no aparece, ese espacio sigue contando como libre, pero son datos que quedan ahí sin usar.

Los nombres de 15 caracteres ocupan todo el campo y no les queda lugar para el byte nulo que pone la imagen del profe. Mi programa los lee bien, pero no sé si otro programa que espere ese nulo los leería igual.

El hilo del disco atiende una solicitud a la vez y la interfaz se queda esperando, así que mientras copia un archivo no se puede hacer otra cosa.

Para mejorarlo se podría agregar una opción para desfragmentar, que recorra los archivos hacia el inicio del área de datos y junte todos los huecos en uno solo, así nunca fallaría una copia por falta de espacio contiguo.

También estaría bien que el hilo del disco pudiera atender varias solicitudes mientras la interfaz sigue respondiendo, por ejemplo copiar varios archivos en segundo plano.

Otra idea es hacer un módulo de FUSE como los ejemplos que nos mostró el profe. Con `readdir`, `getattr` y `read` ya se podría montar la imagen como una carpeta de solo lectura, agregando `create`, `write` y `unlink` también se podría modificar desde cualquier programa sin pasar por el menú.
