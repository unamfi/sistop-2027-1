#!/usr/bin/env python3
import math
import os
import queue
import struct
import sys
import threading
from datetime import datetime

SECTOR_SIZE = 512
SECTORS_PER_CLUSTER = 4
CLUSTER_SIZE = SECTOR_SIZE * SECTORS_PER_CLUSTER  # 2048
DISK_SIZE = 1440 * 1024  # 1474560 bytes
TOTAL_CLUSTERS = DISK_SIZE // CLUSTER_SIZE  # 720

DIR_START_CLUSTER = 1
DIR_NUM_CLUSTERS = 4
DIR_OFFSET = DIR_START_CLUSTER * CLUSTER_SIZE
DIR_SIZE = DIR_NUM_CLUSTERS * CLUSTER_SIZE  # 8192 bytes
ENTRY_SIZE = 64
MAX_ENTRIES = DIR_SIZE // ENTRY_SIZE  # 128 entries
DATA_START_CLUSTER = DIR_START_CLUSTER + DIR_NUM_CLUSTERS  # 5

MAGIC_FS = b"FiUnamFS"
EXPECTED_VERSION = b"27-1"


class FiUnamFSError(Exception):
    pass


class FiUnamFS:
    def __init__(self, image_path: str):
        self.image_path = image_path
        self.io_lock = threading.Lock()
        self.op_cond = threading.Condition(self.io_lock)
        self.active_workers = 0
        self.log_lock = threading.Lock()
        self._validate_image()

    def _log_thread(self, msg: str):
        with self.log_lock:
            print(f"[{threading.current_thread().name}] {msg}")

    def _validate_image(self):
        if not os.path.isfile(self.image_path):
            raise FiUnamFSError(f"No existe el archivo de imagen: {self.image_path}")
        size = os.path.getsize(self.image_path)
        if size != DISK_SIZE:
            raise FiUnamFSError(
                f"Tamaño inválido ({size} bytes). Se esperan {DISK_SIZE} bytes (1440 KiB)."
            )

        with open(self.image_path, "rb") as f:
            sb = f.read(CLUSTER_SIZE)

        fs_name = sb[0:8]
        version = sb[10:14].rstrip(b"\x00 ")
        cluster_size = struct.unpack("<I", sb[40:44])[0]
        dir_clusters = struct.unpack("<I", sb[44:48])[0]
        total_clusters = struct.unpack("<I", sb[48:52])[0]

        if fs_name != MAGIC_FS:
            raise FiUnamFSError(f"Sistema de archivos inválido: {fs_name!r}")
        if version != EXPECTED_VERSION:
            raise FiUnamFSError(
                f"Versión incompatible: {version!r} (se requiere {EXPECTED_VERSION!r})"
            )
        if cluster_size != CLUSTER_SIZE or dir_clusters != DIR_NUM_CLUSTERS or total_clusters != TOTAL_CLUSTERS:
            raise FiUnamFSError("Parámetros del superbloque inconsistentes con la especificación.")

    def get_label(self) -> str:
        with self.io_lock, open(self.image_path, "rb") as f:
            f.seek(20)
            raw = f.read(16)
        return raw.split(b"\x00")[0].decode("ascii", errors="replace").strip()

    def _read_entries_unlocked(self, f):
        f.seek(DIR_OFFSET)
        entries = []
        for idx in range(MAX_ENTRIES):
            raw = f.read(ENTRY_SIZE)
            ftype = raw[0:1]
            name_raw = raw[1:16]
            size, start_cluster = struct.unpack("<II", raw[16:24])
            created = raw[24:38].decode("ascii", errors="replace")
            modified = raw[38:52].decode("ascii", errors="replace")
            name = name_raw.split(b"\x00")[0].decode("ascii", errors="replace").strip()
            entries.append({
                "index": idx,
                "raw": raw,
                "ftype": ftype,
                "name": name,
                "size": size,
                "start_cluster": start_cluster,
                "created": created,
                "modified": modified,
            })
        return entries

    @staticmethod
    def _format_ts(ts: str) -> str:
        if len(ts) == 14 and ts.isdigit():
            return f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:{ts[12:14]}"
        return ts

    def list_files(self):
        with self.io_lock:
            self.active_workers += 1
            try:
                with open(self.image_path, "rb") as f:
                    entries = self._read_entries_unlocked(f)
            finally:
                self.active_workers -= 1
                self.op_cond.notify_all()

        files = [e for e in entries if e["ftype"] == b"F"]
        files.sort(key=lambda x: x["name"])

        print(f"Volumen: {self.get_label()} | Archivos encontrados: {len(files)}")
        print(f"{'Nombre':<16} {'Tamaño':>10} {'Cluster':>8} {'Modificación':<19}")
        print("-" * 58)
        for item in files:
            print(
                f"{item['name']:<16} {item['size']:>10} {item['start_cluster']:>8} "
                f"{self._format_ts(item['modified']):<19}"
            )

    def copy_from_fs(self, fs_name: str, host_dest: str):
        with self.io_lock:
            while self.active_workers > 0:
                self.op_cond.wait()
            self.active_workers += 1
            try:
                with open(self.image_path, "rb") as f:
                    entries = self._read_entries_unlocked(f)
                    target = next((e for e in entries if e["ftype"] == b"F" and e["name"] == fs_name), None)
                    if not target:
                        raise FiUnamFSError(f"Archivo '{fs_name}' no encontrado en FiUnamFS.")

                    f.seek(target["start_cluster"] * CLUSTER_SIZE)
                    data = f.read(target["size"])
            finally:
                self.active_workers -= 1
                self.op_cond.notify_all()

        dest_path = host_dest
        if os.path.isdir(host_dest):
            dest_path = os.path.join(host_dest, fs_name)

        with open(dest_path, "wb") as out:
            out.write(data)
        print(f"Copiado '{fs_name}' -> '{dest_path}' ({len(data)} bytes).")

    def _find_free_contiguous_clusters(self, entries, needed_clusters: int) -> int:
        if needed_clusters <= 0:
            needed_clusters = 1
        occupied = [False] * TOTAL_CLUSTERS
        for c in range(0, DATA_START_CLUSTER):
            occupied[c] = True

        for e in entries:
            if e["ftype"] == b"F" and e["size"] > 0:
                n_clust = math.ceil(e["size"] / CLUSTER_SIZE)
                for c in range(e["start_cluster"], min(TOTAL_CLUSTERS, e["start_cluster"] + n_clust)):
                    occupied[c] = True

        run_start = None
        run_len = 0
        for c in range(DATA_START_CLUSTER, TOTAL_CLUSTERS):
            if not occupied[c]:
                if run_start is None:
                    run_start = c
                run_len += 1
                if run_len >= needed_clusters:
                    return run_start
            else:
                run_start = None
                run_len = 0

        raise FiUnamFSError(f"No hay espacio contiguo suficiente ({needed_clusters} clusters requeridos).")

    def copy_to_fs(self, host_src: str, fs_name: str | None = None):
        if not os.path.isfile(host_src):
            raise FiUnamFSError(f"Archivo origen no existe: {host_src}")

        target_name = fs_name or os.path.basename(host_src)
        name_bytes = target_name.encode("ascii")
        if len(target_name) == 0 or len(name_bytes) > 15:
            raise FiUnamFSError("El nombre en FiUnamFS debe tener entre 1 y 15 caracteres ASCII.")

        with open(host_src, "rb") as src:
            data = src.read()

        needed_clusters = max(1, math.ceil(len(data) / CLUSTER_SIZE))
        now_str = datetime.now().strftime("%Y%m%d%H%M%S")

        with self.io_lock:
            while self.active_workers > 0:
                self.op_cond.wait()
            self.active_workers += 1
            try:
                with open(self.image_path, "r+b") as f:
                    entries = self._read_entries_unlocked(f)
                    if any(e["ftype"] == b"F" and e["name"] == target_name for e in entries):
                        raise FiUnamFSError(f"Ya existe un archivo llamado '{target_name}' en FiUnamFS.")

                    free_entry = next((e for e in entries if e["ftype"] != b"F"), None)
                    if not free_entry:
                        raise FiUnamFSError("No hay entradas libres en el directorio (máx. 128).")

                    start_cluster = self._find_free_contiguous_clusters(entries, needed_clusters)

                    # Escribir datos en clusters contiguos
                    f.seek(start_cluster * CLUSTER_SIZE)
                    f.write(data)
                    pad = (needed_clusters * CLUSTER_SIZE) - len(data)
                    if pad > 0:
                        f.write(b"\x00" * pad)

                    # Construir entrada de 64 bytes
                    padded_name = name_bytes.ljust(15, b"\x00")
                    entry_bytes = (
                        b"F"
                        + padded_name
                        + struct.pack("<II", len(data), start_cluster)
                        + now_str.encode("ascii")
                        + now_str.encode("ascii")
                        + (b"\x00" * 12)
                    )
                    f.seek(DIR_OFFSET + free_entry["index"] * ENTRY_SIZE)
                    f.write(entry_bytes)
            finally:
                self.active_workers -= 1
                self.op_cond.notify_all()

        print(f"Importado '{host_src}' como '{target_name}' en cluster {start_cluster} ({len(data)} bytes).")

    def delete_file(self, fs_name: str):
        with self.io_lock:
            while self.active_workers > 0:
                self.op_cond.wait()
            self.active_workers += 1
            try:
                with open(self.image_path, "r+b") as f:
                    entries = self._read_entries_unlocked(f)
                    target = next((e for e in entries if e["ftype"] == b"F" and e["name"] == fs_name), None)
                    if not target:
                        raise FiUnamFSError(f"Archivo '{fs_name}' no encontrado en FiUnamFS.")

                    # Marcar entrada como vacía ('-') y limpiar nombre con '#'
                    empty_entry = (
                        b"-"
                        + b"#..............."
                        + struct.pack("<II", 0, 0)
                        + (b"\x00" * 40)
                    )
                    f.seek(DIR_OFFSET + target["index"] * ENTRY_SIZE)
                    f.write(empty_entry)
            finally:
                self.active_workers -= 1
                self.op_cond.notify_all()

        print(f"Eliminado '{fs_name}' de FiUnamFS.")

    def run_concurrent_tasks(self, tasks: list[tuple]):
        """Ejecuta múltiples operaciones en hilos coordinados por cola y sincronización."""
        task_queue: queue.Queue = queue.Queue()
        errors: list[str] = []
        err_lock = threading.Lock()

        for t in tasks:
            task_queue.put(t)

        def worker():
            while True:
                try:
                    item = task_queue.get_nowait()
                except queue.Empty:
                    break

                op = item[0]
                self._log_thread(f"Iniciando operación: {op}")
                try:
                    if op == "list":
                        self.list_files()
                    elif op == "get":
                        self.copy_from_fs(item[1], item[2])
                    elif op == "put":
                        self.copy_to_fs(item[1], item[2] if len(item) > 2 else None)
                    elif op == "rm":
                        self.delete_file(item[1])
                    else:
                        raise FiUnamFSError(f"Operación desconocida: {op}")
                    self._log_thread(f"Finalizada operación: {op}")
                except Exception as exc:
                    with err_lock:
                        errors.append(str(exc))
                    self._log_thread(f"Error en {op}: {exc}")
                finally:
                    task_queue.task_done()

        threads = [
            threading.Thread(target=worker, name=f"Worker-{i+1}")
            for i in range(min(3, max(1, len(tasks))))
        ]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        if errors:
            raise FiUnamFSError("; ".join(errors))


def print_usage():
    print("Uso:")
    print("  fiunamfs.py <disco.img> ls")
    print("  fiunamfs.py <disco.img> get <archivo_fs> <destino_local>")
    print("  fiunamfs.py <disco.img> put <archivo_local> [nombre_fs]")
    print("  fiunamfs.py <disco.img> rm <archivo_fs>")


def main():
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    img_path = sys.argv[1]
    cmd = sys.argv[2]

    try:
        fs = FiUnamFS(img_path)
        if cmd == "ls" and len(sys.argv) == 3:
            fs.run_concurrent_tasks([("list",)])
        elif cmd == "get" and len(sys.argv) == 5:
            fs.run_concurrent_tasks([("get", sys.argv[3], sys.argv[4])])
        elif cmd == "put" and len(sys.argv) in (4, 5):
            nombre_fs = sys.argv[4] if len(sys.argv) == 5 else None
            fs.run_concurrent_tasks([("put", sys.argv[3], nombre_fs)])
        elif cmd == "rm" and len(sys.argv) == 4:
            fs.run_concurrent_tasks([("rm", sys.argv[3])])
        else:
            print_usage()
            sys.exit(1)
    except FiUnamFSError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()