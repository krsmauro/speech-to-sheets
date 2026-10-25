from pydantic import BaseModel, ConfigDict, Field, model_validator


class Columns(BaseModel):
    """Header text in row 1 of the sheet for each of the four roles."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    date: str = Field("Date", min_length=1)
    amount: str = Field("Amount", min_length=1)
    category: str = Field("Category", min_length=1)
    description: str = Field("Description", min_length=1)

    @model_validator(mode="after")
    def _headers_are_distinct(self) -> "Columns":
        headers = [h.casefold() for h in self.model_dump().values()]
        if len(set(headers)) != len(headers):
            raise ValueError("each role needs its own header, two roles share one")
        return self
