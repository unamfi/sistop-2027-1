#include "../include/FiUnamFS.h"

#include <iostream>
#include <thread>

int main() {
    std::cout << "=== PRUEBA DE CONCURRENCIA FIUNAMFS ===\n";

    FiUnamFS fs;

    // Abrir exclusivamente la imagen de pruebas.
    if (!fs.openImage("../fiunamfs_pruebas.img")) {
        std::cerr << "Error: No se pudo abrir la imagen.\n";
        return 1;
    }

    if (!fs.loadSuperBlock() || !fs.validate()) {
        std::cerr << "Error: Sistema de archivos no valido.\n";
        return 1;
    }

    // Cargar el directorio antes de iniciar los hilos.
    fs.loadDirectory();

    std::cout << "\nDirectorio cargado correctamente.\n";
    std::cout << "Iniciando tres hilos...\n";

    // Todos los hilos comparten el mismo objeto FiUnamFS.
    std::thread hilo1([&fs]() {
        std::cout << "\n[Hilo 1] Iniciando eliminacion logica...\n";

        if (fs.deleteFile("hilo_prueba.txt")) {
            std::cout << "[Hilo 1] Eliminacion completada.\n";
        } else {
            std::cout << "[Hilo 1] No se pudo eliminar el archivo.\n";
        }
    });

    std::thread hilo2([&fs]() {
        std::cout << "\n[Hilo 2] Solicitando listado...\n";
        fs.listFiles();
    });

    std::thread hilo3([&fs]() {
        std::cout << "\n[Hilo 3] Solicitando listado...\n";
        fs.listFiles();
    });

    // Esperar a que terminen todos los hilos.
    hilo1.join();
    hilo2.join();
    hilo3.join();

    std::cout << "\nLos tres hilos finalizaron correctamente.\n";
    std::cout << "=== FIN DE LA PRUEBA ===\n";

    return 0;
}
