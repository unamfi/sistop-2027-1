#pragma once

#include <map>
#include <mutex>
#include <string>

/**
 * Encapsula toda la información de contabilidad
 * del sistema.
 *
 * Esta clase es compartida por múltiples hilos,
 * por lo que protege sus estructuras internas
 * mediante exclusión mutua.
 */

class Statistics {
private:

    /// Protege todas las estadísticas del sistema.
    std::mutex mutex_;

    /// Total de solicitudes atendidas.
    int totalRequests;

    /// Cantidad de accesos por página.
    std::map<std::string, int> pageRequests;

    /// Cantidad de solicitudes procesadas por trabajador.
    std::map<int, int> workerRequests;

public:

    Statistics();

    /**
     * Registra una petición procesada.
     */

    void registerRequest(
        int workerId,
        const std::string& page
    );

    void printReport();
};
