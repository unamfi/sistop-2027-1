/**
 * Descripción:
 * Punto de entrada principal del programa.
 * En esta etapa del desarrollo el programa:
 *
 * - Abre la imagen FiUnamFS.
 * - Lee y valida el superbloque.
 * - Muestra la información general del volumen.
 * - Lee las entradas del directorio.
 * - Carga en memoria los archivos válidos encontrados.
 *
 * Este avance corresponde al tercer commit funcional del proyecto.
 */

#include "../include/FiUnamFS.h"

#include <iostream>

int main() {
    // Instancia principal del sistema de archivos
    FiUnamFS fs;

    std::cout << "Abriendo imagen FiUnamFS...\n";

    // Intentar abrir la imagen
    if (!fs.openImage("../fiunamfs.img")){
        std::cerr
            << "Error: No se pudo abrir fiunamfs.img\n";

        return 1;
    }

    std::cout << "Imagen abierta correctamente.\n";

    // Leer información del superbloque
    if (!fs.loadSuperBlock()) {
        std::cerr
            << "Error: No fue posible leer el superbloque.\n";

        return 1;
    }

    // Validar que sea una imagen FiUnamFS válida
    if (!fs.validate()) {
        std::cerr
            << "Error: El archivo no corresponde "
            << "a una imagen valida de FiUnamFS.\n";

        return 1;
    }

    std::cout
        << "\nSistema de archivos validado correctamente.\n";

    // Mostrar información general obtenida desde el superbloque.
    fs.printInfo();

    // Leer las entradas de directorio
    // definidas en los clusters 1 al 4.
    fs.loadDirectory();

    // Mostrar archivos encontrados
    fs.listFiles();

    // Mostrar los archivos detectados (salida para depuración).
    //fs.debugDirectory();

    return 0;
}