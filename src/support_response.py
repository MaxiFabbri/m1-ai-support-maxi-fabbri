from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    OTHER = "other"


class SupportResponse(BaseModel):
    """Define los campos y las reglas de una respuesta de soporte válida."""

    # Rechaza campos que no pertenecen al contrato.
    model_config = {"extra": "forbid"}

    answer: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0, strict=True)
    category: Category
    actions: list[str]
