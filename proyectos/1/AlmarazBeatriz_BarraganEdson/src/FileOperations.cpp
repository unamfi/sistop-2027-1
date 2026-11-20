#include "../include/FiUnamFS.h"
#include "../include/Utils.h"

#include <algorithm>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <mutex>
#include <string>
#include <vector>

namespace {

std::string trimFixedName(std::string name) {
    const auto lastCharacter = name.find_last_not_of(' ');
    if (lastCharacter == std::string::npos) {
        return {};
    }

    name.erase(lastCharacter + 1);
    return name;
}

bool hasValidFileName(const std::string& filename) {
    return !filename.empty() &&
        filename.size() <= 15 &&
        filename != "." &&
        filename != ".." &&
        filename.find_first_of("/\\") == std::string::npos;
}

}

bool FiUnamFS::exportFile(
    const std::string& filename,
    const std::string& destination
) {
    std::lock_guard<std::mutex> lock(imageMutex);

    const auto file = std::find_if(
        files.begin(),
        files.end(),
        [&](const DirectoryEntry& entry) {
            return entry.filename == filename;
        }
    );

    if (file == files.end()) {
        std::cerr << "Error: Archivo no encontrado.\n";
        return false;
    }

    if (!image.is_open() || !validate()) {
        std::cerr << "Error: Imagen no valida o no abierta.\n";
        return false;
    }

    const uint64_t clusterSize = superBlock.clusterSize;
    const uint64_t volumeSize =
        clusterSize * superBlock.totalClusters;
    const uint64_t offset =
        static_cast<uint64_t>(file->startCluster) * clusterSize;

    if (clusterSize == 0 ||
        file->startCluster < 1 + superBlock.directoryClusters ||
        offset > volumeSize ||
        file->size > volumeSize - offset) {
        std::cerr << "Error: Ubicacion del archivo invalida.\n";
        return false;
    }

    if (std::filesystem::exists(destination)) {
        std::cerr << "Error: El destino ya existe.\n";
        return false;
    }

    std::vector<char> data(file->size);
    image.clear();
    image.seekg(static_cast<std::streamoff>(offset));

    if (!image) {
        std::cerr << "Error: No se pudo localizar el archivo.\n";
        return false;
    }

    if (!data.empty()) {
        image.read(data.data(), static_cast<std::streamsize>(data.size()));
        if (!image) {
            std::cerr << "Error: Lectura incompleta.\n";
            return false;
        }
    }

    std::ofstream output(destination, std::ios::binary);
    if (!output.is_open()) {
        std::cerr << "Error: No se pudo crear el destino.\n";
        return false;
    }

    if (!data.empty()) {
        output.write(data.data(), static_cast<std::streamsize>(data.size()));
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

bool FiUnamFS::importFile(
    const std::string& source,
    const std::string& filename
) {
    std::lock_guard<std::mutex> lock(imageMutex);

    if (!image.is_open() || !validate()) {
        std::cerr << "Error: Imagen no valida o no abierta.\n";
        return false;
    }

    if (!hasValidFileName(filename)) {
        std::cerr << "Error: Nombre de archivo invalido.\n";
        return false;
    }

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

    std::ifstream input(source, std::ios::binary);
    if (!input.is_open()) {
        std::cerr << "Error: No se pudo abrir el archivo de origen.\n";
        return false;
    }

    input.seekg(0, std::ios::end);
    const std::streampos fileSize = input.tellg();
    if (fileSize <= 0 ||
        static_cast<uint64_t>(fileSize) > UINT32_MAX) {
        std::cerr << "Error: Tamano de archivo invalido.\n";
        return false;
    }

    const uint32_t size = static_cast<uint32_t>(fileSize);
    input.seekg(0, std::ios::beg);

    std::vector<char> data(size);
    input.read(data.data(), static_cast<std::streamsize>(data.size()));
    if (!input) {
        std::cerr << "Error: No se pudo leer completamente "
                  << "el archivo de origen.\n";
        return false;
    }

    const uint32_t clusterSize = superBlock.clusterSize;
    if (clusterSize == 0 || superBlock.totalClusters == 0) {
        std::cerr << "Error: Geometria del volumen invalida.\n";
        return false;
    }

    const uint64_t requiredClusters =
        (static_cast<uint64_t>(size) + clusterSize - 1) / clusterSize;
    const uint64_t firstDataCluster =
        1ULL + superBlock.directoryClusters;
    uint64_t freeCluster = 0;

    for (uint64_t candidate = firstDataCluster;
         candidate < superBlock.totalClusters;
         ++candidate) {
        if (requiredClusters >
            static_cast<uint64_t>(superBlock.totalClusters) - candidate) {
            break;
        }

        const uint64_t candidateEnd = candidate + requiredClusters;
        bool occupied = false;

        for (const auto& entry : files) {
            const uint64_t usedClusters =
                (static_cast<uint64_t>(entry.size) + clusterSize - 1)
                / clusterSize;
            const uint64_t usedEnd = entry.startCluster + usedClusters;

            if (candidate < usedEnd && entry.startCluster < candidateEnd) {
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

    const uint64_t directoryStart = clusterSize;
    const uint64_t directorySize =
        static_cast<uint64_t>(superBlock.directoryClusters) * clusterSize;
    const uint64_t entrySize = 64;
    const uint64_t totalEntries = directorySize / entrySize;
    uint64_t freeEntryOffset = 0;

    for (uint64_t i = 0; i < totalEntries; ++i) {
        const uint64_t offset = directoryStart + i * entrySize;
        char type = '\0';

        image.clear();
        image.seekg(static_cast<std::streamoff>(offset));
        image.read(&type, 1);
        if (!image) {
            std::cerr << "Error: No se pudo leer el directorio.\n";
            return false;
        }

        if (type != 'F') {
            freeEntryOffset = offset;
            break;
        }
    }

    if (freeEntryOffset == 0) {
        std::cerr << "Error: El directorio de FiUnamFS esta lleno.\n";
        return false;
    }

    const uint64_t dataOffset =
        freeCluster * static_cast<uint64_t>(clusterSize);
    const uint64_t volumeSize =
        static_cast<uint64_t>(superBlock.totalClusters) * clusterSize;

    if (dataOffset > volumeSize ||
        static_cast<uint64_t>(size) > volumeSize - dataOffset) {
        std::cerr << "Error: El archivo excede los limites del volumen.\n";
        return false;
    }

    image.clear();
    image.seekg(0, std::ios::end);
    const std::streampos imageSize = image.tellg();
    if (imageSize < 0 ||
        static_cast<uint64_t>(imageSize) < volumeSize) {
        std::cerr << "Error: La imagen esta incompleta.\n";
        return false;
    }

    image.clear();
    image.seekp(static_cast<std::streamoff>(dataOffset));
    image.write(data.data(), static_cast<std::streamsize>(data.size()));
    image.flush();
    if (!image) {
        std::cerr << "Error: No se pudo escribir el contenido.\n";
        return false;
    }

    std::time_t currentTime = std::time(nullptr);
    std::tm* localTime = std::localtime(&currentTime);
    if (localTime == nullptr) {
        std::cerr << "Error: No se pudo obtener la fecha actual.\n";
        return false;
    }

    char date[15];
    if (std::strftime(date, sizeof(date), "%Y%m%d%H%M%S", localTime) != 14) {
        std::cerr << "Error: No se pudo generar la fecha.\n";
        return false;
    }

    char fixedName[15] = {};
    std::copy(filename.begin(), filename.end(), fixedName);
    char reserved[12] = {};

    image.clear();
    image.seekp(static_cast<std::streamoff>(freeEntryOffset));
    const char inactiveType = '/';
    image.write(&inactiveType, 1);
    image.write(fixedName, 15);
    writeLittleEndian32(image, size);
    writeLittleEndian32(image, static_cast<uint32_t>(freeCluster));
    image.write(date, 14);
    image.write(date, 14);
    image.write(reserved, 12);
    image.flush();

    if (!image) {
        std::cerr << "Error: No se pudieron guardar los metadatos.\n";
        return false;
    }

    image.clear();
    image.seekp(static_cast<std::streamoff>(freeEntryOffset));
    const char activeType = 'F';
    image.write(&activeType, 1);
    image.flush();

    if (!image) {
        std::cerr << "Error: No se pudo activar la entrada.\n";
        return false;
    }

    loadDirectoryUnlocked();
    std::cout << "\nArchivo importado correctamente: "
              << filename << '\n';
    return true;
}

bool FiUnamFS::deleteFile(const std::string& filename) {
    std::lock_guard<std::mutex> lock(imageMutex);

    if (!image.is_open() || !validate()) {
        std::cerr << "Error: Imagen no valida o no abierta.\n";
        return false;
    }

    const auto file = std::find_if(
        files.begin(),
        files.end(),
        [&](const DirectoryEntry& entry) {
            return entry.filename == filename;
        }
    );

    if (file == files.end()) {
        std::cerr << "Error: Archivo no encontrado.\n";
        return false;
    }

    const uint64_t directoryStart = superBlock.clusterSize;
    const uint64_t directorySize =
        static_cast<uint64_t>(superBlock.directoryClusters) *
        superBlock.clusterSize;
    const uint64_t entrySize = 64;
    const uint64_t totalEntries = directorySize / entrySize;

    for (uint64_t i = 0; i < totalEntries; ++i) {
        const uint64_t offset = directoryStart + i * entrySize;
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

        const std::string currentName =
            trimFixedName(readFixedString(image, 15));
        if (!image) {
            std::cerr << "Error: No se pudo leer el nombre.\n";
            return false;
        }

        if (currentName == filename) {
            const char deletedType = '/';
            image.clear();
            image.seekp(static_cast<std::streamoff>(offset));
            image.write(&deletedType, 1);
            image.flush();

            if (!image) {
                std::cerr << "Error: No se pudo eliminar el archivo.\n";
                return false;
            }

            loadDirectoryUnlocked();
            std::cout << "Archivo eliminado logicamente: "
                      << filename << '\n';
            return true;
        }
    }

    std::cerr << "Error: No se encontro la entrada del archivo.\n";
    return false;
}
