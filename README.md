# MM-DataIngestionService
Mobile Monitoring Data Ingestion Service 
# 🐘 PostgreSQL — Documentación de Integración

> Guía para conectarse directamente a la base de datos PostgreSQL,
> Explorar las tablas disponibles, ejecutar consultas y exportar resultados a CSV.

---

## 📋 Índice

- [Requisitos](#requisitos)
- [Configuración de Conexión](#configuración-de-conexión)
- [Verificar Conexión](#verificar-conexión)
- [Tablas Disponibles](#tablas-disponibles)
- [Integración en tu Script](#integración-en-tu-script)
- [Script de Export CSV](#script-de-export-csv)
- [Notas y Advertencias](#notas-y-advertencias)
- [Historial de Cambios](#historial-de-cambios)

---

## Requisitos

| Herramienta | Versión mínima | Instalación |
|---|---|---|
| Python | 3.8+ | [python.org](https://python.org) |
| psycopg2 | 2.9+ | `pip install psycopg2-binary` |
| python-dotenv | 1.0+ | `pip install python-dotenv` |
| PostgreSQL client (opcional) | 13+ | `brew install libpq` / `apt install postgresql-client` |

```bash
# Instalar todo de una vez
pip install psycopg2-binary python-dotenv
```

> `csv` y `argparse` vienen incluidos en la librería estándar de Python — no requieren instalación.

---

## Configuración de Conexión

### 1. Crear archivo `.env`

Crea un archivo `.env` en la raíz del proyecto con tus credenciales:

```bash
# .env
DB_HOST=localhost          # IP o hostname del servidor
DB_PORT=5432               # Puerto por defecto de PostgreSQL
DB_NAME=nombre_base_datos  # Nombre de la base de datos
DB_USER=tu_usuario
DB_PASSWORD=tu_contraseña
DB_SCHEMA=public           # Esquema por defecto
```

### 2. Agregar `.env` al `.gitignore`

```bash
# .gitignore
.env
*.csv
__pycache__/
```

> ⚠️ **Nunca** subas el archivo `.env` al repositorio. Comparte las credenciales
> únicamente a través de un gestor de secretos o de forma segura con tu equipo.

---

## Verificar Conexión

### Desde terminal (psql)

```bash
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME
# Te pedirá la contraseña de DB_PASSWORD
```

### Desde Python

```python
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
    print("✅ Conexión exitosa")
    conn.close()

except psycopg2.OperationalError as e:
    print(f"❌ Error de conexión: {e}")
```

---

## Tablas Disponibles

### Query para explorar tablas del esquema

```sql
-- Lista todas las tablas del esquema actual con su tamaño
SELECT
    table_name,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) AS tamaño
FROM
    information_schema.tables
WHERE
    table_schema = 'public'
ORDER BY
    table_name;
```

```sql
-- Ver columnas de una tabla específica
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'mobilemonn'
ORDER BY
    ordinal_position;
```

---

### `mobilemonn`

**Descripción:** Registros de monitoreos móviles de calidad del aire. Cada fila representa una medición georreferenciada capturada durante una sesión de monitoreo, incluyendo contaminantes particulados, temperatura y humedad.

| Columna en BD | Tipo | Nullable | Descripción |
|---|---|---|---|
| `objectid` | `INT` | No | Llave primaria / identificador único del registro |
| `session_name` | `VARCHAR` | Sí | Nombre de la sesión de monitoreo |
| `timestamp` | `TIMESTAMP` | Sí | Fecha y hora de la medición |
| `latitude` | `FLOAT` | Sí | Latitud geográfica del punto de medición |
| `longitude` | `FLOAT` | Sí | Longitud geográfica del punto de medición |
| `temperature` | `FLOAT` | Sí | 🌡️ Temperatura |
| `pm1` | `FLOAT` | Sí | 🌫️ PM1 — Material particulado < 1 µm |
| `pm10` | `FLOAT` | Sí | 🌫️ PM10 — Material particulado < 10 µm |
| `pm25` | `FLOAT` | Sí | 🌫️ PM2.5 — Material particulado < 2.5 µm |
| `humidity` | `FLOAT` | Sí | 💧 Humedad relativa |

> ℹ️ Todas las columnas están en **minúsculas**. PostgreSQL es case-insensitive por defecto,
> pero se recomienda escribirlas siempre en minúsculas para consistencia.

#### Constantes recomendadas para tu script

```python
# columns.py — nombres de columnas de la tabla mobilemonn
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
```

---

## Integración en tu Script

### Módulo de conexión reutilizable (`db.py`)

```python
# db.py
import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

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


def run_query(sql: str, params: tuple = None) -> list[dict]:
    """
    Ejecuta una consulta SELECT y devuelve los resultados
    como lista de diccionarios {columna: valor}.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
```

---

### Consultas de ejemplo sobre `mobilemonn`

```python
# queries_example.py
from db import run_query
from columns import (
    COL_OBJECT_ID, COL_SESSION_NAME, COL_TIMESTAMP,
    COL_LATITUDE, COL_LONGITUDE,
    COL_TEMPERATURE, COL_PM1, COL_PM10, COL_PM25, COL_HUMIDITY,
)

# 1. Vista previa de los primeros 10 registros
rows = run_query(f"""
    SELECT
        {COL_OBJECT_ID},
        {COL_SESSION_NAME},
        {COL_TIMESTAMP},
        {COL_LATITUDE},
        {COL_LONGITUDE},
        {COL_TEMPERATURE} AS "Temperature",
        {COL_PM25}        AS "PM25",
        {COL_HUMIDITY}    AS "Humidity"
    FROM mobilemonn
    ORDER BY {COL_TIMESTAMP} DESC
    LIMIT 10;
""")

for row in rows:
    print(row)


# 2. Filtrar por sesión específica
rows = run_query(f"""
    SELECT
        {COL_OBJECT_ID},
        {COL_SESSION_NAME},
        {COL_TIMESTAMP},
        {COL_LATITUDE},
        {COL_LONGITUDE},
        {COL_TEMPERATURE} AS "Temperature",
        {COL_PM1}         AS "PM1",
        {COL_PM10}        AS "PM10",
        {COL_PM25}        AS "PM25",
        {COL_HUMIDITY}    AS "Humidity"
    FROM mobilemonn
    WHERE {COL_SESSION_NAME} = %s
    ORDER BY {COL_TIMESTAMP};
""", params=("nombre_de_sesion",))


# 3. Filtrar por rango de fechas
rows = run_query(f"""
    SELECT
        {COL_TIMESTAMP},
        {COL_LATITUDE},
        {COL_LONGITUDE},
        {COL_PM1}   AS "PM1",
        {COL_PM10}  AS "PM10",
        {COL_PM25}  AS "PM25"
    FROM mobilemonn
    WHERE {COL_TIMESTAMP} BETWEEN %s AND %s
    ORDER BY {COL_TIMESTAMP};
""", params=("2024-01-01", "2024-03-31"))


# 4. Promedio de contaminantes por sesión
rows = run_query(f"""
    SELECT
        {COL_SESSION_NAME}                        AS "Session_Name",
        ROUND(AVG({COL_TEMPERATURE})::numeric, 2) AS "Temperature",
        ROUND(AVG({COL_PM1})::numeric, 2)         AS "PM1",
        ROUND(AVG({COL_PM10})::numeric, 2)        AS "PM10",
        ROUND(AVG({COL_PM25})::numeric, 2)        AS "PM25",
        ROUND(AVG({COL_HUMIDITY})::numeric, 2)    AS "Humidity",
        COUNT(*)                                  AS "Total_Measurements"
    FROM mobilemonn
    GROUP BY {COL_SESSION_NAME}
    ORDER BY "PM25" DESC;
""")
```

---

## Script de Export CSV

El script `export_csv.py` consulta la tabla `mobilemonn` y exporta los resultados
a un archivo `.csv` conservando exactamente la nomenclatura de la base de datos.

### Estructura de archivos

```
proyecto/
├── .env
├── export_csv.py
└── output/                  ← CSVs generados aquí
    └── mobilemonn_20240315_142500.csv
```

### Uso

```bash
# Exportar todos los registros
python export_csv.py

# Filtrar por sesión
python export_csv.py --session "Sesion_01"

# Filtrar por rango de fechas
python export_csv.py --start 2024-01-01 --end 2024-03-31

# Combinar filtros
python export_csv.py --session "Sesion_01" --start 2024-01-01 --end 2024-03-31

# Cambiar carpeta de destino
python export_csv.py --output-dir /ruta/a/mi/carpeta
```

### Parámetros disponibles

| Parámetro | Tipo | Requerido | Default | Descripción |
|---|---|---|---|---|
| `--session` | `str` | No | `None` | Filtra por `session_name` |
| `--start` | `str` | No | `None` | Fecha de inicio `YYYY-MM-DD` |
| `--end` | `str` | No | `None` | Fecha de fin `YYYY-MM-DD` |
| `--output-dir` | `str` | No | `output/` | Carpeta de destino del CSV |

### Columnas del CSV generado

El CSV respeta exactamente los nombres de la base de datos:

```
objectid, session_name, timestamp, latitude, longitude,
temperature, pm1, pm10, pm25, humidity
```

### Ejemplo de salida en consola

```
🔌 Conectando a la base de datos...
✅ 1248 registros obtenidos.
📄 CSV exportado en: output/mobilemonn_20240315_142500.csv
```

---

## Notas y Advertencias

> 💡 **Tip:** Usa siempre parámetros `%s` en lugar de f-strings para construir el
> WHERE de tus queries — evita inyecciones SQL:
> ```python
> # ✅ Correcto
> cur.execute("SELECT * FROM mobilemonn WHERE session_name = %s", (sesion,))
>
> # ❌ Peligroso
> cur.execute(f"SELECT * FROM mobilemonn WHERE session_name = '{sesion}'")
> ```

> ⚠️ **`timestamp` es palabra reservada** en PostgreSQL. Aunque funciona en minúsculas
> sin comillas en la mayoría de los casos, si obtienes errores de sintaxis prueba
> entrecomillándola: `"timestamp"`.

> 🔒 **Permisos mínimos recomendados:** El usuario de BD solo debe tener `SELECT`
> sobre las tablas necesarias. Nunca uses el usuario `postgres` directamente.

---

## Historial de Cambios

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| `1.0.0` | 2026-MM-DD | @usuario | Versión inicial: conexión PostgreSQL | Agregada tabla `mobilemonn` y ejemplos de queries | Corrección: nombres de columnas en minúsculas según esquema real | Agregado `export_csv.py` y documentación de export CSV |

---

*Mantén este archivo actualizado cada vez que se agreguen tablas o cambien las credenciales de acceso.*
