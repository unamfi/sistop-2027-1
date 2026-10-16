import threading
import time
import random

NUM_WORKERS = 4       # Cantidad de hilos trabajadores (k) 
NUM_REQUESTS = 10     # Número total de solicitudes a simular

request_queue = []
accounting_data = []

queue_lock = threading.Lock()
accounting_lock = threading.Lock()

# Semáforo para controlar y despertar a los trabajadores dormidos 
request_semaphore = threading.Semaphore(0)

class Worker(threading.Thread):
    def __init__(self, worker_id):
        super().__init__()
        self.worker_id = worker_id
        self.running = True

    def run(self):
        while self.running:
            # El trabajador se suspende hasta que el jefe le asigne una tarea 
            request_semaphore.acquire()
            
            if not self.running:
                break
            
            # Extrae la solicitud de la cola
            with queue_lock:
                if request_queue:
                    page = request_queue.pop(0)
                else:
                    continue
            
            # Simulación del procesamiento de la página web
            print(f"[Trabajador {self.worker_id}] Atendiendo la solicitud de: {page}")
            time.sleep(random.uniform(0.4, 0.9))
            
            # Notificar y registrar información de contabilidad antes de terminar
            with accounting_lock:
                accounting_data.append({
                    "worker_id": self.worker_id,
                    "page": page,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
            print(f"[Trabajador {self.worker_id}] Solicitud de '{page}' finalizada y registrada.")

    def stop(self):
        self.running = False
        request_semaphore.release() # Desbloquea para permitir una salida limpia

def boss_process():
    workers = []
    
    print(f"[Jefe] Inicializando servidor con {NUM_WORKERS} hilos trabajadores...")
    # Al inicializar, el proceso jefe lanza k hilos trabajadores 
    for i in range(NUM_WORKERS):
        w = Worker(i + 1)
        workers.append(w)
        w.start()

    # Simulación de recepción de conexiones de red por parte del jefe 
    for req_id in range(1, NUM_REQUESTS + 1):
        time.sleep(random.uniform(0.2, 0.5))
        page = f"/index_recurso_{req_id}.html"
        
        with queue_lock:
            request_queue.append(page)
        
        print(f"[Jefe] Conexión de red recibida ({page}). Asignando y despertando a un trabajador...")
        # El jefe asigna la tarea y despierta a un trabajador disponible 
        request_semaphore.release()

    # Esperar un momento prudente para que terminen las últimas tareas
    time.sleep(4)

    # Detener de forma ordenada a los trabajadores
    print("\n[Jefe] Apagando el servidor web...")
    for w in workers:
        w.stop()
    for w in workers:
        w.join()

    # Impresión del reporte de contabilidad
    print("\n" + "="*50)
    print(" REPORTE DE CONTABILIDAD DEL SISTEMA")
    print("="*50)
    for idx, record in enumerate(accounting_data, 1):
        print(f"[{idx}] Trabajador ID: {record['worker_id']} | Página: {record['page']} | Hora: {record['timestamp']}")
    print("="*50)

if __name__ == "__main__":
    boss_process()