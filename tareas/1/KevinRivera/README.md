Tarea 1: Sincronizacion

Alumno: Rivera Velazquez Brandon Kevin
Materia: Sistemas Operativos
Ejercicio: Santa Claus
Lenguaje: Python 3.9 o posterior
Entorno: Terminal Windows


1. ----------------------------------------Problema elegido----------------------------------------

Santa duerme mientras los elfos construyen juguetes y los nueve renos están de vacaciones.
Un elfo necesita ayuda cuando tiene una duda, pero Santa sólo atiende grupos de **exactamente tres** elfos.
Cuando regresan **los nueve renos**, Santa debe prepararlos para partir. El programa modela estos
personajes como hilos concurrentes con esperas reales. El número de elfos es configurable.


2. ----------------------------------------Cómo ejecutar----------------------------------------

Abrir en una terminal la carpeta que contiene santa_claus.py y ejecutar:

python3 santa_claus.py

Alternativamente, con visual code studio usando la extención de Python

Opciones útiles:

python3 santa_claus.py --elfos 18 --escala 0.4
python3 santa_claus.py --elfos 2 --escala 0.4
python3 santa_claus.py --elfos 12 --semilla 17 --sin-color
python3 -m unittest -v


3. ----------------------------------------Estrategia de sincronización----------------------------------------

Los mecanismos principales son threading.Semaphore y threading.Lock.
También se utilizó threading.Event para iniciar los hilos juntos y anunciar el fin.

Recursos usados:
mutex: Protege la cola de elfos, contadores y resultados compartidos. 
despertar_santa: (inicia en 0) | Mantiene a Santa bloqueado hasta reunir tres solicitudes o nueve renos. 
solicitud_permiso: (uno por elfo, inicia en 0) | Suspende a cada elfo hasta ser atendido o hasta la salida de Santa. 
fin_ayuda: (inicia en 0) | Santa espera la confirmación de los tres elfos del turno. |
permisos_renos: (uno por reno, inicia en 0) | Cada reno espera la autorización de Santa para subir al trineo. 
renos_listos: (inicia en 0) | Santa no despega hasta recibir nueve confirmaciones de abordaje
viaje: (Event) | Marca la partida y evita dejar elfos esperando indefinidamente. 

Procedimiento:

1. Santa se bloquea en despertar_santa.acquire(). No gira revisando variables ni consume CPU esperando.
2. Cada elfo agrega su solicitud a una cola FIFO protegida por mutex y se bloquea en su semáforo personal. Por cada tercer elfo en la cola, se emite una señal para Santa.
3. Santa comprueba bajo mutex si ya regresaron los nueve renos. Si regresaron, elige partir; en caso contrario, toma exactamente los tres elfos más antiguos de la cola.
4. Santa simula la atención y libera los tres semáforos personales. Espera tres confirmaciones antes de comenzar otro grupo.
5. Cada reno regresa en un momento distinto, incrementa el contador protegido y espera su permiso. El noveno despierta a Santa.
6. Al iniciar la salida, Santa despierta a los elfos aún pendientes, deja pasar a los nueve renos y espera sus nueve confirmaciones. Finalmente despega y todos los hilos terminan.

Los if comprueban estados dentro de una sección crítica protegida por Lock;
no reemplazan los semáforos ni constituyen busy waiting.


4. ----------------------------------------Refinamientos implementados----------------------------------------

Prioridad de renos: al tomar una decisión, si los nueve renos ya llegaron, Santa elige el viaje antes de un nuevo grupo de elfos. Si Santa estaba atendiendo a un grupo, termina esa atención y después parte, no interrumpe la ayuda a mitad.
Orden de llegada (FIFO): los grupos se forman con las primeras tres solicitudes pendientes, sin que un elfo que llegó después adelante a los anteriores.
Atención sin superposiciones: Santa espera tres confirmaciones al terminar cada grupo.
Finalización limpia: al anunciar la partida se desbloquean elfos pendientes, y se hace join() de todos los hilos.
Simulación configurable:admite cualquier cantidad no negativa de elfos y diferentes tiempos de espera. Con menos de tres elfos que soliciten ayuda, esos elfos esperan hasta que el viaje provoque el cierre.

5. ----------------------------------------Limitaciones y dudas----------------------------------------

Para acotar la simulación a una Navidad, cada elfo genera una solicitud de ayuda como máximo. Una extensión posible sería permitir múltiples solicitudes por elfo en ciclos de trabajo sucesivos.
Si los nueve renos regresan mientras quedan elfos esperando, sus solicitudes no se atienden: se cancelan al despegar Santa. Esto es deliberado y se indica en la salida.
Los tiempos de llegada son artificiales y sólo sirven para visualizar la concurrencia. El orden preciso de eventos depende del planificador de hilos del sistema operativo.
Sería interesante comparar esta implementación de semáforos con una alternativa basada en variables de condición.

6. ----------------------------------------Verificaciones----------------------------------------

El archivo test_santa.py prueba, con distintas cantidades de elfos y semillas, que:

- Ningún grupo tiene una cantidad diferente de tres elfos.
- Ningún elfo es atendido dos veces y se respeta el orden FIFO.
- Los nueve renos abordan una sola vez, y Santa efectivamente despega.
- Toda solicitud registrada se atiende o se cancela al terminar.

Ejecutar con python3 -m unittest -v desde la misma carpeta.