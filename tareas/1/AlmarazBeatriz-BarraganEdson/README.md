# Simulación de servidor concurrente: modelo jefe–trabajador
Alumnos: Almaraz García Beatriz
        Barragán Galicia Edson

Materia: Sistemas operativos 2027-1

Profesor: Gunnar Wolf

Fecha de entrega: 15 de octubre de 2026

## Problema que decidimos resolver

El problema consiste en **modelar la interacción entre un jefe y varios hilos trabajadores**, utilizando mecanismos de sincronización. Nos inspiramos en el funcionamiento de servidores que deben atender varias solicitudes sin procesarlas todas de manera secuencial.

De acuerdo con el planteamiento de la práctica, el jefe inicia `k` trabajadores, los trabajadores sin tareas esperan, y cuando llega una solicitud se despierta a un trabajador para atenderla. También consideramos un refinamiento de **contabilidad del trabajo realizado**.

Nuestra implementación **simula** las conexiones mediante solicitudes de páginas web: no abre un puerto ni acepta conexiones de red reales. El hilo principal actúa como jefe y genera 20 solicitudes; cuatro trabajadores las consumen concurrentemente.

## Lenguaje, entorno y ejecución

- **Lenguaje:** C++ (estándar C++17). 
Nota: No quisimos usar otro lenguaje porque sería más "talachudo" jaja.
- **Sistema operativo de trabajo:** Linux.
- **Compilador:** `g++` con soporte de hilos POSIX (`-pthread`).
- **Bibliotecas:** biblioteca estándar de C++ (`thread`, `mutex`, `condition_variable`, `queue`, `map`, etc.). No se requieren bibliotecas externas.

### Requisitos

Tener una terminal Linux y el compilador `g++` instalado. En distribuciones basadas en Debian o Ubuntu, si hace falta:

```bash
sudo apt update
sudo apt install g++
```

### Compilación

Desde la carpeta raíz del proyecto, donde está `main.cpp`:

```bash
mkdir -p build
g++ -std=c++17 -Wall -Wextra -pedantic -pthread \
    main.cpp src/server.cpp src/trabajador.cpp src/stats.cpp \
    -o build/servidor
```

### Ejecución

```bash
./build/servidor
```

### Organización de la tarea

```text
.
├── main.cpp               # Hilo jefe y creación de trabajadores
├── include/
│   ├── Request.h          # Estructura de cada solicitud
│   ├── Trabajador.h       # Declaración del trabajador
│   ├── server.h           # Cola y sincronización
│   └── stats.h            # Estadísticas
├── src/
│   ├── trabajador.cpp     # Trabajo de cada hilo
│   ├── server.cpp         # Encolado, espera y cierre
│   └── stats.cpp          # Registro y reporte
├── build/                 # Ejecutables generados (ignorados por Git)
└── README.md
```

## Estrategia de sincronización

Utilizamos el **patrón productor–consumidor**, como implementación del modelo **jefe–trabajador**:

1. El hilo principal (jefe) crea **4 hilos trabajadores**.
2. El jefe genera **20 solicitudes**, una cada 500 ms aproximadamente, y las agrega a una cola compartida (`std::queue<Request>`).
3. El acceso a la cola se protege con `std::mutex` para impedir modificaciones simultáneas.
4. Los trabajadores sin solicitudes quedan bloqueados en `std::condition_variable::wait()`, sin consumir CPU en espera activa.
5. Cuando el jefe agrega una solicitud, llama a `notify_one()` para despertar a un trabajador. El trabajador toma una solicitud de la cola y simula su atención durante un intervalo de 1 a casi 4 segundos.
6. Al terminar de atenderla, el trabajador registra la página procesada y su identificador en las estadísticas, protegidas con otro mutex.
7. Tras generar todas las solicitudes, el jefe activa el cierre (`shutdown()`), despierta a los trabajadores (`notify_all()`), espera a que terminen con `join()` y muestra el reporte final.

**Asignación de trabajo:** el jefe no selecciona explícitamente a un trabajador por identificador. En cambio, cualquier trabajador disponible puede tomar la siguiente solicitud de la cola; la variable de condición permite despertar a uno de los que esperan. Esto cumple la idea de asignar trabajo a un trabajador disponible, aunque no implementa una asignación dirigida.

**Cantidad de trabajadores:** la implementación mantiene **4 hilos creados durante toda la simulación**. No crea hilos adicionales para reponer inmediatamente los ocupados, por lo que no garantiza cuatro trabajadores *libres* en todo momento.

## Refinamiento implementado: seguimiento y contabilidad

Sí se implementó el refinamiento de **estadísticas de rendimiento** mediante la clase `Statistics`:

- Cuenta el total de solicitudes atendidas.
- Cuenta cuántas veces se solicitó cada página (`/`, `/login`, `/products`, `/cart`, `/contact`).
- Cuenta cuántas solicitudes procesó cada trabajador.
- Imprime un reporte al terminar la ejecución.

Los trabajadores actualizan el registro **después de terminar cada solicitud**, antes de atender la siguiente o salir. El registro es seguro frente a accesos simultáneos porque usa un mutex. El reporte se genera después de que todos los hilos han terminado.

**Alcance del refinamiento:** el código contabiliza solicitudes, páginas y trabajo por hilo; no calcula tiempos promedio, latencia ni uso de CPU. Tampoco envía una notificación separada al jefe al finalizar el hilo: el jefe espera su finalización mediante `join()`.


### Conclusión

La tarea nos ayudó a comprender cómo coordinar un hilo jefe y varios trabajadores utilizando una cola compartida, mutex y variables de condición. También observamos la atención concurrente de solicitudes y consultar estadísticas finales, con las limitaciones propias de una simulación académica.
