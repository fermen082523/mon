from __future__ import annotations

import argparse
import re
import time
from datetime import datetime, timedelta, timezone

from src.config.settings import get_settings
from src.ingesta.paste_input import ingest_paste_multiline
from src.ingesta.txt_input import ingest_txt
from src.persistencia.repository import Repository
from src.persistencia.supabase_sync import SupabaseSync
from src.soap_client.client import SoapClient
from src.orquestador.worker import Worker


def build_runtime() -> tuple[Repository, Worker]:
    settings = get_settings()
    repository = Repository(settings.database_path, SupabaseSync(settings))
    client = SoapClient(settings)
    worker = Worker(settings, repository, client)
    return repository, worker


def normalize_tag(tag: str | None) -> str | None:
    if not tag:
        return None
    normalized = tag.strip().lower()
    if not re.fullmatch(r"[a-z]{2}", normalized):
        raise ValueError("La etiqueta debe tener exactamente 2 letras, por ejemplo: ca")
    return normalized


def cmd_ingest_txt(args: argparse.Namespace) -> None:
    repository, _ = build_runtime()
    print(f"[INGESTA] Leyendo archivo: {args.file}")
    tag = normalize_tag(args.tag)
    valid_count, invalid_count = ingest_txt(
        args.file,
        repository,
        reporter=print,
        etiqueta=tag,
    )
    pending = repository.count_pending()
    print(f"Placas validas cargadas: {valid_count}")
    print(f"Placas invalidas: {invalid_count}")
    print(f"[COLA] Pendientes para procesar: {pending}")


def cmd_ingest_paste(args: argparse.Namespace) -> None:
    repository, _ = build_runtime()
    tag = normalize_tag(args.tag)
    print("Pega las placas (una por linea). Finaliza con una linea vacia:")
    lines = []
    while True:
        line = input().strip()
        if not line:
            break
        lines.append(line)

    raw_text = "\n".join(lines)
    valid_count, invalid_count = ingest_paste_multiline(
        raw_text,
        repository,
        reporter=print,
        etiqueta=tag,
    )
    pending = repository.count_pending()
    print(f"Placas validas cargadas: {valid_count}")
    print(f"Placas invalidas: {invalid_count}")
    print(f"[COLA] Pendientes para procesar: {pending}")


def cmd_run_once(_: argparse.Namespace) -> None:
    _, worker = build_runtime()
    processed = worker.process_next()
    if processed:
        print("Se proceso una placa (ok o error).")
    else:
        print("No hay placas pendientes.")


def cmd_run_loop(_: argparse.Namespace) -> None:
    settings = get_settings()
    repository, worker = build_runtime()
    print("Worker iniciado en modo loop. Ctrl+C para detener.")
    last_supabase_sync = 0.0

    idle_templates = [
        "[WORKER] Seguimiento: ultima={ultima} | siguiente={siguiente} | prox_hora={prox_hora} | ETA cola={eta}",
        "[WORKER] Estado vivo: cola={cola}, abiertas={abiertas}, errores={errores} | siguiente={siguiente} ({prox_hora}) | ETA={eta}",
        "[WORKER] Monitor: ultima={ultima}; proxima={siguiente}; hora_prox={prox_hora}; fin_aprox={eta}",
    ]

    def _parse_as_utc(iso_value: str) -> datetime:
        dt_value = datetime.fromisoformat(iso_value)
        if dt_value.tzinfo is None:
            return dt_value.replace(tzinfo=timezone.utc)
        return dt_value.astimezone(timezone.utc)

    def _fmt_hora(iso_value: str | None) -> str:
        if not iso_value:
            return "-"
        try:
            # Los timestamps en BD se guardan en UTC; aquí se muestran en hora local.
            return _parse_as_utc(iso_value).astimezone().strftime("%H:%M:%S")
        except ValueError:
            return iso_value

    def _estimar_fin(overview: dict[str, object]) -> str:
        total = int(overview.get("pending_count", 0)) + int(overview.get("open_count", 0))
        if total <= 0:
            return "cola vacia"
        avg_wait = (settings.wait_min_minutes + settings.wait_max_minutes) / 2
        lotes = (total + 1) // 2
        fin_estimada = datetime.now() + timedelta(minutes=avg_wait * lotes)
        return fin_estimada.strftime("%H:%M:%S")

    def _siguiente_y_hora(overview: dict[str, object]) -> tuple[str, str]:
        open_count = int(overview.get("open_count", 0))
        next_pending = overview.get("next_pending_plate") or "-"
        next_finalize = overview.get("next_finalize_plate") or "-"
        next_finalize_after = overview.get("next_finalize_after")

        # Prioridad: si ya hay una lista para finalizar, esa es la siguiente.
        if next_finalize != "-":
            if not next_finalize_after:
                return str(next_finalize), "ahora"
            try:
                ready_at_utc = _parse_as_utc(str(next_finalize_after))
                if ready_at_utc <= datetime.now(timezone.utc):
                    return str(next_finalize), "ahora"
                if open_count >= 2 and next_pending != "-":
                    # Si hay limite abierto, la próxima solicitud depende de la próxima finalización.
                    return str(next_pending), ready_at_utc.astimezone().strftime("%H:%M:%S")
                return str(next_finalize), ready_at_utc.astimezone().strftime("%H:%M:%S")
            except ValueError:
                return str(next_finalize), _fmt_hora(str(next_finalize_after))

        if next_pending != "-":
            return str(next_pending), "ahora"
        return "-", "-"

    last_signature = ""
    template_index = 0
    heartbeat_every = max(1, int(60 / max(settings.poll_interval_seconds, 1)))
    idle_ticks = 0

    try:
        while True:
            before = repository.get_queue_overview()
            processed = worker.process_next()
            after = repository.get_queue_overview()

            # Heartbeat de sincronizacion para reintentar automaticamente en segundo plano.
            now_ts = time.time()
            if now_ts - last_supabase_sync >= max(5, settings.supabase_sync_every_seconds):
                try:
                    total_ordenes, total_audits = repository.sync_all_to_supabase()
                    print(
                        "[SUPABASE] Sync heartbeat OK "
                        f"(ordenes={total_ordenes}, auditoria={total_audits})."
                    )
                except RuntimeError:
                    # Supabase no configurado: omitir sin ruido en cada tick.
                    pass
                except Exception as exc:
                    print(f"[SUPABASE] Sync heartbeat fallo: {exc}")
                finally:
                    last_supabase_sync = now_ts

            if not processed:
                idle_ticks += 1
                siguiente, prox_hora = _siguiente_y_hora(after)
                ultima_hora = _fmt_hora(after.get("last_at"))
                ultima = (
                    f"{after.get('last_plate') or '-'} ({after.get('last_event') or '-'} @ {ultima_hora})"
                )
                eta = _estimar_fin(after)

                signature = "|".join(
                    [
                        str(after.get("pending_count", 0)),
                        str(after.get("open_count", 0)),
                        str(after.get("error_count", 0)),
                        str(siguiente),
                        str(prox_hora),
                        str(after.get("last_plate") or "-"),
                        str(after.get("last_event") or "-"),
                    ]
                )

                must_print = signature != last_signature or idle_ticks >= heartbeat_every
                if must_print:
                    template = idle_templates[template_index % len(idle_templates)]
                    template_index += 1
                    print(
                        template.format(
                            ultima=ultima,
                            siguiente=siguiente,
                            prox_hora=prox_hora,
                            eta=eta,
                            cola=after.get("pending_count", 0),
                            abiertas=after.get("open_count", 0),
                            errores=after.get("error_count", 0),
                        )
                    )
                    last_signature = signature
                    idle_ticks = 0
            else:
                idle_ticks = 0
                did_solicitar = int(after.get("pending_count", 0)) < int(before.get("pending_count", 0))
                did_finalizar = int(after.get("finished_count", 0)) > int(before.get("finished_count", 0))

                if did_solicitar and did_finalizar:
                    print(
                        "[WORKER] Actualizacion: se finalizo una orden y se inicio una nueva en el mismo ciclo."
                    )
                elif did_finalizar:
                    print("[WORKER] Actualizacion: se finalizo una orden.")
                elif did_solicitar:
                    print("[WORKER] Actualizacion: se inicio una nueva orden.")

            time.sleep(settings.poll_interval_seconds)
    except KeyboardInterrupt:
        print("Worker detenido por usuario.")


def cmd_cancel(args: argparse.Namespace) -> None:
    _, worker = build_runtime()
    cancelled = worker.cancel_by_plate(args.plate, args.reason)
    if cancelled:
        print("Orden anulada correctamente.")
    else:
        print("No se encontro orden abierta para esa placa o fallo la anulacion.")


def cmd_dequeue(args: argparse.Namespace) -> None:
    repository, _ = build_runtime()
    removed = repository.dequeue_plate(args.plate)
    if removed:
        print(f"[DEQUEUE] Placa {args.plate} eliminada de la cola (marcada ANULADA).")
    else:
        print(
            f"[DEQUEUE] Placa {args.plate} no encontrada en cola "
            f"(debe estar en estado PENDIENTE_SOLICITUD o ERROR)."
        )


def cmd_status(_: argparse.Namespace) -> None:
    from datetime import datetime
    repository, _ = build_runtime()
    data = repository.get_status_summary()

    en_cola = data["en_cola"]
    ejecutando = data["ejecutando"]
    con_error = data["con_error"]

    print(f"\n{'='*55}")
    print(f"  ESTADO DE LA COLA  |  {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*55}")

    print(f"\n[EN COLA] ({len(en_cola)} placa(s) esperando solicitar)")
    if en_cola:
        for i, p in enumerate(en_cola, 1):
            print(f"  {i:>3}. {p['placa']}")
    else:
        print("  (ninguna)")

    print(f"\n[EJECUTANDO] ({len(ejecutando)} placa(s) solicitadas, esperando finalizar)")
    if ejecutando:
        for p in ejecutando:
            if p["finalizar_after"]:
                # Calcular tiempo restante
                from datetime import timezone
                fa = datetime.fromisoformat(p["finalizar_after"])
                ahora = datetime.now(timezone.utc).replace(tzinfo=None)
                diff = (fa - ahora).total_seconds()
                if diff > 0:
                    mins = int(diff // 60)
                    segs = int(diff % 60)
                    timer = f"finaliza en {mins}m {segs:02d}s"
                else:
                    timer = "lista para finalizar"
            else:
                timer = "lista para finalizar"
            print(f"  - {p['placa']}  |  Orden ANT: {p['numero_orden']}  |  {timer}")
    else:
        print("  (ninguna)")

    print(f"\n[ERROR] ({len(con_error)} placa(s) con fallo)")
    if con_error:
        for p in con_error:
            orden_str = p["numero_orden"] or "sin orden ANT"
            print(f"  ! {p['placa']}  |  {orden_str}")
    else:
        print("  (ninguna)")

    print(f"{'='*55}\n")


def cmd_sync_supabase(_: argparse.Namespace) -> None:
    repository, _ = build_runtime()
    try:
        total_ordenes, total_audits = repository.sync_all_to_supabase()
    except RuntimeError as exc:
        print(f"[SUPABASE] {exc}")
        return
    print(
        f"[SUPABASE] Sincronizacion completa. "
        f"Ordenes: {total_ordenes} | Auditoria: {total_audits}"
    )


def cmd_report_incidencias(args: argparse.Namespace) -> None:
    repository, _ = build_runtime()
    incidents = repository.get_error_incidents(limit=args.limit)
    if not incidents:
        print("[INCIDENCIAS] No hay incidencias en estado ERROR.")
        return

    print(f"[INCIDENCIAS] Total encontradas: {len(incidents)}")
    for incident in incidents:
        numero_orden = incident["numero_orden"] or "-"
        ultimo_error = incident["ultimo_error"] or "Sin detalle de error"
        print(
            " | ".join(
                [
                    f"ID local: {incident['id']}",
                    f"Placa: {incident['placa']}",
                    f"Etapa: {incident['etapa']}",
                    f"Orden ANT: {numero_orden}",
                    f"Intentos: {incident['intentos']}",
                    f"Actualizado: {incident['updated_at']}",
                ]
            )
        )
        print(f"  Error: {ultimo_error}")


def cmd_retry_failed(args: argparse.Namespace) -> None:
    repository, _ = build_runtime()
    
    if args.plate:
        # Reintentar una placa específica
        success = repository.retry_error_by_plate(args.plate)
        if success:
            print(f"[RETRY] Placa {args.plate} encolada de nuevo para reintentar.")
        else:
            print(f"[RETRY] Placa {args.plate} no encontrada en estado ERROR.")
    elif args.etapa:
        # Reintentar todas las de una etapa
        count = repository.retry_errors_by_etapa(args.etapa)
        if count > 0:
            print(
                f"[RETRY] {count} placas en etapa {args.etapa.upper()} "
                f"encoladas para reintentar."
            )
        else:
            print(
                f"[RETRY] No hay placas en ERROR para etapa {args.etapa.upper()}."
            )
    else:
        print("[RETRY] Debes especificar --plate o --etapa.")


def cmd_help(_: argparse.Namespace) -> None:
    """Mostrar ayuda de todos los comandos disponibles."""
    help_text = """
[HELP] Comandos disponibles:

1. ingest-txt --file <ruta> [--tag xx]
   Cargar placas desde archivo TXT (una por linea).
    Ejemplo: python -m src.main ingest-txt --file placas.txt --tag ca

2. ingest-paste [etiqueta]
    Pegar placas manualmente en consola (una por linea, terminar con linea vacia).
    Ejemplo: python -m src.main ingest-paste ca

3. run-once
   Procesar una placa pendiente (ejecutar una sola vez).
   Ejemplo: python -m src.main run-once

4. run-loop
   Procesar placas continuamente en loop (Ctrl+C para detener).
   Ágil: solicita hasta 2 órdenes en paralelo y finaliza cuando el timer expire.
   No bloquea la cola mientras espera la finalización.
   Ejemplo: python -m src.main run-loop

5. cancel --plate <PLACA> [--reason <motivo>]
   Anular orden en ANT (llama al servicio web).
   Solo funciona si la orden tiene numero_orden asignado.
   Ejemplo: python -m src.main cancel --plate PDM5915 --reason "Cancelacion solicitada"

6. dequeue --plate <PLACA>
   Quitar una placa de la cola localmente (sin llamar a ANT).
   Funciona para placas en PENDIENTE_SOLICITUD o ERROR.
   Ejemplo: python -m src.main dequeue --plate PDM5915

7. status
   Ver en tiempo real las placas en cola, ejecutandose y con error.
   Muestra tiempo restante para finalizar cada orden activa.
   Ejemplo: python -m src.main status

8. report-incidencias [--limit <numero>]
   Reportar placas que fallaron (estado ERROR).
   Muestra etapa (SOLICITAR/FINALIZAR) y ultimo error.
   Ejemplo: python -m src.main report-incidencias --limit 10

9. retry-failed [--plate <PLACA> | --etapa <SOLICITAR|FINALIZAR>]
   Reintentar placas fallidas. Puedes especificar una placa o una etapa.
   - Si la placa ya tiene numeroOrden, solo se reintenta la finalizacion (inmediata).
   - Si no tiene numeroOrden, se reintenta desde la solicitud.
   Ejemplo: python -m src.main retry-failed --plate PDM5915
   Ejemplo: python -m src.main retry-failed --etapa FINALIZAR

10. sync-supabase
    Sube a Supabase todas las ordenes y auditoria ya existentes en SQLite.
    Util para poblar el panel web inicial.
    Ejemplo: python -m src.main sync-supabase

11. help
   Mostrar este mensaje de ayuda.
   Ejemplo: python -m src.main help

[SUPABASE]
Configura en .env:
- SUPABASE_URL
- SUPABASE_KEY
- SUPABASE_ORDERS_TABLE
- SUPABASE_AUDIT_TABLE

Para ingest-paste con responsable:
python -m src.main ingest-paste ca
Donde 'ca' identifica a Carlos.

[CONFIGURACION]
Todos los parametros (endpoint SOAP, credenciales, delays, etc.) se leen de .env
Archivo de base de datos: auto_rtv.db (SQLite)

[LIMITES]
- Maximo 2 solicitudes iniciadas sin finalizar simultaneamente
- Maximo 3 reintentos por operacion con backoff exponencial
- Espera aleatoria entre 2.5 y 5.0 minutos antes de finalizar orden

[ESTADOS]
- PENDIENTE_SOLICITUD: Placa en cola para solicitar
- SOLICITADA: Orden solicitada a ANT, esperando finalizacion
- FINALIZADA: Orden completada exitosamente
- ERROR: Fallo en solicitud o finalizacion (reintentable)
- ANULADA: Orden cancelada manualmente
"""
    print(help_text)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Procesamiento SOAP de ordenes por placa"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_txt = sub.add_parser("ingest-txt", help="Cargar placas desde archivo TXT")
    p_txt.add_argument("--file", required=True, help="Ruta del archivo TXT")
    p_txt.add_argument("--tag", help="Etiqueta opcional de 2 letras del responsable")
    p_txt.set_defaults(func=cmd_ingest_txt)

    p_paste = sub.add_parser("ingest-paste", help="Pegar placas manualmente")
    p_paste.add_argument("tag", nargs="?", help="Etiqueta opcional de 2 letras, por ejemplo: ca")
    p_paste.set_defaults(func=cmd_ingest_paste)

    p_once = sub.add_parser("run-once", help="Procesar una placa pendiente")
    p_once.set_defaults(func=cmd_run_once)

    p_loop = sub.add_parser("run-loop", help="Procesar placas continuamente")
    p_loop.set_defaults(func=cmd_run_loop)

    p_cancel = sub.add_parser("cancel", help="Anular orden de una placa")
    p_cancel.add_argument("--plate", required=True, help="Placa a anular")
    p_cancel.add_argument(
        "--reason",
        default="Cancelacion manual",
        help="Motivo de anulacion",
    )
    p_cancel.set_defaults(func=cmd_cancel)

    p_dequeue = sub.add_parser("dequeue", help="Quitar placa de la cola localmente (sin llamar a ANT)")
    p_dequeue.add_argument("--plate", required=True, help="Placa a eliminar de la cola")
    p_dequeue.set_defaults(func=cmd_dequeue)

    p_status = sub.add_parser("status", help="Ver placas en cola y ejecutandose")
    p_status.set_defaults(func=cmd_status)

    p_report = sub.add_parser(
        "report-incidencias",
        help="Reportar placas con fallo en solicitud o finalizacion",
    )
    p_report.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Numero maximo de incidencias a mostrar",
    )
    p_report.set_defaults(func=cmd_report_incidencias)

    p_retry = sub.add_parser(
        "retry-failed",
        help="Reintentar placas que fallaron en solicitud o finalizacion",
    )
    p_retry.add_argument(
        "--plate",
        help="Placa especifica a reintentar",
    )
    p_retry.add_argument(
        "--etapa",
        choices=["SOLICITAR", "FINALIZAR"],
        help="Etapa para reintentar (SOLICITAR o FINALIZAR)",
    )
    p_retry.set_defaults(func=cmd_retry_failed)

    p_supabase = sub.add_parser("sync-supabase", help="Sincronizar SQLite completo hacia Supabase")
    p_supabase.set_defaults(func=cmd_sync_supabase)

    p_help = sub.add_parser("help", help="Mostrar ayuda de comandos disponibles")
    p_help.set_defaults(func=cmd_help)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
