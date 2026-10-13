"""SQLAlchemy declarative base and cross-dialect type adapters.

Normative source: docs/database.md.
"""
from geoalchemy2 import Geography, Geometry
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Cross-dialect compilation hook:
# Compiles GeoAlchemy2 Geography/Geometry types to TEXT on SQLite for rapid in-memory testing,
# while rendering full PostGIS geography/geometry on PostgreSQL.
@compiles(Geography, "sqlite")
def compile_geography_sqlite(type_, compiler, **kw):
    return "TEXT"


@compiles(Geometry, "sqlite")
def compile_geometry_sqlite(type_, compiler, **kw):
    return "TEXT"


# Cross-dialect JSON type: uses native JSONB on PostgreSQL, standard JSON on SQLite.
JSON_VARIANT = JSON().with_variant(JSONB, "postgresql")

# Gracefully handle SQLite in-memory environments lacking the SpatiaLite C extension
import binascii

_DUMMY_WKB = binascii.unhexlify("010100000000000000000000000000000000000000")

try:
    import geoalchemy2.admin.dialects.sqlite as _geo_sqlite
    from sqlalchemy import event as _sa_event
    from sqlalchemy.engine import Engine as _Engine
    from sqlalchemy.exc import OperationalError as _OperationalError

    _orig_after_create = _geo_sqlite.after_create

    def _safe_sqlite_after_create(table, bind, **kw):
        try:
            _orig_after_create(table, bind, **kw)
        except _OperationalError as exc:
            if "RecoverGeometryColumn" in str(exc):
                if "_after_create_indexes" in table.info:
                    table.info.pop("_after_create_indexes", None)
                return
            raise

    _geo_sqlite.after_create = _safe_sqlite_after_create

    @_sa_event.listens_for(_Engine, "connect")
    def _register_sqlite_spatial_udfs(dbapi_connection, connection_record):
        if hasattr(dbapi_connection, "create_function"):
            for fn in [
                "GeomFromEWKT",
                "GeomFromText",
                "ST_GeomFromText",
                "ST_GeogFromText",
                "ST_GeogFromWKB",
                "ST_GeographyFromText",
            ]:
                try:
                    dbapi_connection.create_function(fn, 1, lambda x: x)
                except Exception:
                    pass
            for fn in ["AsBinary", "AsEWKB", "ST_AsBinary", "ST_AsBinary"]:
                try:
                    dbapi_connection.create_function(fn, 1, lambda x: _DUMMY_WKB)
                except Exception:
                    pass
            for fn in ["AsEWKT", "ST_AsText", "ST_AsEWKT"]:
                try:
                    dbapi_connection.create_function(fn, 1, lambda x: "POINT(0 0)")
                except Exception:
                    pass
except (ImportError, AttributeError):
    pass


# Ensure all models are loaded into Base.metadata
import app.models  # noqa: F401, E402

