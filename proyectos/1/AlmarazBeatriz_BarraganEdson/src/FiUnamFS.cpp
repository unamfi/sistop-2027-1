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

#include <iomanip>
#include <iostream>
#include <algorithm>
#include <filesystem>
#include <vector>
#include <cstdint>

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

//Obtiene la información relevante del superbloque.
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

     
        // Eliminar espacios de relleno del nombre.
        const auto lastCharacter =
            entry.filename.find_last_not_of(' ');

        if (lastCharacter != std::string::npos) {
            entry.filename.erase(lastCharacter + 1);
        } else {
            entry.filename.clear();
        }



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

/**
 * Muestra los archivos almacenados
 * en memoria de forma tabulada.
 */
void FiUnamFS::listFiles() const {
    std::cout
        << "\n========================================\n";

    std::cout
        << "      ARCHIVOS EN FIUNAMFS\n";

    std::cout
        << "========================================\n\n";

    std::cout
        << std::left
        << std::setw(18) << "Nombre"
        << std::setw(18) << "Tamano"
        << std::setw(18) << "Cluster"
        << '\n';

    std::cout
        << "--------------------------------------------------\n";

    for(const auto& file : files) {
        std::cout
            << std::left
            << std::setw(18) << file.filename
            << std::setw(18) << file.size
            << std::setw(18) << file.startCluster
            << '\n';
    }

    std::cout
        << "\nTotal de archivos: "
        << files.size()
        << '\n';
}

/**
 * Exporta un archivo desde FiUnamFS al sistema anfitrion.
 * Lee los datos directamente desde la imagen binaria.
 */
bool FiUnamFS::exportFile(
    const std::string& filename,
    const std::string& destination
) {
    // Buscar el archivo en el directorio cargado.
    auto it = std::find_if(
        files.begin(),
        files.end(),
        [&](const DirectoryEntry& entry) {
            return entry.filename == filename;
        }
    );

    if (it == files.end()) {
        std::cerr << "Error: Archivo no encontrado.\n";
        return false;
    }

    if (!image.is_open() || !validate()) {
        std::cerr << "Error: Imagen no valida o no abierta.\n";
        return false;
    }

    // Comprobar que los datos esten dentro del volumen.
    const uint64_t clusterSize = superBlock.clusterSize;
    const uint64_t volumeSize =
        clusterSize * superBlock.totalClusters;
    const uint64_t offset =
        static_cast<uint64_t>(it->startCluster) * clusterSize;

    if (clusterSize == 0 ||
        it->startCluster < 1 + superBlock.directoryClusters ||
        offset > volumeSize ||
        it->size > volumeSize - offset) {
        std::cerr << "Error: Ubicacion del archivo invalida.\n";
        return false;
    }

    // Evitar sobrescribir un archivo existente.
    if (std::filesystem::exists(destination)) {
        std::cerr << "Error: El destino ya existe.\n";
        return false;
    }

    // Leer primero todos los bytes del archivo.
    std::vector<char> data(it->size);

    image.clear();
    image.seekg(static_cast<std::streamoff>(offset));

    if (!image) {
        std::cerr << "Error: No se pudo localizar el archivo.\n";
        return false;
    }

    if (!data.empty()) {
        image.read(data.data(),
                   static_cast<std::streamsize>(data.size()));

        if (!image) {
            std::cerr << "Error: Lectura incompleta.\n";
            return false;
        }
    }

    // Crear el archivo de salida en Windows.
    std::ofstream output(destination, std::ios::binary);

    if (!output.is_open()) {
        std::cerr << "Error: No se pudo crear el destino.\n";
        return false;
    }

    if (!data.empty()) {
        output.write(data.data(),
                     static_cast<std::streamsize>(data.size()));
    }

    output.close();

    if (!output) {
        std::cerr << "Error: No se pudo guardar el archivo.\n";
        return false;
    }

    std::cout << "Archivo exportado correctamente: "
              << destination << '\n';

    return true;
}

