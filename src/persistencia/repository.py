from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

from src.domain.models import EstadoOrden, Orden
from src.persistencia.supabase_sync import SupabaseSync


class Repository:
    def __init__(self, db_path: str, supabase_sync: Optional[SupabaseSync] = None) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._supabase_sync = supabase_sync
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS ordenes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    placa TEXT NOT NULL,
                    numero_orden TEXT,
                    estado TEXT NOT NULL,
                    intentos INTEGER NOT NULL DEFAULT 0,
                    origen TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_ordenes_estado ON ordenes(estado);
                CREATE INDEX IF NOT EXISTS idx_ordenes_placa ON ordenes(placa);

                CREATE TABLE IF NOT EXISTS auditoria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    orden_id INTEGER,
                    evento TEXT NOT NULL,
                    request_xml TEXT,
                    response_xml TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (orden_id) REFERENCES ordenes(id)
                );
                """
            )
            conn.commit()
            # Migración: agregar columna finalizar_after si no existe
            try:
                conn.execute("ALTER TABLE ordenes ADD COLUMN finalizar_after TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Columna ya existe
            try:
                conn.execute("ALTER TABLE ordenes ADD COLUMN etiqueta TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass

    def _serialize_order(self, row: sqlite3.Row) -> dict[str, Optional[str]]:
        return {
            "local_id": row["id"],
            "placa": row["placa"],
            "numero_orden": row["numero_orden"],
            "estado": row["estado"],
            "intentos": row["intentos"],
            "origen": row["origen"],
            "etiqueta": row["etiqueta"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "finalizar_after": row["finalizar_after"],
        }

    def _serialize_audit(self, row: sqlite3.Row) -> dict[str, Optional[str]]:
        return {
            "local_id": row["id"],
            "orden_local_id": row["orden_id"],
            "evento": row["evento"],
            "request_xml": row["request_xml"],
            "response_xml": row["response_xml"],
            "error": row["error"],
            "created_at": row["created_at"],
        }

    def _sync_orders(self, conn: sqlite3.Connection, orden_ids: list[int]) -> None:
        if not self._supabase_sync or not self._supabase_sync.enabled or not orden_ids:
            return
        rows = conn.execute(
            f"""
            SELECT id, placa, numero_orden, estado, intentos, origen, etiqueta,
                   created_at, updated_at, finalizar_after
            FROM ordenes
            WHERE id IN ({','.join('?' for _ in orden_ids)})
            ORDER BY id ASC
            """,
            orden_ids,
        ).fetchall()
        if not rows:
            return
        try:
            self._supabase_sync.upsert_orders([self._serialize_order(row) for row in rows])
        except Exception as exc:
            print(f"[SUPABASE] No se pudo sincronizar ordenes: {exc}")

    def _sync_audits(self, conn: sqlite3.Connection, audit_ids: list[int]) -> None:
        if not self._supabase_sync or not self._supabase_sync.enabled or not audit_ids:
            return
        rows = conn.execute(
            f"""
            SELECT id, orden_id, evento, request_xml, response_xml, error, created_at
            FROM auditoria
            WHERE id IN ({','.join('?' for _ in audit_ids)})
            ORDER BY id ASC
            """,
            audit_ids,
        ).fetchall()
        if not rows:
            return
        try:
            self._supabase_sync.insert_audits([self._serialize_audit(row) for row in rows])
        except Exception as exc:
            print(f"[SUPABASE] No se pudo sincronizar auditoria: {exc}")

    def sync_all_to_supabase(self) -> tuple[int, int]:
        if not self._supabase_sync or not self._supabase_sync.enabled:
            raise RuntimeError("Supabase no esta configurado.")
        with self._lock, self._connect() as conn:
            order_rows = conn.execute(
                """
                SELECT id, placa, numero_orden, estado, intentos, origen, etiqueta,
                       created_at, updated_at, finalizar_after
                FROM ordenes
                ORDER BY id ASC
                """
            ).fetchall()
            audit_rows = conn.execute(
                """
                SELECT id, orden_id, evento, request_xml, response_xml, error, created_at
                FROM auditoria
                ORDER BY id ASC
                """
            ).fetchall()
        self._supabase_sync.upsert_orders([self._serialize_order(row) for row in order_rows])
        self._supabase_sync.insert_audits([self._serialize_audit(row) for row in audit_rows])
        return len(order_rows), len(audit_rows)

    def add_placa(self, placa: str, origen: str, etiqueta: Optional[str] = None) -> int:
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO ordenes (placa, estado, origen, etiqueta, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (placa, EstadoOrden.PENDIENTE_SOLICITUD.value, origen, etiqueta, now, now),
            )
            conn.commit()
            orden_id = int(cur.lastrowid)
            self._sync_orders(conn, [orden_id])
            return orden_id

    def get_next_pending(self) -> Optional[Orden]:
        """Obtener próxima orden en PENDIENTE_SOLICITUD para solicitar."""
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, placa, numero_orden, estado, intentos, etiqueta
                FROM ordenes
                WHERE estado = ?
                ORDER BY id ASC
                LIMIT 1
                """,
                (EstadoOrden.PENDIENTE_SOLICITUD.value,),
            ).fetchone()
            if not row:
                return None
            return Orden(
                id=row["id"],
                placa=row["placa"],
                numero_orden=row["numero_orden"],
                estado=EstadoOrden(row["estado"]),
                intentos=row["intentos"],
                etiqueta=row["etiqueta"],
            )

    def get_pending_tag_keys(self) -> list[str]:
        """Retorna las etiquetas pendientes en orden de llegada (min id por etiqueta)."""
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT COALESCE(etiqueta, '') AS tag_key, MIN(id) AS first_id
                FROM ordenes
                WHERE estado = ?
                GROUP BY COALESCE(etiqueta, '')
                ORDER BY first_id ASC
                """,
                (EstadoOrden.PENDIENTE_SOLICITUD.value,),
            ).fetchall()
            return [str(row["tag_key"]) for row in rows]

    def get_next_pending_by_tag_key(self, tag_key: str) -> Optional[Orden]:
        """Obtiene la siguiente pendiente de una etiqueta concreta.

        Usa tag_key='' para placas sin etiqueta.
        """
        with self._lock, self._connect() as conn:
            if tag_key == "":
                row = conn.execute(
                    """
                    SELECT id, placa, numero_orden, estado, intentos, etiqueta
                    FROM ordenes
                    WHERE estado = ?
                      AND (etiqueta IS NULL OR etiqueta = '')
                    ORDER BY id ASC
                    LIMIT 1
                    """,
                    (EstadoOrden.PENDIENTE_SOLICITUD.value,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT id, placa, numero_orden, estado, intentos, etiqueta
                    FROM ordenes
                    WHERE estado = ?
                      AND etiqueta = ?
                    ORDER BY id ASC
                    LIMIT 1
                    """,
                    (EstadoOrden.PENDIENTE_SOLICITUD.value, tag_key),
                ).fetchone()

            if not row:
                return None

            return Orden(
                id=row["id"],
                placa=row["placa"],
                numero_orden=row["numero_orden"],
                estado=EstadoOrden(row["estado"]),
                intentos=row["intentos"],
                etiqueta=row["etiqueta"],
            )

    def get_orden_lista_para_finalizar(self) -> Optional[Orden]:
        """Obtener la primera orden SOLICITADA cuyo timer ya expiró."""
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                                SELECT id, placa, numero_orden, estado, intentos, etiqueta
                FROM ordenes
                WHERE estado = ?
                  AND (finalizar_after IS NULL OR finalizar_after <= ?)
                ORDER BY finalizar_after ASC
                LIMIT 1
                """,
                (EstadoOrden.SOLICITADA.value, now),
            ).fetchone()
            if not row:
                return None
            return Orden(
                id=row["id"],
                placa=row["placa"],
                numero_orden=row["numero_orden"],
                estado=EstadoOrden(row["estado"]),
                intentos=row["intentos"],
                etiqueta=row["etiqueta"],
            )

    def count_pending(self) -> int:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(1) AS total
                FROM ordenes
                WHERE estado = ?
                """,
                (EstadoOrden.PENDIENTE_SOLICITUD.value,),
            ).fetchone()
            return int(row["total"]) if row else 0

    def count_solicitudes_sin_finalizar(self) -> int:
        """Contar ordenes SOLICITADAS que aun no se finalizan."""
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(1) AS total
                FROM ordenes
                WHERE estado = ?
                """,
                (EstadoOrden.SOLICITADA.value,),
            ).fetchone()
            return int(row["total"]) if row else 0

    def get_queue_overview(self) -> dict[str, Optional[str]]:
        """Resumen rápido para monitoreo de loop."""
        with self._lock, self._connect() as conn:
            pending_row = conn.execute(
                """
                SELECT COUNT(1) AS total
                FROM ordenes
                WHERE estado = ?
                """,
                (EstadoOrden.PENDIENTE_SOLICITUD.value,),
            ).fetchone()

            open_row = conn.execute(
                """
                SELECT COUNT(1) AS total
                FROM ordenes
                WHERE estado = ?
                """,
                (EstadoOrden.SOLICITADA.value,),
            ).fetchone()

            error_row = conn.execute(
                """
                SELECT COUNT(1) AS total
                FROM ordenes
                WHERE estado = ?
                """,
                (EstadoOrden.ERROR.value,),
            ).fetchone()

            finished_row = conn.execute(
                """
                SELECT COUNT(1) AS total
                FROM ordenes
                WHERE estado = ?
                """,
                (EstadoOrden.FINALIZADA.value,),
            ).fetchone()

            next_pending = conn.execute(
                """
                SELECT placa, etiqueta
                FROM ordenes
                WHERE estado = ?
                ORDER BY id ASC
                LIMIT 1
                """,
                (EstadoOrden.PENDIENTE_SOLICITUD.value,),
            ).fetchone()

            next_finalize = conn.execute(
                """
                SELECT placa, numero_orden, finalizar_after, etiqueta
                FROM ordenes
                WHERE estado = ?
                ORDER BY CASE WHEN finalizar_after IS NULL THEN 0 ELSE 1 END, finalizar_after ASC
                LIMIT 1
                """,
                (EstadoOrden.SOLICITADA.value,),
            ).fetchone()

            last_processed = conn.execute(
                """
                SELECT o.placa, o.etiqueta, a.evento, a.created_at
                FROM auditoria a
                LEFT JOIN ordenes o ON o.id = a.orden_id
                WHERE a.evento IN ('SOLICITAR_OK', 'FINALIZAR_OK', 'PROCESS_ERROR')
                ORDER BY a.id DESC
                LIMIT 1
                """
            ).fetchone()

        return {
            "pending_count": int(pending_row["total"]) if pending_row else 0,
            "open_count": int(open_row["total"]) if open_row else 0,
            "error_count": int(error_row["total"]) if error_row else 0,
            "finished_count": int(finished_row["total"]) if finished_row else 0,
            "next_pending_plate": next_pending["placa"] if next_pending else None,
            "next_pending_tag": next_pending["etiqueta"] if next_pending else None,
            "next_finalize_plate": next_finalize["placa"] if next_finalize else None,
            "next_finalize_order": next_finalize["numero_orden"] if next_finalize else None,
            "next_finalize_after": next_finalize["finalizar_after"] if next_finalize else None,
            "next_finalize_tag": next_finalize["etiqueta"] if next_finalize else None,
            "last_plate": last_processed["placa"] if last_processed else None,
            "last_tag": last_processed["etiqueta"] if last_processed else None,
            "last_event": last_processed["evento"] if last_processed else None,
            "last_at": last_processed["created_at"] if last_processed else None,
        }

    def get_open_order_by_placa(self, placa: str) -> Optional[Orden]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                                SELECT id, placa, numero_orden, estado, intentos, etiqueta
                FROM ordenes
                WHERE placa = ?
                  AND estado IN (?, ?)
                ORDER BY id DESC
                LIMIT 1
                """,
                (placa, EstadoOrden.SOLICITADA.value, EstadoOrden.ERROR.value),
            ).fetchone()
            if not row:
                return None
            return Orden(
                id=row["id"],
                placa=row["placa"],
                numero_orden=row["numero_orden"],
                estado=EstadoOrden(row["estado"]),
                intentos=row["intentos"],
                etiqueta=row["etiqueta"],
            )

    def mark_solicitada(self, orden_id: int, numero_orden: str, finalizar_after: str) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE ordenes
                SET numero_orden = ?, estado = ?, finalizar_after = ?, updated_at = ?
                WHERE id = ?
                """,
                (numero_orden, EstadoOrden.SOLICITADA.value, finalizar_after, now, orden_id),
            )
            conn.commit()
            self._sync_orders(conn, [orden_id])

    def mark_finalizada(self, orden_id: int) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE ordenes
                SET estado = ?, updated_at = ?
                WHERE id = ?
                """,
                (EstadoOrden.FINALIZADA.value, now, orden_id),
            )
            conn.commit()
            self._sync_orders(conn, [orden_id])

    def mark_anulada(self, orden_id: int) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE ordenes
                SET estado = ?, updated_at = ?
                WHERE id = ?
                """,
                (EstadoOrden.ANULADA.value, now, orden_id),
            )
            conn.commit()
            self._sync_orders(conn, [orden_id])

    def mark_error(self, orden_id: int, increment_attempt: bool = True) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with self._lock, self._connect() as conn:
            if increment_attempt:
                conn.execute(
                    """
                    UPDATE ordenes
                    SET estado = ?, intentos = intentos + 1, updated_at = ?
                    WHERE id = ?
                    """,
                    (EstadoOrden.ERROR.value, now, orden_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE ordenes
                    SET estado = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (EstadoOrden.ERROR.value, now, orden_id),
                )
            conn.commit()
            self._sync_orders(conn, [orden_id])

    def requeue_error(self, orden_id: int) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE ordenes
                SET estado = ?, updated_at = ?
                WHERE id = ?
                """,
                (EstadoOrden.PENDIENTE_SOLICITUD.value, now, orden_id),
            )
            conn.commit()
            self._sync_orders(conn, [orden_id])

    def get_status_summary(self, solo_hoy: bool = False) -> dict:
        """Retorna un resumen de todas las placas activas: en cola y en ejecución."""
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        hoy_inicio = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None
        ).isoformat()
        fecha_filter = f" AND created_at >= '{hoy_inicio}'" if solo_hoy else ""
        with self._lock, self._connect() as conn:
            # Pendientes de solicitar
            en_cola = conn.execute(
                f"""
                SELECT placa, etiqueta, created_at
                FROM ordenes
                WHERE estado = ?{fecha_filter}
                ORDER BY id ASC
                """,
                (EstadoOrden.PENDIENTE_SOLICITUD.value,),
            ).fetchall()

            # Solicitadas esperando finalizar
            ejecutando = conn.execute(
                f"""
                SELECT placa, etiqueta, numero_orden, finalizar_after
                FROM ordenes
                WHERE estado = ?{fecha_filter}
                ORDER BY finalizar_after ASC
                """,
                (EstadoOrden.SOLICITADA.value,),
            ).fetchall()

            # Con error
            con_error = conn.execute(
                f"""
                SELECT placa, etiqueta, numero_orden
                FROM ordenes
                WHERE estado = ?{fecha_filter}
                ORDER BY updated_at DESC
                """,
                (EstadoOrden.ERROR.value,),
            ).fetchall()

        return {
            "en_cola": [
                {"placa": r["placa"], "etiqueta": r["etiqueta"], "created_at": r["created_at"]}
                for r in en_cola
            ],
            "ejecutando": [
                {
                    "placa": r["placa"],
                    "etiqueta": r["etiqueta"],
                    "numero_orden": r["numero_orden"],
                    "finalizar_after": r["finalizar_after"],
                    "lista": (r["finalizar_after"] or "") <= now,
                }
                for r in ejecutando
            ],
            "con_error": [
                {"placa": r["placa"], "etiqueta": r["etiqueta"], "numero_orden": r["numero_orden"]}
                for r in con_error
            ],
        }

    def dequeue_plate(self, placa: str) -> bool:
        """Eliminar de la cola una placa (PENDIENTE_SOLICITUD o ERROR) marcándola ANULADA localmente."""
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id
                FROM ordenes
                WHERE placa = ?
                  AND estado IN (?, ?)
                """,
                (
                    placa,
                    EstadoOrden.PENDIENTE_SOLICITUD.value,
                    EstadoOrden.ERROR.value,
                ),
            ).fetchall()
            cursor = conn.execute(
                """
                UPDATE ordenes
                SET estado = ?, updated_at = ?
                WHERE placa = ?
                  AND estado IN (?, ?)
                """,
                (
                    EstadoOrden.ANULADA.value, now, placa,
                    EstadoOrden.PENDIENTE_SOLICITUD.value,
                    EstadoOrden.ERROR.value,
                ),
            )
            conn.commit()
            self._sync_orders(conn, [int(row["id"]) for row in rows])
            return cursor.rowcount > 0

    def save_audit(
        self,
        orden_id: Optional[int],
        evento: str,
        request_xml: Optional[str] = None,
        response_xml: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO auditoria (orden_id, evento, request_xml, response_xml, error, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (orden_id, evento, request_xml, response_xml, error, now),
            )
            conn.commit()
            self._sync_audits(conn, [int(cur.lastrowid)])

    def get_error_incidents(self, limit: int = 100) -> list[dict[str, Optional[str]]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    o.id,
                    o.placa,
                    o.numero_orden,
                    o.intentos,
                    o.updated_at,
                    (
                        SELECT a.evento
                        FROM auditoria a
                        WHERE a.orden_id = o.id
                          AND (
                              a.evento LIKE 'SOLICITAR_RETRY_%'
                              OR a.evento LIKE 'FINALIZAR_RETRY_%'
                              OR a.evento = 'PROCESS_ERROR'
                          )
                        ORDER BY a.id DESC
                        LIMIT 1
                    ) AS ultimo_evento,
                    (
                        SELECT a.error
                        FROM auditoria a
                        WHERE a.orden_id = o.id
                          AND a.error IS NOT NULL
                        ORDER BY a.id DESC
                        LIMIT 1
                    ) AS ultimo_error
                FROM ordenes o
                WHERE o.estado = ?
                ORDER BY o.updated_at DESC
                LIMIT ?
                """,
                (EstadoOrden.ERROR.value, limit),
            ).fetchall()

            incidents: list[dict[str, Optional[str]]] = []
            for row in rows:
                ultimo_evento = row["ultimo_evento"] or ""
                if "FINALIZAR" in ultimo_evento or row["numero_orden"]:
                    etapa = "FINALIZAR"
                else:
                    etapa = "SOLICITAR"

                incidents.append(
                    {
                        "id": str(row["id"]),
                        "placa": row["placa"],
                        "numero_orden": row["numero_orden"],
                        "intentos": str(row["intentos"]),
                        "updated_at": row["updated_at"],
                        "etapa": etapa,
                        "ultimo_evento": row["ultimo_evento"],
                        "ultimo_error": row["ultimo_error"],
                    }
                )

            return incidents

    def retry_errors_by_etapa(self, etapa: str) -> int:
        """Reintentar todas las placas en ERROR de una etapa específica (SOLICITAR/FINALIZAR).
        SOLICITAR: vuelven a PENDIENTE_SOLICITUD.
        FINALIZAR: vuelven a SOLICITADA (sin volver a solicitar).
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with self._lock, self._connect() as conn:
            if etapa.upper() == "SOLICITAR":
                rows = conn.execute(
                    """
                    SELECT id FROM ordenes
                    WHERE estado = ? AND numero_orden IS NULL
                    """,
                    (EstadoOrden.ERROR.value,),
                ).fetchall()
                # Reintentar las que no tienen numero_orden (fallaron en solicitud)
                cursor = conn.execute(
                    """
                    UPDATE ordenes
                    SET estado = ?, intentos = 0, updated_at = ?
                    WHERE estado = ? AND numero_orden IS NULL
                    """,
                    (EstadoOrden.PENDIENTE_SOLICITUD.value, now, EstadoOrden.ERROR.value),
                )
            elif etapa.upper() == "FINALIZAR":
                rows = conn.execute(
                    """
                    SELECT id FROM ordenes
                    WHERE estado = ? AND numero_orden IS NOT NULL
                    """,
                    (EstadoOrden.ERROR.value,),
                ).fetchall()
                # Reintentar las que sí tienen numero_orden (fallaron en finalización)
                # Vuelven a SOLICITADA con finalizar_after=NULL para que se procesen de inmediato
                cursor = conn.execute(
                    """
                    UPDATE ordenes
                    SET estado = ?, intentos = 0, finalizar_after = NULL, updated_at = ?
                    WHERE estado = ? AND numero_orden IS NOT NULL
                    """,
                    (EstadoOrden.SOLICITADA.value, now, EstadoOrden.ERROR.value),
                )
            else:
                return 0

            conn.commit()
            self._sync_orders(conn, [int(row["id"]) for row in rows])
            return cursor.rowcount

    def retry_error_by_plate(self, placa: str) -> bool:
        """Reintentar una placa específica en ERROR.
        Si tiene numero_orden: retorna a SOLICITADA (reintentar solo finalización).
        Si no: retorna a PENDIENTE_SOLICITUD (reintentar desde solicitud).
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with self._lock, self._connect() as conn:
            # Determinar el estado correcto según si tiene numero_orden
            row = conn.execute(
                "SELECT numero_orden FROM ordenes WHERE placa = ? AND estado = ?",
                (placa, EstadoOrden.ERROR.value),
            ).fetchone()
            if not row:
                return False

            nuevo_estado = (
                EstadoOrden.SOLICITADA.value
                if row["numero_orden"]
                else EstadoOrden.PENDIENTE_SOLICITUD.value
            )
            # Si vuelve a SOLICITADA, limpiar finalizar_after para procesar de inmediato
            if nuevo_estado == EstadoOrden.SOLICITADA.value:
                cursor = conn.execute(
                    """
                    UPDATE ordenes
                    SET estado = ?, intentos = 0, finalizar_after = NULL, updated_at = ?
                    WHERE placa = ? AND estado = ?
                    """,
                    (nuevo_estado, now, placa, EstadoOrden.ERROR.value),
                )
            else:
                cursor = conn.execute(
                    """
                    UPDATE ordenes
                    SET estado = ?, intentos = 0, updated_at = ?
                    WHERE placa = ? AND estado = ?
                    """,
                    (nuevo_estado, now, placa, EstadoOrden.ERROR.value),
                )
            conn.commit()
            rows = conn.execute(
                "SELECT id FROM ordenes WHERE placa = ? AND estado = ?",
                (placa, nuevo_estado),
            ).fetchall()
            self._sync_orders(conn, [int(item["id"]) for item in rows])
            return cursor.rowcount > 0
