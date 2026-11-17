/**
 * Proyecto: Implementación de FiUnamFS
 * Materia: Sistemas Operativos
 *
 * Descripción:
 * Punto de entrada principal del programa.
 * Para este segundo commit únicamente se realiza:
 *
 * - Apertura de la imagen
 * - Lectura del superbloque
 * - Validación del sistema de archivos
 * - Impresión de la información obtenida
 */

#include "../include/FiUnamFS.h"

#include <iostream>

int main()
{
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
    if (!fs.loadSuperBlock())
    {
        std::cerr
            << "Error: No fue posible leer el superbloque.\n";

        return 1;
    }

    // Validar que sea una imagen FiUnamFS válida
    if (!fs.validate())
    {
        std::cerr
            << "Error: El archivo no corresponde "
            << "a una imagen valida de FiUnamFS.\n";

        return 1;
    }

    std::cout
        << "\nSistema de archivos validado correctamente.\n";

    // Mostrar información obtenida
    fs.printInfo();

    return 0;
}