import json
from dataclasses import dataclass
import re

import httpx

from app.core.config import get_settings
from app.schemas.generation import AssessmentItem, SoapNoteGenerationResult


class AiClientError(Exception):
    pass


@dataclass
class MockClinicalScribeClient:
    async def generate_soap_note(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> SoapNoteGenerationResult:
        prompt = user_prompt.lower()

        patient_history_match = re.search(r"relevant prior patient history:\n(.+)$", prompt, re.DOTALL)
        patient_history = patient_history_match.group(1).strip() if patient_history_match else ""

        if "knee" in prompt:
            diagnosis = "Right knee osteoarthritis"
            code = "M17.11"
            description = "Unilateral primary osteoarthritis, right knee"
            subjective = "Patient reports chronic right knee pain that worsens with stairs."
            objective = "No objective examination findings were documented."
            plan = "Continue physical therapy, encourage home exercises, and follow up in four weeks."
        elif "cough" in prompt or "sore throat" in prompt:
            diagnosis = "Upper respiratory infection"
            code = "J06.9"
            description = "Acute upper respiratory infection, unspecified"
            subjective = "Patient reports cough and sore throat for several days and denies fever."
            objective = "No objective measurements were documented."
            plan = "Recommend supportive care, hydration, and return precautions if symptoms worsen."
        else:
            diagnosis = "General follow-up evaluation"
            code = "Z09"
            description = "Follow-up examination after treatment"
            subjective = "Patient reports ongoing symptoms requiring follow-up assessment."
            objective = "No objective examination findings were documented."
            plan = "Continue monitoring symptoms and follow up as clinically indicated."

        if "denies fever" in prompt and "denies fever" not in subjective.lower():
            subjective += " The patient denies fever."

        if "physical therapy" in patient_history:
            subjective += " The patient is returning after physical therapy with partial improvement."

        warnings: list[str] = []
        missing_information: list[str] = []
        if "no exam findings" in prompt or "not provided" in prompt:
            missing_information.append("Objective examination details were not provided.")

        if "blood pressure" in prompt and "objective" not in prompt:
            warnings.append("Vital signs were mentioned without a structured objective section.")

        return SoapNoteGenerationResult(
            subjective=subjective,
            objective=objective,
            assessment=[
                AssessmentItem(
                    diagnosis=diagnosis,
                    icd10_code=code,
                    description=description,
                )
            ],
            plan=plan,
            missing_information=missing_information,
            warnings=warnings,
        )


@dataclass
class OpenAIClinicalScribeClient:
    timeout_seconds: float
    max_retries: int

    def __post_init__(self) -> None:
        self.settings = get_settings()

    async def generate_soap_note(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> SoapNoteGenerationResult:
        if not self.settings.openai_api_key or self.settings.openai_api_key.startswith("replace_with_"):
            raise AiClientError("OPENAI_API_KEY is not configured.")

        request_payload = {
            "model": self.settings.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "soap_note_generation",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "subjective": {"type": "string"},
                            "objective": {"type": "string"},
                            "assessment": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "diagnosis": {"type": "string"},
                                        "icd10_code": {"type": ["string", "null"]},
                                        "description": {"type": ["string", "null"]},
                                    },
                                    "required": ["diagnosis", "icd10_code", "description"],
                                    "additionalProperties": False,
                                },
                            },
                            "plan": {"type": "string"},
                            "missing_information": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "warnings": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": [
                            "subjective",
                            "objective",
                            "assessment",
                            "plan",
                            "missing_information",
                            "warnings",
                        ],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            },
        }

        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for _ in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=request_payload,
                    )
                response.raise_for_status()
                body = response.json()
                content = body["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return SoapNoteGenerationResult.model_validate(parsed)
            except httpx.TimeoutException as exc:
                last_error = exc
            except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError, ValueError) as exc:
                last_error = exc

        if isinstance(last_error, httpx.TimeoutException):
            raise AiClientError("The AI note generation service timed out. Please retry.")

        raise AiClientError("The AI note generation service is unavailable right now. Please retry.")


def get_openai_clinical_scribe_client() -> OpenAIClinicalScribeClient | MockClinicalScribeClient:
    settings = get_settings()
    if settings.llm_provider == "mock":
        return MockClinicalScribeClient()
    return OpenAIClinicalScribeClient(
        timeout_seconds=settings.openai_timeout_seconds,
        max_retries=settings.openai_max_retries,
    )
