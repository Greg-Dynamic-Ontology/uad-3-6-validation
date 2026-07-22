from urllib.parse import quote
from app.core.config import settings


class IriMintingService:
    def mint(self, *parts: str) -> str:
        cleaned = [quote(str(part).strip().replace(" ", "_"), safe="-_#/") for part in parts if str(part).strip()]
        return settings.iri_base + "/".join(cleaned)
