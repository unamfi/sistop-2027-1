#pragma once

class Server;

class Worker{
private:

    int workerId;

    Server& server;

public:

    Worker(
        int workerId,
        Server& server
    );

    void operator()();
};