from app.contract.common import ContractModel, Phone, Role, UtcDatetime


class AuthProvidersResponse(ContractModel):
    google: bool
    phone_otp: bool


class Me(ContractModel):
    id: str
    email: str | None
    full_name: str
    phone: str | None
    role: Role
    avatar_url: str | None
    artist_slug: str | None
    created_at: UtcDatetime


class CreateMeRequest(ContractModel):
    role: Role
    full_name: str
    phone: Phone | None = None


class UpdateMeRequest(ContractModel):
    full_name: str | None = None
    phone: Phone | None = None
