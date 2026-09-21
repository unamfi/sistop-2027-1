from datetime import datetime
import platform
with open("reporte.txt", "w", encoding="utf-8") as archivo:
   archivo.write("=== REPORTE DEL SISTEMA ===\n")
   archivo.write(f"Fecha y hora: {datetime.now()}\n")
   archivo.write(f"Sistema operativo: {platform.system()}\n")
   archivo.write(f"Versión: {platform.version()}\n")
   archivo.write(f"Arquitectura: {platform.machine()}\n")
print("Reporte generado correctamente en reporte.txt")