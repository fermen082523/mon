# AUTO-RTV

Servicio Python para procesar placas por lotes con SOAP (XML in / XML out).

## Flujo
1. Ingesta de placas por TXT o pegado manual.
2. Solicitar orden por placa.
3. Obtener numero de orden desde XML de respuesta.
4. Esperar tiempo aleatorio entre 2.5 y 5 minutos.
5. Finalizar orden con numero de orden.
6. Opcion de anular orden.

## Requisitos
- Python 3.11+
- Dependencias en `requirements.txt`

## Configuracion
1. Copiar `.env.example` a `.env`.
2. Ajustar endpoint y SOAP actions.

## Ejecucion
```bash
python -m src.main ingest-txt --file placas.txt
python -m src.main ingest-paste
python -m src.main run-once
python -m src.main run-loop
python -m src.main cancel --plate ABC123
```

## Notas
- El procesamiento es secuencial (una placa a la vez).
- Los XML enviados y recibidos quedan registrados en auditoria.
