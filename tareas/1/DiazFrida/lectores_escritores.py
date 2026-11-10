import threading
import time
import random

base_de_datos = "Información inicial del sistema"
contador_lectores = 0

mutex_lectores = threading.Semaphore(1)
mutex_escritura = threading.Semaphore(1)

def escritor(id_escritor):
    global base_de_datos
    for _ in range(3):
        time.sleep(random.uniform(1.5, 3.0))
        mutex_escritura.acquire()
        print(f"✍️  [ESCRITOR {id_escritor}] Escribiendo...")
        time.sleep(random.uniform(0.8, 1.5))
        base_de_datos = f"Dato actualizado por Escritor {id_escritor}"
        print(f"✅ [ESCRITOR {id_escritor}] Escritura terminada.")
        mutex_escritura.release()

def lector(id_lector):
    global contador_lectores
    for _ in range(3):
        time.sleep(random.uniform(1.0, 2.5))
        mutex_lectores.acquire()
        contador_lectores += 1
        if contador_lectores == 1:
            mutex_escritura.acquire()
        mutex_lectores.release()
        
        print(f"📖 [Lector {id_lector}] Leyendo (Activos: {contador_lectores}) -> Valor: '{base_de_datos}'")
        time.sleep(random.uniform(0.5, 1.0))
        
        mutex_lectores.acquire()
        contador_lectores -= 1
        if contador_lectores == 0:
            mutex_escritura.release()
        mutex_lectores.release()

if __name__ == "__main__":
    print("=== SIMULACIÓN DE LECTORES - ESCRITORES ===")
    hilos = []
    for i in range(1, 4):
        hilos.append(threading.Thread(target=escritor, args=(i,)))
    for i in range(1, 6):
        hilos.append(threading.Thread(target=lector, args=(i,)))
    for t in hilos:
        t.start()
    for t in hilos:
        t.join()
    print("=== FIN ===")