from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, computed_field

from app.config import settings


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LinkCreate(BaseModel):
    url: HttpUrl


class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    target_url: str
    created_at: datetime

    @computed_field
    @property
    def short_url(self) -> str:
        return f"{settings.base_url.rstrip('/')}/{self.code}"
