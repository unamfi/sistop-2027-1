# Gatos y ratones

## Problema elegido

El programa simula un comedor al que entran gatos y ratones. Las dos especies no pueden ocuparlo al mismo tiempo. Los animales de una misma especie pueden comer en paralelo, pero cada plato solo puede ser usado por un animal a la vez.

## Requisitos

El código de esta versión está preparado para Windows y MinGW, usando la API de hilos y sincronización de Windows. No necesita `pthread.h`.

## Compilar y ejecutar en Windows

Abre PowerShell en esta carpeta y ejecuta:

```powershell
gcc -std=c11 -Wall -Wextra -Wpedantic gatos_ratones.c -o gatos_ratones.exe
.\gatos_ratones.exe
```

El programa pide la cantidad de gatos, ratones, platos y comidas por animal.

## Cómo se sincroniza

- `sala` impide que gatos y ratones ocupen el comedor al mismo tiempo.
- `puerta` coordina las entradas.
- `mutex_gatos` y `mutex_ratones` protegen los contadores de cada especie.
- Cada semáforo de `platos` permite que solo un animal use ese plato a la vez.
- `mutex_plato` protege la selección circular de platos.
- `mutex_salida` evita que los mensajes se mezclen.

Cada animal se ejecuta en su propio hilo. Las pausas solo hacen visible la concurrencia; la exclusión se controla con los objetos de sincronización.

## Decisiones y limitaciones

Se permite que varios animales de la misma especie estén en el comedor a la vez. La selección de platos es circular. La API de sincronización no garantiza por sí sola un orden FIFO estricto, por lo que no se afirma una garantía absoluta contra la inanición.

## Archivos

- `gatos_ratones.c`: código fuente.
- `README.md`: instrucciones y explicación.
- `Makefile`: se conserva para entornos compatibles con make.
