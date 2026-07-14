import json
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.schemas.generation import SoapNoteGenerationResult


class AiClientError(Exception):
    pass


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
            except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError, ValueError) as exc:
                last_error = exc

        raise AiClientError(f"SOAP generation request failed: {last_error}")


def get_openai_clinical_scribe_client() -> OpenAIClinicalScribeClient:
    settings = get_settings()
    return OpenAIClinicalScribeClient(
        timeout_seconds=settings.openai_timeout_seconds,
        max_retries=settings.openai_max_retries,
    )
