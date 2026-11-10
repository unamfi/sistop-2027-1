#pragma once

#include <queue>
#include <mutex>
#include <condition_variable>

#include "Request.h"
#include "stats.h"

/**
 * Implementa el patrón Jefe-Trabajador.
 *
 * El hilo jefe deposita solicitudes en una cola
 * compartida y los trabajadores las consumen.
 *
 * La cola es protegida mediante mutex y la
 * coordinación entre hilos se realiza con
 * variables de condición.
 */

class Server {
private:

    /// Cola de solicitudes pendientes.
    std::queue<Request> pendingRequests;

    /// Protege el acceso concurrente a la cola.
    std::mutex queueMutex;

    /**
     * Permite bloquear trabajadores cuando
     * no existe trabajo disponible.
     */
    std::condition_variable requestAvailable;

    /// Indica que el servidor comenzará su cierre.
    bool shuttingDown;

public:

    Server();

    void submitRequest(
        const Request& request
    );

    Request getRequest();

    void shutdown();

    void logRequest(
        int workerId,
        const std::string& page
    );

    Statistics& getStatistics();
};