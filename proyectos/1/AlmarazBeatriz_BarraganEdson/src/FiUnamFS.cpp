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
#include <ctime>
#include <mutex>
#include <string>

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
    // Lectura protegida del directorio.
// Evita que otros hilos modifiquen la imagen durante la lectura.
void FiUnamFS::loadDirectory() {
    std::lock_guard<std::mutex> lock(imageMutex);

    loadDirectoryUnlocked();
}

void FiUnamFS::loadDirectoryUnlocked() {
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

   // Evitar que el directorio cambie mientras se listan los archivos.
    std::lock_guard<std::mutex> lock(imageMutex);
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
    // Proteger la exportacion frente a operaciones concurrentes.
    std::lock_guard<std::mutex> lock(imageMutex);

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

/**
 * Importa un archivo desde Windows hacia FiUnamFS.
 */
bool FiUnamFS::importFile(
    const std::string& source,
    const std::string& filename
) {
    // Evitar que otros hilos modifiquen la imagen
    // mientras se realiza una importacion.
    std::lock_guard<std::mutex> lock(imageMutex);

    // Comprobar que la imagen este abierta y sea valida.
    if (!image.is_open() || !validate()) {
        std::cerr << "Error: Imagen no valida o no abierta.\n";
        return false;
    }

    // Comprobar que el archivo exista en Windows.
    std::ifstream input(source, std::ios::binary);

    if (!input.is_open()) {
        std::cerr << "Error: No se pudo abrir el archivo de origen.\n";
        return false;
    }

    // Verificar que el nombre sea valido para FiUnamFS.
    if (filename.empty() || filename.size() > 15 ||
        filename == "." || filename == ".." ||
        filename.find_first_of("/\\") != std::string::npos) {
        std::cerr << "Error: Nombre de archivo invalido.\n";
        return false;
    }

    // Evitar nombres duplicados.
    const auto duplicate = std::find_if(
        files.begin(),
        files.end(),
        [&](const DirectoryEntry& entry) {
            return entry.filename == filename;
        }
    );

    if (duplicate != files.end()) {
        std::cerr << "Error: Ya existe un archivo con ese nombre.\n";
        return false;
    }

    // Obtener el tamano del archivo de origen.
    input.seekg(0, std::ios::end);
    const std::streampos fileSize = input.tellg();

    if (fileSize < 0 ||
        static_cast<uint64_t>(fileSize) > UINT32_MAX) {
        std::cerr << "Error: Tamano de archivo invalido.\n";
        return false;
    }

    const uint32_t size = static_cast<uint32_t>(fileSize);
    input.seekg(0, std::ios::beg);
    
    // Por ahora no se permite importar archivos vacios.
    if (size == 0) {
        std::cerr << "Error: No se pueden importar archivos vacios.\n";
        return false;
    }
        // Cargar el contenido del archivo en memoria.
    std::vector<char> data(size);

    if (!data.empty()) {
        input.read(
            data.data(),
            static_cast<std::streamsize>(data.size())
        );

        if (!input) {
            std::cerr << "Error: No se pudo leer completamente "
                      << "el archivo de origen.\n";
            return false;
        }
    }

    std::cout << "Archivo de origen leido correctamente.\n";

    // Calcular cuantos clusters necesitamos.
    const uint32_t clusterSize = superBlock.clusterSize;

    if (clusterSize == 0 || superBlock.totalClusters == 0) {
        std::cerr << "Error: Geometria del volumen invalida.\n";
        return false;
    }

    const uint64_t requiredClusters =
        (static_cast<uint64_t>(size) + clusterSize - 1)
        / clusterSize;

    // El primer cluster de datos va despues del directorio.
    const uint64_t firstDataCluster =
        1ULL + superBlock.directoryClusters;

    // Buscar un espacio continuo que no se cruce con otros archivos.
    uint64_t freeCluster = 0;

    for (uint64_t candidate = firstDataCluster;
         candidate < superBlock.totalClusters;
         ++candidate) {

        if (requiredClusters >
            static_cast<uint64_t>(superBlock.totalClusters) - candidate) {
            break;
        }

        bool occupied = false;

        for (const auto& entry : files) {
            const uint64_t usedClusters =
                (static_cast<uint64_t>(entry.size) + clusterSize - 1)
                / clusterSize;

            const uint64_t usedStart = entry.startCluster;
            const uint64_t usedEnd = usedStart + usedClusters;
            const uint64_t candidateEnd = candidate + requiredClusters;

            if (candidate < usedEnd && usedStart < candidateEnd) {
                occupied = true;
                break;
            }
        }

        if (!occupied) {
            freeCluster = candidate;
            break;
        }
    }

    if (freeCluster == 0) {
        std::cerr << "Error: No hay espacio continuo suficiente.\n";
        return false;
    }
        // Buscar una entrada libre dentro del directorio.
    const uint64_t directoryStart = clusterSize;
    const uint64_t directorySize =
        static_cast<uint64_t>(superBlock.directoryClusters) * clusterSize;

    const uint64_t entrySize = 64;
    const uint64_t totalEntries = directorySize / entrySize;

    uint64_t freeEntryOffset = 0;
    bool foundFreeEntry = false;

    for (uint64_t i = 0; i < totalEntries; ++i) {
        const uint64_t offset =
            directoryStart + i * entrySize;

        char type = '\0';

        image.clear();
        image.seekg(static_cast<std::streamoff>(offset));
        image.read(&type, 1);

        if (!image) {
            std::cerr << "Error: No se pudo leer el directorio.\n";
            return false;
        }

        // Las entradas que no son archivos activos estan disponibles.
        if (type != 'F') {
            freeEntryOffset = offset;
            foundFreeEntry = true;
            break;
        }
    }

    if (!foundFreeEntry) {
        std::cerr << "Error: El directorio de FiUnamFS esta lleno.\n";
        return false;
    }

    std::cout << "Entrada libre encontrada en byte: "
              << freeEntryOffset << '\n';

    std::cout << "Archivo de origen: " << source << '\n';
    std::cout << "Nombre en FiUnamFS: " << filename << '\n';
    std::cout << "Tamano: " << size << " bytes\n";
    std::cout << "Clusters necesarios: " << requiredClusters << '\n';
    std::cout << "Primer cluster disponible: " << freeCluster << '\n';

        // Calcular la posicion donde se guardara el archivo.
    const uint64_t dataOffset =
        freeCluster * static_cast<uint64_t>(clusterSize);

    const uint64_t volumeSize =
        static_cast<uint64_t>(superBlock.totalClusters) * clusterSize;

    // Verificar que el contenido no exceda los limites del volumen.
    if (dataOffset > volumeSize ||
        static_cast<uint64_t>(size) > volumeSize - dataOffset) {
        std::cerr << "Error: El archivo excede los limites del volumen.\n";
        return false;
    }

    // Comprobar que la imagen fisica tenga el tamano esperado.
    image.clear();
    image.seekg(0, std::ios::end);

    const std::streampos imageSize = image.tellg();

    if (imageSize < 0 ||
        static_cast<uint64_t>(imageSize) < volumeSize) {
        std::cerr << "Error: La imagen esta incompleta.\n";
        return false;
    }

    // Escribir el contenido en los clusters seleccionados.
    image.clear();
    image.seekp(static_cast<std::streamoff>(dataOffset));

    if (!image) {
        std::cerr << "Error: No se pudo localizar el espacio libre.\n";
        return false;
    }

    if (!data.empty()) {
        image.write(
            data.data(),
            static_cast<std::streamsize>(data.size())
        );

        if (!image) {
            std::cerr << "Error: No se pudo escribir el contenido.\n";
            return false;
        }
    }

    image.flush();

    if (!image) {
        std::cerr << "Error: No se pudieron guardar los datos.\n";
        return false;
    }

    std::cout << "Contenido escrito correctamente en el cluster "
              << freeCluster << ".\n";

        // Preparar la fecha y hora actuales.
    std::time_t currentTime = std::time(nullptr);
    std::tm* localTime = std::localtime(&currentTime);

    if (localTime == nullptr) {
        std::cerr << "Error: No se pudo obtener la fecha actual.\n";
        return false;
    }

    char date[15];

    if (std::strftime(
            date,
            sizeof(date),
            "%Y%m%d%H%M%S",
            localTime
        ) != 14) {
        std::cerr << "Error: No se pudo generar la fecha.\n";
        return false;
    }

    // Preparar el nombre de 15 bytes.
    char fixedName[15] = {};

    std::copy(
        filename.begin(),
        filename.end(),
        fixedName
    );

    // Preparar los 12 bytes reservados.
    char reserved[12] = {};

    // Posicionarnos en la entrada libre del directorio.
    image.clear();
    image.seekp(static_cast<std::streamoff>(freeEntryOffset));

    if (!image) {
        std::cerr << "Error: No se pudo localizar la entrada libre.\n";
        return false;
    }

    // Escribir la entrada inicialmente como inactiva.
    const char inactiveType = '/';
    image.write(&inactiveType, 1);

    // Nombre del archivo.
    image.write(fixedName, 15);

    // Tamano del archivo.
    writeLittleEndian32(image, size);

    // Cluster inicial.
    writeLittleEndian32(
        image,
        static_cast<uint32_t>(freeCluster)
    );

    // Fecha de creacion.
    image.write(date, 14);

    // Fecha de modificacion.
    image.write(date, 14);

    // Bytes reservados.
    image.write(reserved, 12);

    image.flush();

    if (!image) {
        std::cerr << "Error: No se pudieron guardar los metadatos.\n";
        return false;
    }

    // Activar la entrada solo cuando todos los datos esten escritos.
    image.clear();
    image.seekp(static_cast<std::streamoff>(freeEntryOffset));

    const char activeType = 'F';
    image.write(&activeType, 1);
    image.flush();

    if (!image) {
        std::cerr << "Error: No se pudo activar la entrada.\n";
        return false;
    }

    // Actualizar el directorio cargado en memoria.
    image.clear();
    loadDirectoryUnlocked();

    std::cout << "\nArchivo importado correctamente: "
              << filename << '\n';

    return true;
}
/**
 * Elimina logicamente un archivo de FiUnamFS.
 * Marca su entrada como libre sin borrar los datos fisicos.
 */
bool FiUnamFS::deleteFile(const std::string& filename) {

    // Proteger la eliminacion frente a operaciones concurrentes.
    std::lock_guard<std::mutex> lock(imageMutex);

    // Comprobar que la imagen este abierta y sea valida.
    if (!image.is_open() || !validate()) {
        std::cerr << "Error: Imagen no valida o no abierta.\n";
        return false;
    }

    // Buscar el archivo entre las entradas activas.
    const auto it = std::find_if(
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

    // Calcular la posicion del directorio.
    const uint64_t directoryStart = superBlock.clusterSize;
    const uint64_t directorySize =
        static_cast<uint64_t>(superBlock.directoryClusters) *
        superBlock.clusterSize;

    const uint64_t entrySize = 64;
    const uint64_t totalEntries = directorySize / entrySize;

    // Buscar la entrada fisica correspondiente al archivo.
    for (uint64_t i = 0; i < totalEntries; ++i) {

        const uint64_t offset =
            directoryStart + i * entrySize;

                char type = '\0';

        image.clear();
        image.seekg(static_cast<std::streamoff>(offset));

        image.read(&type, 1);

        if (!image) {
            std::cerr << "Error: No se pudo leer el directorio.\n";
            return false;
        }

        if (type != 'F') {
            continue;
        }

        // Leer el nombre igual que en loadDirectory().
        std::string currentName = readFixedString(image, 15);

        if (!image) {
            std::cerr << "Error: No se pudo leer el nombre.\n";
            return false;
        }

        // Quitar los espacios de relleno.
        const auto lastCharacter =
            currentName.find_last_not_of(' ');

        if (lastCharacter != std::string::npos) {
            currentName.erase(lastCharacter + 1);
        } else {
            currentName.clear();
        }

        if (currentName == filename) {

            // Cambiar el tipo de entrada de 'F' a '/'.
            const char deletedType = '/';

            image.clear();
            image.seekp(static_cast<std::streamoff>(offset));
            image.write(&deletedType, 1);
            image.flush();

            if (!image) {
                std::cerr << "Error: No se pudo eliminar el archivo.\n";
                return false;
            }

            // Actualizar el directorio en memoria.
            image.clear();
            loadDirectoryUnlocked();

            std::cout << "Archivo eliminado logicamente: "
                      << filename << '\n';

            return true;
        }
    }

    std::cerr << "Error: No se encontro la entrada del archivo.\n";
    return false;
}

