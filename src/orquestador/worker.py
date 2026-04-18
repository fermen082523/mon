from __future__ import annotations

import random
import time
from datetime import datetime, timedelta, timezone
from typing import Callable

from src.config.settings import AppSettings
from src.persistencia.repository import Repository
from src.soap_client.client import SoapClient
from src.soap_client.xml_builders import (
    build_anular_xml,
    build_finalizar_xml,
    build_solicitar_xml,
)
from src.soap_client.xml_parsers import extract_cod_error, extract_order_number, has_soap_fault


class Worker:
    def __init__(self, settings: AppSettings, repository: Repository, client: SoapClient) -> None:
        self._settings = settings
        self._repository = repository
        self._client = client

    def _log(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {message}")

    def _retry(self, fn: Callable[[], str], orden_id: int, evento: str) -> str:
        last_error = None
        for attempt in range(1, self._settings.max_retries + 1):
            try:
                if attempt > 1:
                    self._log(
                        f"[WORKER] Reintento {attempt}/{self._settings.max_retries} "
                        f"para {evento} (orden local #{orden_id})."
                    )
                return fn()
            except Exception as exc:
                last_error = exc
                self._log(
                    f"[WORKER] Error en {evento} (intento {attempt}/"
                    f"{self._settings.max_retries}) orden local #{orden_id}: {exc}"
                )
                self._repository.save_audit(
                    orden_id=orden_id,
                    evento=f"{evento}_RETRY_{attempt}",
                    error=str(exc),
                )
                if attempt < self._settings.max_retries:
                    time.sleep(self._settings.retry_backoff_seconds * attempt)
        raise RuntimeError(
            f"Fallo en {evento} luego de {self._settings.max_retries} intentos"
        ) from last_error

    def _solicitar_siguiente(self) -> bool:
        """Solicitar la próxima placa pendiente si no se ha alcanzado el límite de 2 abiertas."""
        solicitudes_abiertas = self._repository.count_solicitudes_sin_finalizar()
        if solicitudes_abiertas >= 2:
            return False

        orden = self._repository.get_next_pending()
        if not orden:
            return False

        self._log(f"[WORKER] Iniciando orden local #{orden.id} para placa {orden.placa}.")
        try:
            solicitar_xml = build_solicitar_xml(orden.placa)
            self._log(f"[WORKER] Enviando solicitarOrden para placa {orden.placa}...")
            # Sin reintentos automáticos: falla una vez → ERROR/incidencia
            solicitar_response = self._client.solicitar_orden(solicitar_xml)
            self._repository.save_audit(
                orden_id=orden.id,
                evento="SOLICITAR_OK",
                request_xml=solicitar_xml,
                response_xml=solicitar_response,
            )
            if has_soap_fault(solicitar_response):
                raise RuntimeError("SOAP Fault durante solicitar orden")

            numero_orden = extract_order_number(solicitar_response)
            cod, msg = extract_cod_error(solicitar_response)
            if cod != "0":
                raise RuntimeError(f"Error en solicitar orden: [{cod}] {msg}")

            wait_seconds = random.uniform(
                self._settings.wait_min_minutes * 60,
                self._settings.wait_max_minutes * 60,
            )
            finalizar_after = (
                datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=wait_seconds)
            ).isoformat()

            self._repository.mark_solicitada(orden.id, numero_orden, finalizar_after)

            wait_minutes = wait_seconds / 60
            pending_count = self._repository.count_pending()
            self._log(
                f"[WORKER] Solicitud OK. Orden ANT: {numero_orden}. "
                f"Finalizara en {wait_minutes:.2f} min. Pendientes en cola: {pending_count}."
            )
            return True
        except Exception as exc:
            self._repository.mark_error(orden.id)
            self._repository.save_audit(
                orden_id=orden.id,
                evento="PROCESS_ERROR",
                error=str(exc),
            )
            self._log(
                f"[WORKER] ERROR al solicitar orden local #{orden.id} placa {orden.placa}: {exc}"
            )
            return True

    def _finalizar_lista(self) -> bool:
        """Finalizar la primera orden SOLICITADA cuyo timer ya expiró."""
        orden = self._repository.get_orden_lista_para_finalizar()
        if not orden:
            return False

        self._log(
            f"[WORKER] Finalizando orden ANT {orden.numero_orden} para placa {orden.placa}."
        )
        try:
            finalizar_xml = build_finalizar_xml(orden.numero_orden)
            self._log(f"[WORKER] Enviando finalizarOrden para ANT {orden.numero_orden}...")
            finalizar_response = self._retry(
                lambda: self._client.finalizar_orden(finalizar_xml),
                orden.id,
                "FINALIZAR",
            )
            self._repository.save_audit(
                orden_id=orden.id,
                evento="FINALIZAR_OK",
                request_xml=finalizar_xml,
                response_xml=finalizar_response,
            )
            if has_soap_fault(finalizar_response):
                raise RuntimeError("SOAP Fault durante finalizar orden")

            cod, msg = extract_cod_error(finalizar_response)
            if cod != "0":
                raise RuntimeError(f"Error en finalizar orden: [{cod}] {msg}")

            self._repository.mark_finalizada(orden.id)
            self._log(
                f"[WORKER] Orden ANT {orden.numero_orden} placa {orden.placa} finalizada OK."
            )
            return True
        except Exception as exc:
            self._repository.mark_error(orden.id)
            self._repository.save_audit(
                orden_id=orden.id,
                evento="PROCESS_ERROR",
                error=str(exc),
            )
            self._log(
                f"[WORKER] ERROR al finalizar orden local #{orden.id} placa {orden.placa}: {exc}"
            )
            return True

    def process_next(self) -> bool:
        """Ejecutar un tick: finalizar las listas y solicitar nuevas. Retorna True si hubo trabajo."""
        did_finalize = self._finalizar_lista()
        did_solicitar = self._solicitar_siguiente()
        return did_finalize or did_solicitar

    def cancel_by_plate(self, placa: str, motivo: str = "Cancelacion manual") -> bool:
        orden = self._repository.get_open_order_by_placa(placa)
        if not orden or not orden.numero_orden:
            self._log(f"[WORKER] No hay orden abierta para placa {placa}.")
            return False

        try:
            self._log(
                f"[WORKER] Enviando anularOrden para placa {placa} "
                f"(ANT {orden.numero_orden})..."
            )
            anular_xml = build_anular_xml(orden.numero_orden, motivo)
            anular_response = self._retry(
                lambda: self._client.anular_orden(anular_xml),
                orden.id,
                "ANULAR",
            )
            self._repository.save_audit(
                orden_id=orden.id,
                evento="ANULAR_OK",
                request_xml=anular_xml,
                response_xml=anular_response,
            )
            if has_soap_fault(anular_response):
                raise RuntimeError("SOAP Fault durante anular orden")

            cod, msg = extract_cod_error(anular_response)
            if cod != "0":
                raise RuntimeError(f"Error en anular orden: [{cod}] {msg}")

            self._repository.mark_anulada(orden.id)
            self._log(f"[WORKER] Orden ANT {orden.numero_orden} anulada correctamente.")
            return True
        except Exception as exc:
            self._repository.mark_error(orden.id, increment_attempt=False)
            self._repository.save_audit(
                orden_id=orden.id,
                evento="ANULAR_ERROR",
                error=str(exc),
            )
            self._log(f"[WORKER] ERROR al anular orden de placa {placa}: {exc}")
            return False
