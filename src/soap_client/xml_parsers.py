from xml.etree import ElementTree as ET


def extract_order_number(xml_response: str) -> str:
    root = ET.fromstring(xml_response)

    # Busqueda namespace-agnostica: recorre todos los nodos
    for node in root.iter():
        tag = node.tag.split("}")[-1] if "}" in node.tag else node.tag
        if tag.lower() == "numeroorden" and node.text and node.text.strip():
            return node.text.strip()

    raise ValueError("No se encontro numeroOrden en la respuesta SOAP.")


def extract_cod_error(xml_response: str) -> tuple[str, str]:
    """Devuelve (codError, mensaje) desde <resultado> del response."""
    root = ET.fromstring(xml_response)
    cod = None
    msg = ""
    for node in root.iter():
        tag = node.tag.split("}")[-1] if "}" in node.tag else node.tag
        if tag.lower() == "coderror" and node.text is not None:
            cod = node.text.strip()
        elif tag.lower() == "mensaje" and node.text is not None:
            msg = node.text.strip()
    if cod is None:
        raise ValueError("No se encontro codError en la respuesta SOAP.")
    return cod, msg


def has_soap_fault(xml_response: str) -> bool:
    root = ET.fromstring(xml_response)
    for node in root.iter():
        tag = node.tag.split("}")[-1] if "}" in node.tag else node.tag
        if tag.lower() == "fault":
            return True
    return False
