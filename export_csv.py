"""
export_csv.py
-------------
Consulta la tabla `mobilemonn` en PostgreSQL y exporta los resultados
a un archivo CSV conservando la nomenclatura exacta de la base de datos.

Uso:
    # Exportar todos los registros
    python export_csv.py

    # Filtrar por sesión
    python export_csv.py --session "Sesion_01"

    # Filtrar por rango de fechas
    python export_csv.py --start 2024-01-01 --end 2024-03-31

    # Combinar filtros
    python export_csv.py --session "Sesion_01" --start 2024-01-01 --end 2024-03-31

Dependencias:
    pip install psycopg2-binary python-dotenv
"""

import os
import csv
import argparse
from datetime import datetime
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Nombres de columnas — misma nomenclatura que la base de datos
# ---------------------------------------------------------------------------
COL_OBJECT_ID    = "objectid"
COL_SESSION_NAME = "session_name"
COL_TIMESTAMP    = "timestamp"
COL_LATITUDE     = "latitude"
COL_LONGITUDE    = "longitude"
COL_TEMPERATURE  = "temperature"
COL_PM1          = "pm1"
COL_PM10         = "pm10"
COL_PM25         = "pm25"
COL_HUMIDITY     = "humidity"

ALL_COLUMNS = [
    COL_OBJECT_ID,
    COL_SESSION_NAME,
    COL_TIMESTAMP,
    COL_LATITUDE,
    COL_LONGITUDE,
    COL_TEMPERATURE,
    COL_PM1,
    COL_PM10,
    COL_PM25,
    COL_HUMIDITY,
]

# ---------------------------------------------------------------------------
# Conexión
# ---------------------------------------------------------------------------

def get_connection():
    """Retorna una conexión activa a PostgreSQL."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        options=f"-c search_path={os.getenv('DB_SCHEMA', 'public')}",
    )

# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def fetch_data(session: str = None, start: str = None, end: str = None) -> list[dict]:
    """
    Consulta la tabla mobilemonn con filtros opcionales.

    Args:
        session: Nombre exacto de la sesión (session_name).
        start:   Fecha de inicio en formato YYYY-MM-DD.
        end:     Fecha de fin en formato YYYY-MM-DD.

    Returns:
        Lista de diccionarios con los registros.
    """
    columns_sql = ", ".join(ALL_COLUMNS)
    where_clauses = []
    params = []

    if session:
        where_clauses.append(f"{COL_SESSION_NAME} = %s")
        params.append(session)

    if start:
        where_clauses.append(f"{COL_TIMESTAMP} >= %s")
        params.append(start)

    if end:
        where_clauses.append(f"{COL_TIMESTAMP} <= %s")
        params.append(end)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    sql = f"""
        SELECT {columns_sql}
        FROM mobilemonn
        {where_sql}
        ORDER BY {COL_TIMESTAMP};
    """

    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params if params else None)
            return [dict(row) for row in cur.fetchall()]

# ---------------------------------------------------------------------------
# Export CSV
# ---------------------------------------------------------------------------

def export_to_csv(rows: list[dict], output_dir: str = "output") -> str:
    """
    Exporta una lista de registros a un archivo CSV.
    El nombre del archivo incluye timestamp de generación.

    Args:
        rows:       Lista de diccionarios a exportar.
        output_dir: Carpeta de destino (se crea si no existe).

    Returns:
        Ruta del archivo generado.
    """
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mobilemonn_{timestamp}.csv"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ALL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return filepath

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Exporta datos de mobilemonn a CSV."
    )
    parser.add_argument(
        "--session", type=str, default=None,
        help="Filtrar por nombre de sesión (session_name)."
    )
    parser.add_argument(
        "--start", type=str, default=None,
        help="Fecha de inicio (YYYY-MM-DD)."
    )
    parser.add_argument(
        "--end", type=str, default=None,
        help="Fecha de fin (YYYY-MM-DD)."
    )
    parser.add_argument(
        "--output-dir", type=str, default="output",
        help="Carpeta de destino para el CSV (default: output/)."
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print(" Conectando a la base de datos...")
    try:
        rows = fetch_data(
            session=args.session,
            start=args.start,
            end=args.end,
        )
    except psycopg2.OperationalError as e:
        print(f"Error de conexión: {e}")
        raise SystemExit(1)

    if not rows:
        print("La consulta no devolvio registros con los filtros aplicados.")
        raise SystemExit(0)

    print(f" {len(rows)} registros obtenidos.")

    filepath = export_to_csv(rows, output_dir=args.output_dir)
    print(f"CSV exportado en: {filepath}")


if __name__ == "__main__":
    main()
