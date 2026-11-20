"""Configuración del servicio. Viene del entorno o de .env (regla 7).

Sin valores por defecto para lo que importa: sin URL_BASE el servicio no arranca.
"""

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

LARGO_MINIMO_CLAVE = 20


class ConfiguracionInvalida(Exception):
    """Falta una variable obligatoria o tiene un valor inválido."""


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Conexión a la base `mercado`, con el rol api_lectura.
    url_base: str
    # Una clave por consumidor: "nombre:clave,nombre:clave".
    claves: str
    # Cuánto se espera una conexión libre antes de responder "servicio sin datos".
    espera_base_segundos: int = 5

    def claves_por_consumidor(self) -> dict[str, str]:
        resultado: dict[str, str] = {}
        for par in self.claves.split(","):
            nombre, _, clave = par.strip().partition(":")
            nombre, clave = nombre.strip(), clave.strip()
            if not nombre or len(clave) < LARGO_MINIMO_CLAVE or clave == "CAMBIAR":
                raise ConfiguracionInvalida(
                    "CLAVES tiene que tener la forma nombre:clave, separadas por coma, "
                    f"con claves de al menos {LARGO_MINIMO_CLAVE} caracteres. Mirá .env.ejemplo."
                )
            resultado[nombre] = clave
        return resultado


def cargar_configuracion() -> Configuracion:
    try:
        return Configuracion()  # type: ignore[call-arg]
    except ValidationError as error:
        faltantes = ", ".join(str(e["loc"][0]).upper() for e in error.errors())
        raise ConfiguracionInvalida(
            f"Configuración incompleta o inválida: {faltantes}. Mirá .env.ejemplo."
        ) from None
