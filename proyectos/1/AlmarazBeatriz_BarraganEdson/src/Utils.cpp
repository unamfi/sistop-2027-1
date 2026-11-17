#include "../include/Utils.h"

/**
 * Convierte cuatro bytes consecutivos almacenados
 * en formato little-endian a un entero de 32 bits.
 */
uint32_t readLittleEndian32(std::fstream& file) {
    unsigned char bytes[4];

    file.read(
        reinterpret_cast<char*>(bytes),
        4
    );

    return
        static_cast<uint32_t>(bytes[0]) |
        (static_cast<uint32_t>(bytes[1]) << 8) |
        (static_cast<uint32_t>(bytes[2]) << 16) |
        (static_cast<uint32_t>(bytes[3]) << 24);
}

/**
 * Lee una cadena de longitud fija y elimina los
 * caracteres nulos sobrantes utilizados como relleno.
 */
std::string readFixedString(
    std::fstream& file,
    size_t length
) {
    std::string result(length, '\0');

    file.read(&result[0], length);

    size_t end = result.find('\0');

    if(end != std::string::npos){
        result.resize(end);
    }

    return result;
}