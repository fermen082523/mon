def build_solicitar_xml(placa: str) -> str:
    return (
        "<ant:solicitarOrden xmlns:ant=\"http://www.ant.gob.ec/\">"
        "<orden>"
        "<ambito></ambito>"
        "<claseServicio></claseServicio>"
        "<fechaOrden></fechaOrden>"
        "<institucion>156SVC</institucion>"
        "<numeroRevision></numeroRevision>"
        f"<placa>{placa}</placa>"
        "<proceso></proceso>"
        "<solicitud>1</solicitud>"
        "<tipoOrden>RT1</tipoOrden>"
        "<tipoServicio></tipoServicio>"
        "<tipoTransporte></tipoTransporte>"
        "<vin></vin>"
        "</orden>"
        "</ant:solicitarOrden>"
    )


def build_finalizar_xml(numero_orden: str) -> str:
    return (
        "<ant:finalizarOrden xmlns:ant=\"http://www.ant.gob.ec/\">"
        "<orden>"
        "<aprobado>S</aprobado>"
        "<aprobado1>S</aprobado1>"
        "<aprobado2>S</aprobado2>"
        "<aprobado3>S</aprobado3>"
        "<aprobado4>S</aprobado4>"
        "<fechaFinOt></fechaFinOt>"
        f"<numeroOrden>{numero_orden}</numeroOrden>"
        "</orden>"
        "</ant:finalizarOrden>"
    )


def build_anular_xml(numero_orden: str, motivo: str) -> str:
    return (
        "<ant:anularOrden xmlns:ant=\"http://www.ant.gob.ec/\">"
        "<orden>"
        f"<numeroOrden>{numero_orden}</numeroOrden>"
        f"<motivo>{motivo}</motivo>"
        "</orden>"
        "</ant:anularOrden>"
    )


def wrap_soap_envelope(body_xml: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soapenv:Envelope'
        ' xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"'
        ' xmlns:ant="http://www.ant.gob.ec/">'
        "<soapenv:Header/>"
        f"<soapenv:Body>{body_xml}</soapenv:Body>"
        "</soapenv:Envelope>"
    )
