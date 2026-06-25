from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "UAD 3.6 Compliance Scaffold"
    supported_uad_version: str = "3.6"
    iri_base: str = "https://example.org/uad36/"


settings = Settings()
