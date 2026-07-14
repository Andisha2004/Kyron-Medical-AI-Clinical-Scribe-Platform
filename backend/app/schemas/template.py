from pydantic import BaseModel, Field


class TemplateSectionResponse(BaseModel):
    id: str
    section: str
    instructions: str
    sort_order: int


class TemplateListResponse(BaseModel):
    id: str
    name: str
    description: str | None
    is_active: bool
    sections: list[TemplateSectionResponse]


class TemplateSectionInput(BaseModel):
    section: str
    instructions: str = Field(min_length=1)
    sort_order: int = Field(ge=0)


class TemplateMutationRequest(BaseModel):
    name: str
    description: str | None = None
    is_active: bool = True
    sections: list[TemplateSectionInput]
