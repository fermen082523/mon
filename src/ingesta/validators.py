import re


PLATE_REGEX = re.compile(r"^[A-Z0-9-]{5,10}$")


def normalize_plate(raw: str) -> str:
    return raw.strip().upper().replace(" ", "")


def is_valid_plate(plate: str) -> bool:
    return bool(PLATE_REGEX.match(plate))
