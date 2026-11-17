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
bool FiUnamFS::validate() {
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
void FiUnamFS::printInfo() const {
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

void FiUnamFS::loadDirectory() {
    // Limpiar información previa
    files.clear();

    /*
     * El directorio comienza en el cluster 1.
     * Cluster: 2048 bytes
     */
    image.seekg(2048);

    for(int i = 0; i < 128; i++) {
        DirectoryEntry entry;

        // Tipo de entrada
        image.read(
            &entry.type,
            1
        );

        // Si la entrada está vacía, avanzamos hasta la siguiente.
        if(entry.type != 'F') {
            image.seekg(
                63,
                std::ios::cur
            );

            continue;
        }

        // Nombre (15 bytes)
        entry.filename =
            readFixedString(
                image,
                15
            );

        // Tamaño del archivo
        entry.size =
            readLittleEndian32(
                image
            );

        //Cluster inicial
        entry.startCluster =
            readLittleEndian32(
                image
            );

        // Fecha de creación
        entry.creationDate =
            readFixedString(
                image,
                14
            );

        // Fecha de modificación
        entry.modificationDate =
            readFixedString(
                image,
                14
            );

        // Área reservada
        image.seekg(
            12,
            std::ios::cur
        );

        files.push_back(entry);
    }
}

void FiUnamFS::debugDirectory() const {
    std::cout
        << "\nArchivos encontrados: "
        << files.size()
        << "\n\n";

    for(const auto& file : files) {
        std::cout
            << file.filename
            << '\n';
    }
}