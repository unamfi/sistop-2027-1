#include <iostream>
#include <thread>
#include <vector>
#include <chrono>

#include "include/Trabajador.h"
#include "include/server.h"

int main() {
    // Inicialización del servidor encargado de coordinar la interacción entre
    // jefe y trabajadores.
    Server server;

    constexpr int NUM_WORKERS = 4;
    constexpr int NUM_REQUESTS = 20;

    std::vector<std::thread> workers;

    /*
     * Creación del pool de trabajadores.
     *
     * Una vez creados, permanecerán bloqueados esperando solicitudes hasta que el jefe
     * produzca trabajo.
     */

    for(int i = 0; i < NUM_WORKERS; i++){
        workers.emplace_back(
            Worker(i + 1,
                   server)
        );
    }

    std::vector<std::string> pages =
    {
        "/",
        "/login",
        "/products",
        "/cart",
        "/contact"
    };

    /*
     * Simulación del comportamiento del jefe.
     *
     * En lugar de recibir conexiones reales,
     * se generan solicitudes aleatorias con
     * distintos recursos web.
     */
    
    for(int i = 0; i < NUM_REQUESTS; i++) {
        Request request;

        request.id = i + 1;

        request.page =
            pages[rand() % pages.size()];

        std::cout
            << "[JEFE] Nueva solicitud "
            << request.page
            << "\n";

        server.submitRequest(
            request
        );

        std::this_thread::sleep_for(
            std::chrono::milliseconds(500)
        );
    }

    server.shutdown();

    for(auto& worker : workers) {
        worker.join();
    }

    server.getStatistics()
          .printReport();

    return 0;
}