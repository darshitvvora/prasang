from app.contract.common import ContractModel


class City(ContractModel):
    name: str
    areas: list[str]


class LocationsResponse(ContractModel):
    cities: list[City]
