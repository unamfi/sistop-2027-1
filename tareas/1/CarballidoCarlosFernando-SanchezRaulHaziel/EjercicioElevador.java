import java.util.Random;
import java.util.concurrent.Semaphore;

public class EjercicioElevador {

    // SEGMENTO 1: Datos del problema
    static final int PISOS = 5;
    static final int CAPACIDAD = 5;
    static final int TOTAL_PERSONAS = 15;

    // SEGMENTO 2: Estado compartido (lo protege el mutex)
    static int[] esperando = new int[PISOS]; // cuantas personas esperan en cada piso
    static int[] queBajan = new int[PISOS]; // cuantas personas bajan en cada piso
    static int dentro = 0; // pasajeros dentro del elevador
    static volatile int pendientes = TOTAL_PERSONAS; // personas que aun no llegan s su destino

    // SEGMENTO 3: Semaforos
    static Semaphore mutex = new Semaphore(1); // un hilo a la vez en los datos
    static Semaphore[] semaforoSubir = new Semaphore[PISOS]; // esperan permiso para subir
    static Semaphore[] semaforoBajar = new Semaphore[PISOS]; // esperan llegar a su piso
    static Semaphore avisoAbordaron = new Semaphore(0); // "ya subi"
    static Semaphore avisoBajaron = new Semaphore(0); // "ya baje"

    // SEGMENTO 4: Hilo del elevador
    static class Elevador implements Runnable {
        public void run() {
            try {
                int piso = 0, direccion = 1; // direccion: 1 sube, -1 baja
                while (pendientes > 0) {

                    // Bajar a quienes llegaron a este piso
                    mutex.acquire();
                    int bajan = queBajan[piso];
                    queBajan[piso] = 0;
                    dentro = dentro - bajan;
                    mutex.release();
                    semaforoBajar[piso].release(bajan); // despierta a los que bajan
                    avisoBajaron.acquire(bajan); // espera a que bajen todos

                    // Subir a quienes esperan, sin pasar la capacidad
                    mutex.acquire();
                    int suben = Math.min(esperando[piso], CAPACIDAD - dentro);
                    esperando[piso] = esperando[piso] - suben;
                    dentro = dentro + suben;
                    mutex.release();
                    semaforoSubir[piso].release(suben); // despierta a los que suben
                    avisoAbordaron.acquire(suben); // espera a que suban todos

                    System.out.println("Piso " + piso + ": bajan " + bajan + ", suben " + suben);

                    // Moverse al siguiente piso (cruza todos los intermedios)
                    Thread.sleep(300);
                    if (piso + direccion < 0 || piso + direccion >= PISOS) {
                        direccion = -direccion;
                    }
                    piso = piso + direccion;
                }
                System.out.println("Todos llegaron. El elevador se detiene.");
            } catch (InterruptedException e) { }
        }
    }

    // SEGMENTO 5: Hilo de cada persona
    static class Persona implements Runnable {
        int numero, origen, destino;

        Persona(int numero, int origen, int destino) {
            this.numero = numero;
            this.origen = origen;
            this.destino = destino;
        }

        public void run() {
            try {
                // Llegar al piso y esperar el elevador
                System.out.println("Persona " + numero + " espera en piso " + origen + " (va al " + destino + ")");
                mutex.acquire();
                esperando[origen]++;
                mutex.release();
                semaforoSubir[origen].acquire(); // bloqueada hasta que la dejen subir

                // Abordar (sin importar la direccion del elevador)
                mutex.acquire();
                queBajan[destino]++;
                mutex.release();
                avisoAbordaron.release();
                System.out.println("Persona " + numero + " ABORDA");

                // Viajar hasta el destino y bajar
                semaforoBajar[destino].acquire();
                System.out.println("Persona " + numero + " BAJA en piso " + destino);
                mutex.acquire();
                pendientes--;
                mutex.release();
                avisoBajaron.release();
            } catch (InterruptedException e) { }
        }
    }

    // SEGMENTO 6: Programa principal
    public static void main(String[] args) throws InterruptedException {
        for (int i = 0; i < PISOS; i++) {
            semaforoSubir[i] = new Semaphore(0, true); // true = FIFO (evita inanicion)
            semaforoBajar[i] = new Semaphore(0, true);
        }

        new Thread(new Elevador()).start();

        Random azar = new Random();
        for (int i = 1; i <= TOTAL_PERSONAS; i++) {
            int origen = azar.nextInt(PISOS);
            int destino = azar.nextInt(PISOS);
            while (destino == origen) {
                destino = azar.nextInt(PISOS);
            }
            new Thread(new Persona(i, origen, destino)).start();
            Thread.sleep(azar.nextInt(250)); // llegan una tras otra
        }
    }
}

