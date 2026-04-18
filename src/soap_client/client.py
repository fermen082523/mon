from __future__ import annotations

import requests

from src.config.settings import AppSettings
from src.soap_client.xml_builders import wrap_soap_envelope


class SoapClient:
    def __init__(self, settings: AppSettings) -> None:
        if not settings.soap_endpoint:
            raise ValueError("SOAP_ENDPOINT no esta configurado.")
        self._settings = settings

    def _post(self, soap_action: str, body_xml: str, password: str) -> str:
        envelope = wrap_soap_envelope(body_xml)
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": soap_action,
            "USERNAME": self._settings.soap_username,
            "PASSWORD": password,
        }
        response = requests.post(
            self._settings.soap_endpoint,
            data=envelope.encode("utf-8"),
            headers=headers,
            timeout=self._settings.soap_timeout_seconds,
        )
        response.raise_for_status()
        return response.text

    def solicitar_orden(self, xml_body: str) -> str:
        return self._post(
            self._settings.soap_action_solicitar,
            xml_body,
            self._settings.soap_password_solicitar,
        )

    def finalizar_orden(self, xml_body: str) -> str:
        return self._post(
            self._settings.soap_action_finalizar,
            xml_body,
            self._settings.soap_password_solicitar,
        )

    def anular_orden(self, xml_body: str) -> str:
        return self._post(
            self._settings.soap_action_anular,
            xml_body,
            self._settings.soap_password_anular,
        )
