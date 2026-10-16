- El problema que decidieron resolver:

  Problema del servidor web

- El lenguaje y entorno en que lo desarrollaron.
  - ¿Qué tengo que saber / tener / hacer para ejecutar su programa en mi computadora?
    - **Lenguaje:** Python 3
    - **Entorno:** De multiplataforma, compatible con terminales de varios sistemas operativos
    - **Requisitos:** Tener instalado Python 3, guardar el código fuente como `.py`, para ejecutarlo, en la terminal se debe ir a la ubicación de la carpeta y ejecutar el programa con el comando:
      ```bash
      python servidor.py
      ```

- La estrategia de sincronización (mecanismo / patrón) que emplearon para lograrlo:

  Se utilizó la estrategia de semáforos, usando un semáforo contador que inicia en 0. Los hilos trabajadores invocan `.acquire()` para que se detengan si no está operando, y se ejecuta `.release()` para despertar un hilo disponible. También se emplean cerrojos para proteger las secciones críticas donde se manipula la cola compartida de solicitudes y se escribe en la estructura de contabilidad, previniendo condiciones de carrera. 

- Si están implementando alguno de los refinamientos:

  Sí, implementamos el refinamiento de contabilidad del sistema, ya que cada hilo trabajador, antes de terminar de atender una solicitud, registra de forma segura datos como identificador del trabajador, nombre de la página solicitada y marca de tiempo exacta, en una bitácora global. Además al concluir las tareas y apagar el servidor ordenadamente, el programa despliega un Reporte de Contabilidad detallado que resume el historial de rendimiento de los hilos.

- Cualquier duda que tengan. Si notan que algún pedazo de la implementación podría mejorar, si algo no les terminó de quedar bien...:

  Ninguna duda, todo bien