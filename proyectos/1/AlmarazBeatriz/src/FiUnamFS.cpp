/*
 * Proyecto: (Micro) sistema de archivos multihilos
 * Materia: Sistemas Operativos
 *
 * Autores:
 * - Beatriz Almaraz Garcia
 * - Edson Barragán Galicia
 *
 * Descripción:
 * Implementación de las operaciones básicas para
 * interactuar con el sistema de archivos FiUnamFS.
 */

#include "../include/FiUnamFS.h"
#include "../include/Utils.h"

#include <iostream>

//Abre la imagen binaria del sistema de archivos.
 
bool FiUnamFS::openImage(
    const std::string& path) {
    image.open(
        path,
        std::ios::in |
        std::ios::out |
        std::ios::binary
    );

    return image.is_open();
}

/**
 * Obtiene la información relevante del superbloque.
 *
 * Los desplazamientos utilizados corresponden
 * exactamente a la especificación proporcionada
 * para FiUnamFS.
 */
bool FiUnamFS::loadSuperBlock() {
    if(!image.is_open()) {
        return false;
    }

    // Nombre del sistema de archivos
    image.seekg(0);
    superBlock.fileSystemName =
        readFixedString(image, 8);

    // Versión de implementación
    image.seekg(10);
    superBlock.version =
        readFixedString(image, 4);

    // Etiqueta del volumen
    image.seekg(20);
    superBlock.volumeLabel =
        readFixedString(image, 16);

    // Tamaño de cluster
    image.seekg(40);
    superBlock.clusterSize =
        readLittleEndian32(image);

    // Número de clusters destinados al directorio
    superBlock.directoryClusters =
        readLittleEndian32(image);

    // Número total de clusters del volumen
    superBlock.totalClusters =
        readLittleEndian32(image);

    return true;
}

/**
 * Comprueba que la imagen corresponda
 * a un sistema de archivos compatible.
 */
bool FiUnamFS::validate()
{
    return
        superBlock.fileSystemName ==
        "FiUnamFS"
        &&
        superBlock.version ==
        "27-1";
}

/**
 * Muestra los metadatos principales
 * encontrados en el superbloque.
 */
void FiUnamFS::printInfo() const
{
    std::cout
        << "\n=== SUPERBLOQUE ===\n";

    std::cout
        << "Sistema: "
        << superBlock.fileSystemName
        << '\n';

    std::cout
        << "Version: "
        << superBlock.version
        << '\n';

    std::cout
        << "Etiqueta: "
        << superBlock.volumeLabel
        << '\n';

    std::cout
        << "Tamano de cluster: "
        << superBlock.clusterSize
        << " bytes\n";

    std::cout
        << "Clusters de directorio: "
        << superBlock.directoryClusters
        << '\n';

    std::cout
        << "Clusters totales: "
        << superBlock.totalClusters
        << '\n';
}