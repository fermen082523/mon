from pathlib import Path
from typing import Callable, Optional

from src.ingesta.validators import is_valid_plate, normalize_plate
from src.persistencia.repository import Repository


def ingest_txt(
    file_path: str,
    repository: Repository,
    reporter: Optional[Callable[[str], None]] = None,
    etiqueta: Optional[str] = None,
) -> tuple[int, int]:
    def report(message: str) -> None:
        if reporter:
            reporter(message)

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {file_path}")

    valid_count = 0
    invalid_count = 0
    seen: set[str] = set()

    for line in path.read_text(encoding="utf-8").splitlines():
        plate = normalize_plate(line)
        if not plate:
            continue

        if plate in seen:
            report(f"[INGESTA] Duplicada en el archivo, se omite: {plate}")
            continue

        seen.add(plate)

        if is_valid_plate(plate):
            orden_id = repository.add_placa(plate, "txt", etiqueta=etiqueta)
            valid_count += 1
            suffix = f" | etiqueta={etiqueta.upper()}" if etiqueta else ""
            report(f"[INGESTA] Encolada placa {plate} (orden local #{orden_id}){suffix}.")
        else:
            repository.save_audit(
                orden_id=None,
                evento="PLACAINVALIDA",
                error=f"Placa invalida: {plate}",
            )
            invalid_count += 1
            report(f"[INGESTA] Placa invalida, se omite: {plate}")

    return valid_count, invalid_count
