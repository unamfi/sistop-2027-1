\# Tarea 1: Ejercicios de sincronización



\*\*Alumno:\*\* Francisco Hernández Moguel  

\*\*Asignatura:\*\* Sistemas Operativos  

\*\*Profesor:\*\* Gunnar Wolf  

\*\*Semestre:\*\* 2027-1



\## Problema seleccionado



Se seleccionó el problema 5, \*\*El servidor Web\*\*, que consiste en simular el modelo jefe-trabajador mediante programación concurrente.



El programa crea inicialmente tres trabajadores, quienes permanecen bloqueados hasta recibir una solicitud. El hilo jefe distribuye las tareas y procura mantener tres trabajadores disponibles, respetando un máximo de ocho.



\## Lenguaje y ejecución



El programa está desarrollado en \*\*Python 3\*\*, utilizando las bibliotecas estándar `threading`, `queue`, `tkinter`, `random` y `time`, entre otras.



Se desarrolló y probó en Windows mediante Visual Studio.



Para ejecutarlo:



```bash

py servidor\_web.py

```



Se requiere Python 3 con soporte para Tkinter. No es necesario instalar paquetes externos mediante pip.



\## Estrategia de sincronización



Se utilizaron:



\- \*\*Semáforos:\*\* permiten bloquear y despertar a los trabajadores mediante `acquire()` y `release()`.

\- \*\*Variables de condición:\*\* permiten que el jefe espere hasta que exista un trabajador disponible.

\- \*\*Exclusión mutua:\*\* protege las estructuras compartidas.

\- \*\*Cola sincronizada:\*\* almacena las solicitudes pendientes.



No se utiliza espera activa para coordinar los hilos.



\## Refinamiento implementado



\*\*Se implementó el refinamiento de seguimiento y contabilidad del rendimiento solicitado en el ejercicio.\*\*



Cada trabajador registra las solicitudes atendidas, las páginas procesadas y los tiempos empleados.



Antes de finalizar, cada hilo notifica sus estadísticas individuales. Posteriormente, el programa genera un informe general mediante un cierre ordenado.



Durante una de las pruebas finales se recibieron y atendieron correctamente \*\*56 solicitudes\*\*, y los \*\*8 trabajadores\*\* entregaron sus informes.



\## Interfaz gráfica



Se desarrolló una interfaz mediante Tkinter que permite visualizar los trabajadores, generar solicitudes y observar las estadísticas e historial de ejecución.



\## Limitaciones y posibles mejoras



El programa simula solicitudes Web, pero no implementa conexiones HTTP reales.



Como posibles mejoras se contempla permitir la configuración dinámica del número máximo de trabajadores y agregar pruebas automatizadas de concurrencia.



\## Uso de inteligencia artificial



Se utilizó ChatGPT como herramienta de apoyo para el diseño e implementación del programa, la arquitectura jefe-trabajador, el desarrollo de la interfaz gráfica con Tkinter, la comprensión de los mecanismos de sincronización y la elaboración de la documentación.



Se realizaron pruebas manuales de funcionamiento para observar el comportamiento de los trabajadores y verificar los informes generados.



\## Documentación



El archivo `Reporte\_Servidor\_Web.pdf` contiene la explicación detallada del proyecto, la arquitectura del código, los mecanismos de sincronización, el refinamiento y las evidencias de las pruebas realizadas.

