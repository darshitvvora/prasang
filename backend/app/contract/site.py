from typing import Literal

from pydantic import Field

from app.contract.common import ContractModel

ContactTopic = Literal["general", "artist_support", "payments", "report"]


class SiteInfo(ContractModel):
    support_email: str | None
    support_phone: str | None
    business_address: str | None


class ContactRequest(ContractModel):
    name: str = Field(min_length=1, max_length=120)
    contact: str = Field(min_length=3, max_length=255)
    topic: ContactTopic
    message: str = Field(min_length=10, max_length=4000)


class ContactResponse(ContractModel):
    id: str
