#include "../include/FiUnamFS.h"
#include "../include/Utils.h"

#include <iomanip>
#include <iostream>
#include <mutex>
#include <string>

void FiUnamFS::loadDirectory() {
    std::lock_guard<std::mutex> lock(imageMutex);
    loadDirectoryUnlocked();
}

void FiUnamFS::loadDirectoryUnlocked() {
    files.clear();

    image.clear();
    image.seekg(superBlock.clusterSize);

    const uint64_t directorySize =
        static_cast<uint64_t>(superBlock.directoryClusters) *
        superBlock.clusterSize;
    const uint64_t entrySize = 64;
    const uint64_t entryCount = directorySize / entrySize;

    for (uint64_t i = 0; i < entryCount; ++i) {
        DirectoryEntry entry{};

        image.read(&entry.type, 1);
        if (!image) {
            return;
        }

        if (entry.type != 'F') {
            image.seekg(entrySize - 1, std::ios::cur);
            continue;
        }

        entry.filename = readFixedString(image, 15);
        const auto lastCharacter =
            entry.filename.find_last_not_of(' ');

        if (lastCharacter != std::string::npos) {
            entry.filename.erase(lastCharacter + 1);
        } else {
            entry.filename.clear();
        }

        entry.size = readLittleEndian32(image);
        entry.startCluster = readLittleEndian32(image);
        entry.creationDate = readFixedString(image, 14);
        entry.modificationDate = readFixedString(image, 14);
        image.seekg(12, std::ios::cur);

        if (!image) {
            return;
        }

        files.push_back(entry);
    }
}

void FiUnamFS::debugDirectory() const {
    std::cout
        << "\nArchivos encontrados: "
        << files.size()
        << "\n\n";

    for (const auto& file : files) {
        std::cout << file.filename << '\n';
    }
}

void FiUnamFS::listFiles() const {
    std::lock_guard<std::mutex> lock(imageMutex);

    std::cout
        << "\n========================================\n"
        << "      ARCHIVOS EN FIUNAMFS\n"
        << "========================================\n\n"
        << std::left
        << std::setw(18) << "Nombre"
        << std::setw(18) << "Tamano"
        << std::setw(18) << "Cluster"
        << '\n'
        << "--------------------------------------------------\n";

    for (const auto& file : files) {
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
