\# Proyecto: (Micro) sistema de archivos multihilos — FiUnamFS



\*\*Autora:\*\* Frida Monserrat Díaz Huerta  

\*\*Materia:\*\* Sistemas Operativos (Semestre 2027-1)



\## Entorno y dependencias

\- \*\*Lenguaje:\*\* Python 3 (biblioteca estándar únicamente: `os`, `sys`, `struct`, `math`, `threading`, `queue`, `datetime`).

\- \*\*Dependencias externas:\*\* Ninguna.



\## Estrategia y diseño del sistema de archivos

\- \*\*Volumen y geometría:\*\* Imagen simulada de `1440 KiB` (`1,474,560` bytes), dividida en sectores de `512` bytes y clusters de `4` sectores (`2048` bytes, `720` clusters en total).

\- \*\*Superbloque (Cluster #0):\*\* Valida firma `FiUnamFS` (`0–7`), versión `27-1` (`10–13`), tamaño de cluster (`40–43`), clusters de directorio (`44–47`) y total de clusters (`48–51`).

\- \*\*Directorio plano (Clusters 1–4):\*\* `128` entradas de `64` bytes cada una (`F` para archivo activo, `-` para entrada libre, nombre ASCII de hasta `15` bytes, tamaño y cluster inicial en \*little-endian\* `<I`, y marcas de tiempo `AAAAMMDDHHMMSS`).

\- \*\*Asignación contigua (Clusters 5–719):\*\* Localiza bloques contiguos libres suficientes para almacenar cada archivo sin fragmentar su contenido.



\## Sincronización entre hilos

\- Las operaciones se despachan a hilos trabajadores (`threading.Thread`) mediante una cola segura (`queue.Queue`).

\- El acceso concurrente a la imagen del disco se coordina con un cerrojo (`threading.Lock`) y una variable de condición (`threading.Condition`) junto con un contador de hilos activos (`active\_workers`), evitando condiciones de carrera y reportando inicio y fin de cada operación por hilo.



\## Ejemplos de uso

\- \*\*Listar contenido:\*\* `python fiunamfs.py <disco.img> ls`

\- \*\*Copiar desde FiUnamFS al equipo:\*\* `python fiunamfs.py <disco.img> get <archivo\_fs> <destino\_local>`

\- \*\*Copiar desde el equipo a FiUnamFS:\*\* `python fiunamfs.py <disco.img> put <archivo\_local> \[nombre\_fs]`

\- \*\*Eliminar archivo de FiUnamFS:\*\* `python fiunamfs.py <disco.img> rm <archivo\_fs>`


## Notas de implementación
- Validación estricta del superbloque (FiUnamFS y versión 27-1) antes de escribir.
- Enteros de 32 bits en formato little-endian (<I) y asignación contigua de clústeres.
