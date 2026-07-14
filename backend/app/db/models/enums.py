from enum import Enum


class UserRole(str, Enum):
    PROVIDER = "provider"
    ADMIN = "admin"


class EncounterStatus(str, Enum):
    DRAFT = "draft"
    COMPLETED = "completed"


class TemplateSectionType(str, Enum):
    GENERAL = "general"
    SUBJECTIVE = "subjective"
    OBJECTIVE = "objective"
    ASSESSMENT = "assessment"
    PLAN = "plan"
