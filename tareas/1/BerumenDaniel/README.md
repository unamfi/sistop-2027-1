# Tarea: ejercicio de sincronización

Daniel Berumen Valdez

## Problema elegido

Santa Claus. Santa duerme en el Polo Norte y solo se despierta en dos casos:

- cuando regresan los 9 renos de vacaciones, para salir a repartir regalos
- cuando hay 3 elfos con problemas, para ayudarlos (los elfos solo lo molestan de 3 en 3)

Si pasan las dos cosas al mismo tiempo, Santa atiende primero a los renos.

## Lenguaje y cómo ejecutarlo

Python 3, usando solo la biblioteca `threading` (no hay que instalar nada).

    python3 santa.py

Al inicio del archivo se pueden cambiar `NUM_ELFOS` (10) y `NAVIDADES` (3). El programa termina cuando Santa completa todas las navidades.

## Cómo funciona

Cada reno y cada elfo es un hilo. Santa corre en el hilo principal. Todo se sincroniza con semáforos.

Hay dos contadores compartidos, `renos` y `elfos`, que siempre se modifican dentro de `mutex` para que dos hilos no los cambien al mismo tiempo.

**Renos**

1. Se van de vacaciones (un `sleep` aleatorio).
2. Al regresar suman 1 a `renos`. Si es el reno número 9, despierta a Santa con `santa_sem.release()`.
3. Se quedan esperando en `renos_sem` a que Santa los enganche al trineo.
4. Luego esperan en `reparto_sem` a que termine el reparto, y vuelven a irse de vacaciones.

**Elfos**

1. Trabajan un rato (otro `sleep`) hasta que les sale un problema.
2. Pasan por `torniquete_elfos`, que solo deja que se junte un grupo de 3 a la vez.
3. Suman 1 a `elfos`. El primero y el segundo vuelven a soltar el torniquete para que pase el siguiente. El tercero **no lo suelta** y despierta a Santa. Así, si un cuarto elfo tiene un problema, se queda esperando afuera y no se mete al grupo que ya está con Santa.
4. Esperan en `ayuda_sem` a que Santa los ayude.
5. Restan 1 a `elfos`. El último del grupo en salir suelta el torniquete para que se pueda formar el siguiente grupo.
6. Avisan a Santa con `listos_sem` que ya terminaron.

**Santa**

1. Se duerme esperando en `santa_sem`.
2. Cuando lo despiertan revisa los contadores (con el `mutex`):
   - Si `renos == 9`: reinicia el contador, suelta 9 veces `renos_sem` (engancha a los renos), reparte regalos y suelta 9 veces `reparto_sem` para que los renos regresen de vacaciones.
   - Si `elfos == 3`: suelta 3 veces `ayuda_sem` y espera 3 veces `listos_sem`, para no volver a dormirse hasta que los tres elfos ya se fueron.
3. Vuelve a dormir. Repite hasta completar las navidades.

Los renos se revisan primero, por eso tienen prioridad sobre los elfos.

## Semáforos usados

| Semáforo | Valor inicial | Para qué sirve |
|---|---|---|
| `mutex` | 1 | Proteger los contadores `renos` y `elfos` |
| `santa_sem` | 0 | Donde Santa duerme hasta que lo despiertan |
| `renos_sem` | 0 | Los renos esperan a que Santa los enganche |
| `reparto_sem` | 0 | Los renos esperan a que termine el reparto |
| `torniquete_elfos` | 1 | Solo deja que se forme un grupo de 3 elfos a la vez |
| `ayuda_sem` | 0 | Los elfos esperan a que Santa los ayude |
| `listos_sem` | 0 | Santa espera a que los 3 elfos terminen |

La idea de los patrones (mutex, señalización, torniquete) es la que vimos en clase, y la solución se basa en la de *The Little Book of Semaphores* de Allen Downey.

## Ejemplo de salida

    🧝 Elfo 0 tiene un problema (1/3)
    🧝 Elfo 5 tiene un problema (2/3)
    🧝 Elfo 6 tiene un problema (3/3)
    🎅🔧 Santa: ayudando a tres elfos
    🧝✅ Elfo 0 recibe ayuda
    🧝✅ Elfo 5 recibe ayuda
    🧝✅ Elfo 6 recibe ayuda
    🎅💤 Santa se va a dormir
    🦌 Reno 2 regresa de vacaciones (9/9)
    🎅🛷 Santa: llegaron los renos, a repartir regalos (navidad 3)
    🎅🎁 Santa: regalos entregados
    🎄 Fin

## Refinamientos

Ninguno (este problema no plantea refinamientos en la presentación).

## Dudas y cosas que se pueden mejorar

Los hilos de renos y elfos son `daemon` porque son ciclos infinitos. Así el programa termina cuando Santa completa sus navidades, sin tener que cortarlo con Ctrl+C.

Por lo mismo, si al acabar la última navidad hay elfos esperando (por ejemplo, ya iban 3/3 mientras Santa repartía), el programa termina y esos elfos se quedan sin ayuda:

    🦌 Reno 5 regresa de vacaciones (9/9)
    🎅🛷 Santa: llegaron los renos, a repartir regalos (navidad 3)
    🧝 Elfo 7 tiene un problema (3/3)
    🎅🎁 Santa: regalos entregados
    🎄 Fin

Se podría arreglar haciendo que Santa revise si quedó un grupo de elfos pendiente antes de terminar, o avisándoles a los hilos que ya se acabó (con un `Event`) y haciendo `join`, pero no lo implementé.