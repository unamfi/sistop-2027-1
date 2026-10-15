# Tarea 1: El servidor Web

- Autores: Angel Escobar y Francisco Corona
- Materia: Sistemas Operativos
- Grupo: 7
- Profesor: DR. GUNNAR EYAL WOLF ISZAEVICH
- Facultad de Ingeniería, UNAM

Elegimos el problema del servidor Web (jefe y trabajadores). El jefe lanza k trabajadores que se duermen hasta que llega una conexión. Cuando llega una, el jefe la pone en la cola y despierta a cualquiera de ellos.

Lo hicimos en Python 3, no necesita nada extra. Se corre con:

    python3 servidor_web.py

Usamos semáforos como en el ejemplo de productores y consumidores de clase. El semáforo `hay_conexion` empieza en cero y los trabajadores se quedan dormidos en él; el jefe hace `release()` por cada conexión. La cola está protegida con un mutex. Cada trabajador atiende una sola conexión y termina, así que el jefe lanza uno nuevo cada vez para que siempre haya k disponibles. Al final el jefe manda `None` a los que siguen esperando para que se cierren.

Hicimos el refinamiento: antes de terminar, cada trabajador anota en un reporte (con su propio mutex) qué página atendió y cuánto tardó, y el jefe lo imprime al final.

Duda: el jefe es el hilo principal y no un hilo aparte; no sabemos si eso cuenta igual.
