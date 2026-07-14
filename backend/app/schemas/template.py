from pydantic import BaseModel


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
