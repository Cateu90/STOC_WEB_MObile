from pydantic import BaseModel

class Mesa(BaseModel):
    id: int | None = None
    numero: int
    status: str  