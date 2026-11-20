"""Acceso a la base `mercado`.

Regla 2: el servicio solo lee. Lo garantizan dos cosas a la vez: el rol
api_lectura, que no tiene permisos de escritura, y la sesión, que se abre en
modo de solo lectura. Si un día alguien le da más permisos al rol, la sesión
igual rechaza cualquier escritura.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg_pool import ConnectionPool, PoolTimeout


class BaseSinDatos(Exception):
    """La base de mercado no responde."""


class BaseDeMercado:
    def __init__(self, url: str, espera_segundos: float = 5) -> None:
        self._espera = espera_segundos
        self._pool = ConnectionPool(
            url,
            min_size=1,
            max_size=4,
            open=False,
            timeout=espera_segundos,
            kwargs={"options": "-c default_transaction_read_only=on"},
        )

    def abrir(self) -> None:
        # Sin esperar: el servicio arranca aunque la base esté caída, y responde 503.
        self._pool.open(wait=False)

    def cerrar(self) -> None:
        self._pool.close()

    @contextmanager
    def conexion(self) -> Iterator[psycopg.Connection]:
        try:
            with self._pool.connection() as conexion:
                yield conexion
        except (PoolTimeout, psycopg.OperationalError) as error:
            raise BaseSinDatos() from error
