# Tarea 2: Obteniendo información de un directorio

- Autores: Angel Escobar y Francisco Corona
- Materia: Sistemas Operativos
- Grupo: 7
- Profesor: DR. GUNNAR EYAL WOLF ISZAEVICH
- Facultad de Ingeniería, UNAM

El programa recibe un directorio y un número de días, y lista los archivos de ese directorio que se modificaron en ese tiempo, ordenados por nombre.

Lo hicimos en Python 3 y sólo usa la biblioteca estándar (`os`, `stat`, `sys`, `time` y `math`). Se corre con:

    python3 archivos_recientes.py <directorio> <días>

Por ejemplo, `python3 archivos_recientes.py /tmp 3` muestra lo que cambió en `/tmp` en los últimos 3 días. Los días aceptan decimales, así que con `0.5` salen las últimas 12 horas. Si falta un parámetro, si los días no son un número mayor o igual a cero o si el directorio no existe, el programa imprime cómo se invoca y termina con código 1.

El límite lo sacamos restándole los días (en segundos) a la hora actual. Recorremos el directorio con `os.scandir()` y a cada entrada le pedimos su `stat()` sin seguir ligas simbólicas; así una liga muestra sus propios datos y no los del archivo al que apunta. Guardamos las que tienen `st_mtime` mayor o igual al límite. Si alguna entrada no se puede leer, por permisos o porque se borró mientras recorríamos el directorio, se avisa por la salida de errores y se sigue con las demás.

La tabla tiene las mismas columnas que el ejemplo del enunciado, más una de permisos escrita como en `ls -l` (`-rw-r--r--`), que sale de `stat.filemode()`. El orden es por código de carácter, igual que en el ejemplo, por eso los nombres con mayúscula quedan antes. La columna del nombre mide 30 caracteres, pero se ensancha cuando hay un nombre más largo para que no se desacomode la tabla. Al final se imprime cuántos archivos salieron y cuántos bytes suman.

Lo probamos en Windows. Ahí el modo sale como `100666` para archivos y `040777` para directorios, porque Windows no maneja los permisos como Linux y Python los aproxima.
