#ALumno: López Vizcarra Ángel David
#Sistemas operativos 2027-1


import threading
import time
import random

# Parámetros de configuración
X_SILLAS = 3           # Capacidad del cubículo 
Y_MAX_PREGUNTAS = 4    # Máximo de preguntas por alumno
NUM_ALUMNOS = 6        # Total de alumnos que intentarán asesoría

class CubiculoAsesor:
    def __init__(self, x_sillas):
        self.x_sillas = x_sillas
        self.alumnos_adentro = 0
        self.horario_activo = True

        # Primitivas de sincronización
        self.mutex_puerta = threading.Lock()         # Protege el conteo al tocar la puerta
        self.turno_pregunta = threading.Lock()       # Solo 1 alumno pregunta a la vez
        self.despertar_profesor = threading.Semaphore(0) # Profesor duerme hasta que le pregunten
        self.respuesta_lista = threading.Semaphore(0)    # Alumno espera la respuesta del profesor
        
        # Datos de la pregunta actual (protegidos implícitamente por turno_pregunta)
        self.alumno_actual = None
        self.num_pregunta_actual = None

    def rutina_profesor(self):
        print("[Profesor] Inicia el horario de atención. No hay nadie, a dormir en el sofá...")
        
        while True:
            # Si no hay alumnos, el profesor duerme (bloqueado en el semáforo sin gastar CPU)
            self.despertar_profesor.acquire()
            
            # Condición de salida al terminar la simulación
            if not self.horario_activo and self.alumnos_adentro == 0:
                print("[Profesor] Terminó el horario de atención. Cerrando cubículo.")
                break

            # Atendiendo la duda del alumno en turno
            print(f"[Profesor] Escuchando y respondiendo la duda #{self.num_pregunta_actual} del Alumno {self.alumno_actual}...")
            time.sleep(random.uniform(0.4, 0.9)) # Tiempo que toma explicar la respuesta
            print(f"[Profesor] Terminó de responder al Alumno {self.alumno_actual}.")

            # Avisar al alumno que su respuesta está lista
            self.respuesta_lista.release()

            # Verificar si el cubículo quedó vacío para volver a dormir
            with self.mutex_puerta:
                if self.alumnos_adentro == 0 and self.horario_activo:
                    print("[Profesor] El cubículo quedó vacío. Las sillas vuelven a ser sofá, a dormir la siesta...")

    def rutina_alumno(self, id_alumno, total_preguntas):
        # Llegada escalonada en cualquier momento
        time.sleep(random.uniform(0.1, 2.0))
        
        entrar = False
        while not entrar:
            print(f" [Alumno {id_alumno}] Toca la puerta (trae {total_preguntas} dudas).")
            with self.mutex_puerta:
                if self.alumnos_adentro < self.x_sillas:
                    self.alumnos_adentro += 1
                    entrar = True
                    print(f" [Alumno {id_alumno}] Entra al cubículo y toma asiento. "
                          f"(Ocupación: {self.alumnos_adentro}/{self.x_sillas})")
                else:
                    print(f" [Alumno {id_alumno}] Cubículo lleno ({self.x_sillas}/{self.x_sillas}). "
                          f"Dará una vuelta por la facultad y regresará.")
            
            if not entrar:
                # Espera afuera antes de volver a tocar la puerta
                time.sleep(random.uniform(1.0, 2.0))

        # Una vez sentado adentro, realiza sus 'y' preguntas alternando con los demás
        for num_p in range(1, total_preguntas + 1):
            # Espera pacientemente su turno para hablar con el profesor
            with self.turno_pregunta:
                self.alumno_actual = id_alumno
                self.num_pregunta_actual = f"{num_p}/{total_preguntas}"
                
                print(f" [Alumno {id_alumno}] Toma el turno y plantea su pregunta {num_p} de {total_preguntas}.")
                
                # Despierta al profesor (o le indica que la duda está planteada)
                self.despertar_profesor.release()
                
                # Espera a que el profesor termine de responderle
                self.respuesta_lista.acquire()
                print(f" [Alumno {id_alumno}] Entendió la respuesta {num_p}/{total_preguntas}.")

            # Si aún le quedan dudas, reflexiona un instante.
            # Esto cede el hilo (context switch) para que otro alumno sentado tome `turno_pregunta`.
            if num_p < total_preguntas:
                print(f" [Alumno {id_alumno}] Anota en su cuaderno y cede el turno a sus compañeros...")
                time.sleep(random.uniform(0.2, 0.5))

        # El alumno resolvió todas sus dudas y libera su silla
        with self.mutex_puerta:
            self.alumnos_adentro -= 1
            print(f" [Alumno {id_alumno}] Resolvió todas sus dudas y sale del cubículo. "
                  f"(Ocupación: {self.alumnos_adentro}/{self.x_sillas})")
            if self.alumnos_adentro == 0:
                print(" [Cubículo] No quedan alumnos. Las sillas quedan libres como sofá.")


def main():
    cubiculo = CubiculoAsesor(X_SILLAS)

    # Iniciar hilo del profesor
    hilo_profesor = threading.Thread(target=cubiculo.rutina_profesor, name="Profesor")
    hilo_profesor.start()

    # Crear e iniciar hilos de los alumnos
    hilos_alumnos = []
    for i in range(1, NUM_ALUMNOS + 1):
        preguntas = random.randint(1, Y_MAX_PREGUNTAS)
        t = threading.Thread(
            target=cubiculo.rutina_alumno,
            args=(i, preguntas),
            name=f"Alumno-{i}"
        )
        hilos_alumnos.append(t)
        t.start()

    # Esperar a que todos los alumnos sean atendidos
    for t in hilos_alumnos:
        t.join()

    # Cerrar el horario de atención y despertar al profesor para que termine su hilo
    cubiculo.horario_activo = False
    cubiculo.despertar_profesor.release()
    hilo_profesor.join()

if __name__ == "__main__":
    main()