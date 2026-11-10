#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define MAX_GATOS 30
#define MAX_RATONES 30
#define MAX_PLATOS 10
#define MAX_COMIDAS 10

typedef enum { GATO, RATON } Especie;
typedef struct { int id; Especie especie; int comidas; unsigned int semilla; } Animal;

static int platos_total, comidas_por_animal;
static HANDLE puerta, sala, mutex_gatos, mutex_ratones, mutex_plato, mutex_salida;
static HANDLE *platos;
static int gatos_activos, ratones_activos, siguiente_plato;

static void imprimir(const char *formato, const char *nombre, int id, int plato, int comidas) {
    WaitForSingleObject(mutex_salida, INFINITE);
    if (plato >= 0) printf(formato, nombre, id, plato + 1);
    else if (comidas >= 0) printf(formato, nombre, id, comidas);
    else printf(formato, nombre, id);
    fflush(stdout);
    ReleaseMutex(mutex_salida);
}
static void pausa_aleatoria(unsigned int *semilla, int minimo_ms, int rango_ms) {
    *semilla = *semilla * 1103515245u + 12345u;
    Sleep((DWORD)(minimo_ms + (*semilla % (unsigned int)rango_ms)));
}
static int entrar_comedor(Especie especie) {
    HANDLE mutex_especie = especie == GATO ? mutex_gatos : mutex_ratones;
    int *activos = especie == GATO ? &gatos_activos : &ratones_activos;
    WaitForSingleObject(puerta, INFINITE);
    WaitForSingleObject(mutex_especie, INFINITE);
    if (*activos == 0) {
        ReleaseMutex(mutex_especie);
        WaitForSingleObject(sala, INFINITE);
        WaitForSingleObject(mutex_especie, INFINITE);
    }
    ++*activos;
    ReleaseMutex(mutex_especie);
    ReleaseSemaphore(puerta, 1, NULL);
    return 0;
}
static void salir_comedor(Especie especie) {
    HANDLE mutex_especie = especie == GATO ? mutex_gatos : mutex_ratones;
    int *activos = especie == GATO ? &gatos_activos : &ratones_activos;
    WaitForSingleObject(mutex_especie, INFINITE);
    --*activos;
    if (*activos == 0) ReleaseSemaphore(sala, 1, NULL);
    ReleaseMutex(mutex_especie);
}
static int elegir_plato(void) {
    WaitForSingleObject(mutex_plato, INFINITE);
    int plato = siguiente_plato;
    siguiente_plato = (siguiente_plato + 1) % platos_total;
    ReleaseMutex(mutex_plato);
    return plato;
}
static DWORD WINAPI rutina_animal(LPVOID argumento) {
    Animal *animal = (Animal *)argumento;
    const char *nombre = animal->especie == GATO ? "Gato" : "Raton";
    for (int i = 0; i < comidas_por_animal; ++i) {
        pausa_aleatoria(&animal->semilla, 100, 400);
        imprimir("%-5s %02d quiere comer.\n", nombre, animal->id, -1, -1);
        entrar_comedor(animal->especie);
        int plato = elegir_plato();
        WaitForSingleObject(platos[plato], INFINITE);
        imprimir("  -> %-5s %02d come en el plato %d.\n", nombre, animal->id, plato, -1);
        pausa_aleatoria(&animal->semilla, 150, 350);
        imprimir("  <- %-5s %02d deja el plato %d.\n", nombre, animal->id, plato, -1);
        ReleaseSemaphore(platos[plato], 1, NULL);
        salir_comedor(animal->especie);
        ++animal->comidas;
    }
    imprimir("%-5s %02d terminó: %d comida(s).\n", nombre, animal->id, -1, animal->comidas);
    return 0;
}
static int leer_entero(const char *mensaje, int minimo, int maximo) {
    char linea[128];
    for (;;) {
        char *fin; long valor;
        printf("%s", mensaje); fflush(stdout);
        if (!fgets(linea, sizeof linea, stdin)) return -1;
        valor = strtol(linea, &fin, 10);
        while (*fin == ' ' || *fin == '\t' || *fin == '\n' || *fin == '\r') ++fin;
        if (fin != linea && *fin == '\0' && valor >= minimo && valor <= maximo) return (int)valor;
        printf("Ingresa un entero entre %d y %d.\n", minimo, maximo);
    }
}
int main(void) {
    int gatos, ratones, total, creados = 0, error = 0;
    HANDLE *hilos = NULL;
    Animal *animales = NULL;
    printf("\nGATOS Y RATONES\nLos gatos y los ratones usan el comedor por turnos.\nCada plato solo puede ser usado por un animal a la vez.\n\n");
    gatos = leer_entero("Cantidad de gatos (1-30): ", 1, MAX_GATOS); if (gatos < 0) return 1;
    ratones = leer_entero("Cantidad de ratones (1-30): ", 1, MAX_RATONES); if (ratones < 0) return 1;
    platos_total = leer_entero("Cantidad de platos (1-10): ", 1, MAX_PLATOS); if (platos_total < 0) return 1;
    comidas_por_animal = leer_entero("Comidas por animal (1-10): ", 1, MAX_COMIDAS); if (comidas_por_animal < 0) return 1;
    total = gatos + ratones;
    platos = (HANDLE *)calloc((size_t)platos_total, sizeof *platos);
    hilos = (HANDLE *)calloc((size_t)total, sizeof *hilos);
    animales = (Animal *)calloc((size_t)total, sizeof *animales);
    if (!platos || !hilos || !animales) { fprintf(stderr, "No se pudo reservar memoria.\n"); error = 1; goto fin; }
    puerta = CreateSemaphore(NULL, 1, 1, NULL); sala = CreateSemaphore(NULL, 1, 1, NULL);
    mutex_gatos = CreateMutex(NULL, FALSE, NULL); mutex_ratones = CreateMutex(NULL, FALSE, NULL);
    mutex_plato = CreateMutex(NULL, FALSE, NULL); mutex_salida = CreateMutex(NULL, FALSE, NULL);
    if (!puerta || !sala || !mutex_gatos || !mutex_ratones || !mutex_plato || !mutex_salida) { fprintf(stderr, "No se pudieron crear los objetos de sincronizacion.\n"); error = 1; goto fin; }
    for (int i = 0; i < platos_total; ++i) { platos[i] = CreateSemaphore(NULL, 1, 1, NULL); if (!platos[i]) { fprintf(stderr, "No se pudo crear el semaforo de un plato.\n"); error = 1; goto fin; } }
    printf("\n--- Inicio de la simulacion ---\n");
    for (int i = 0; i < gatos + ratones; ++i) {
        animales[i].id = i < gatos ? i + 1 : i - gatos + 1;
        animales[i].especie = i < gatos ? GATO : RATON;
        animales[i].semilla = (unsigned int)time(NULL) ^ ((unsigned int)(i + 1) * 2654435761u);
        hilos[i] = CreateThread(NULL, 0, rutina_animal, &animales[i], 0, NULL);
        if (!hilos[i]) { fprintf(stderr, "No se pudo crear el hilo %d.\n", i + 1); error = 1; break; }
        ++creados;
    }
    if (creados > 0) WaitForMultipleObjects((DWORD)creados, hilos, TRUE, INFINITE);
    printf("\nRESUMEN\n");
    for (int i = 0; i < creados; ++i) {
        printf("%s %02d: %d de %d comidas\n", animales[i].especie == GATO ? "Gato " : "Raton", animales[i].id, animales[i].comidas, comidas_por_animal);
        if (animales[i].comidas != comidas_por_animal) error = 1;
    }
    for (int i = 0; i < creados; ++i) CloseHandle(hilos[i]);
fin:
    if (platos) { for (int i = 0; i < platos_total; ++i) if (platos[i]) CloseHandle(platos[i]); }
    if (puerta) {
        CloseHandle(puerta);
    }
    if (sala) {
        CloseHandle(sala);
    }
    if (mutex_gatos) {
        CloseHandle(mutex_gatos);
    }
    if (mutex_ratones) {
        CloseHandle(mutex_ratones);
    }
    if (mutex_plato) {
        CloseHandle(mutex_plato);
    }
    if (mutex_salida) {
        CloseHandle(mutex_salida);
    }
    free(platos);
    free(hilos);
    free(animales);
    if (error) { fprintf(stderr, "La ejecucion termino con errores.\n"); return 1; }
    printf("\nSimulacion finalizada correctamente.\n"); return 0;
}
