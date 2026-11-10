import threading
import time
import random

# Parámetros del sistema
NUM_SILLAS = 3
TOTAL_CLIENTES = 8

# Mecanismos de sincronización
mutex = threading.Lock()           # Protege el acceso a las sillas de espera
barbero = threading.Semaphore(0)   # Notifica al barbero que hay un cliente listo
cliente = threading.Semaphore(0)   # Notifica al cliente que el barbero terminó de atenderlo

sillas_ocupadas = 0

def funcion_barbero():
    global sillas_ocupadas
    print("💈 [BARBERO] La barbería está abierta.")
    
    while True:
        if sillas_ocupadas == 0:
            print("💤 [BARBERO] No hay clientes. El barbero se duerme...")
        
        # Espera a que llegue un cliente
        barbero.acquire()
        
        # Se libera una silla de espera
        with mutex:
            sillas_ocupadas -= 1
            print(f"💈 [BARBERO] Empieza a cortar el cabello. (Sillas de espera ocupadas: {sillas_ocupadas}/{NUM_SILLAS})")
        
        # Simula el tiempo que toma cortar el cabello
        time.sleep(random.uniform(1.0, 2.0))
        
        print("✂️ [BARBERO] Terminó el corte de cabello.")
        cliente.release() # Notifica al cliente que su corte terminó

def funcion_cliente(id_cliente):
    global sillas_ocupadas
    time.sleep(random.uniform(0.2, 3.0)) # Tiempo aleatorio de llegada
    
    with mutex:
        print(f"👤 [CLIENTE {id_cliente}] Llega a la barbería.")
        if sillas_ocupadas < NUM_SILLAS:
            sillas_ocupadas += 1
            print(f"🪑 [CLIENTE {id_cliente}] Toma asiento en la sala de espera. ({sillas_ocupadas}/{NUM_SILLAS})")
            barbero.release() # Despierta o notifica al barbero
        else:
            print(f"🚶 [CLIENTE {id_cliente}] Barbería llena. Se retira sin ser atendido.")
            return

    # Espera a que el barbero termine el corte
    cliente.acquire()
    print(f"✅ [CLIENTE {id_cliente}] Recibió su corte y se retira satisfecho.")

def main():
    # Hilo demonio para el barbero (finaliza cuando concluyen los clientes)
    hilo_barbero = threading.Thread(target=funcion_barbero, daemon=True)
    hilo_barbero.start()

    hilos_clientes = []
    for i in range(1, TOTAL_CLIENTES + 1):
        t = threading.Thread(target=funcion_cliente, args=(i,))
        hilos_clientes.append(t)
        t.start()

    for t in hilos_clientes:
        t.join()

    print("\n🏁 [SISTEMA] Todos los clientes de la jornada han sido procesados. Fin de la simulación.")

if __name__ == "__main__":
    main()

