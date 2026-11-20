#include "../include/FiUnamFS.h"
#include "../include/Utils.h"

#include <iostream>

bool FiUnamFS::openImage(const std::string& path) {
    image.open(
        path,
        std::ios::in |
        std::ios::out |
        std::ios::binary
    );

    return image.is_open();
}

bool FiUnamFS::loadSuperBlock() {
    if (!image.is_open()) {
        return false;
    }

    image.clear();
    image.seekg(0);
    superBlock.fileSystemName = readFixedString(image, 8);

    image.seekg(10);
    superBlock.version = readFixedString(image, 4);

    image.seekg(20);
    superBlock.volumeLabel = readFixedString(image, 16);

    image.seekg(40);
    superBlock.clusterSize = readLittleEndian32(image);
    superBlock.directoryClusters = readLittleEndian32(image);
    superBlock.totalClusters = readLittleEndian32(image);

    return static_cast<bool>(image);
}

bool FiUnamFS::validate() {
    return superBlock.fileSystemName == "FiUnamFS" &&
        superBlock.version == "27-1";
}

void FiUnamFS::printInfo() const {
    std::cout
        << "\n=== SUPERBLOQUE ===\n"
        << "Sistema: " << superBlock.fileSystemName << '\n'
        << "Version: " << superBlock.version << '\n'
        << "Etiqueta: " << superBlock.volumeLabel << '\n'
        << "Tamano de cluster: " << superBlock.clusterSize
        << " bytes\n"
        << "Clusters de directorio: "
        << superBlock.directoryClusters << '\n'
        << "Clusters totales: "
        << superBlock.totalClusters << '\n';
}
