import json
from dataclasses import dataclass
import re

import httpx

from app.core.config import get_settings
from app.schemas.generation import AssessmentItem, SoapNoteGenerationResult
from app.schemas.voice import VoiceRewriteResult


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

    async def rewrite_soap_note_for_voice_command(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> VoiceRewriteResult:
        prompt = user_prompt.lower()
        command_match = re.search(r"provider voice edit request:\n(.+?)\n\n", prompt, re.DOTALL)
        command = command_match.group(1).strip() if command_match else ""
        subjective_match = re.search(r"subjective:\n(.*?)\n\nobjective:", user_prompt, re.DOTALL | re.IGNORECASE)
        objective_match = re.search(r"objective:\n(.*?)\n\nassessment:", user_prompt, re.DOTALL | re.IGNORECASE)
        assessment_match = re.search(r"assessment:\n(.*?)\n\nplan:", user_prompt, re.DOTALL | re.IGNORECASE)
        plan_match = re.search(r"plan:\n(.*)$", user_prompt, re.DOTALL | re.IGNORECASE)

        subjective = subjective_match.group(1).strip() if subjective_match else ""
        objective = objective_match.group(1).strip() if objective_match else ""
        assessment = assessment_match.group(1).strip() if assessment_match else ""
        plan = plan_match.group(1).strip() if plan_match else ""

        if "make it better" in command or "improve" in command:
            if subjective and "denies fever" not in subjective.lower() and "fever" in prompt:
                subjective = subjective.rstrip(".") + " and denies fever."
            if plan:
                plan = "Recommend supportive care, hydration, and return precautions if symptoms worsen."
            assistant_response = "I revised the SOAP note using the current encounter details."
        else:
            assistant_response = "I reviewed the SOAP note and kept the current wording."

        return VoiceRewriteResult(
            subjective=subjective,
            objective=objective,
            assessment=assessment,
            plan=plan,
            assistant_response=assistant_response,
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


@dataclass
class OllamaClinicalScribeClient:
    timeout_seconds: float

    def __post_init__(self) -> None:
        self.settings = get_settings()

    async def generate_soap_note(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> SoapNoteGenerationResult:
        parsed = await self._generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_name="soap_note_generation",
        )

        def normalize_text(value: object) -> str:
            if value is None:
                return ""

            if isinstance(value, str):
                return value.strip()

            if isinstance(value, list):
                return "\n".join(
                    f"- {normalize_text(item)}"
                    for item in value
                    if item is not None
                )

            if isinstance(value, dict):
                return "\n".join(
                    f"{str(key).replace('_', ' ').title()}: {normalize_text(item)}"
                    for key, item in value.items()
                )

            return str(value).strip()

        def normalize_string_list(value: object) -> list[str]:
            if value is None or value == "":
                return []

            if isinstance(value, list):
                return [
                    normalize_text(item)
                    for item in value
                    if normalize_text(item)
                ]

            normalized = normalize_text(value)
            return [normalized] if normalized else []

        def normalize_assessment(value: object) -> list[dict[str, str | None]]:
            if value is None or value == "":
                return []

            if isinstance(value, str):
                diagnosis = value.strip()
                return [
                    {
                        "diagnosis": diagnosis,
                        "icd10_code": None,
                        "description": None,
                    }
                ] if diagnosis else []

            if isinstance(value, dict):
                if any(
                    key in value
                    for key in ("diagnosis", "icd10_code", "description")
                ):
                    return [
                        {
                            "diagnosis": normalize_text(
                                value.get("diagnosis")
                                or value.get("description")
                                or "Clinical assessment"
                            ),
                            "icd10_code": (
                                normalize_text(value.get("icd10_code")) or None
                            ),
                            "description": (
                                normalize_text(value.get("description")) or None
                            ),
                        }
                    ]

                return [
                    {
                        "diagnosis": str(key).replace("_", " ").title(),
                        "icd10_code": None,
                        "description": normalize_text(item) or None,
                    }
                    for key, item in value.items()
                ]

            if isinstance(value, list):
                assessments: list[dict[str, str | None]] = []

                for item in value:
                    if isinstance(item, dict):
                        diagnosis = normalize_text(
                            item.get("diagnosis")
                            or item.get("condition")
                            or item.get("name")
                            or item.get("description")
                            or "Clinical assessment"
                        )

                        assessments.append(
                            {
                                "diagnosis": diagnosis,
                                "icd10_code": (
                                    normalize_text(
                                        item.get("icd10_code")
                                        or item.get("icd_code")
                                        or item.get("code")
                                    )
                                    or None
                                ),
                                "description": (
                                    normalize_text(item.get("description"))
                                    or None
                                ),
                            }
                        )
                    else:
                        diagnosis = normalize_text(item)
                        if diagnosis:
                            assessments.append(
                                {
                                    "diagnosis": diagnosis,
                                    "icd10_code": None,
                                    "description": None,
                                }
                            )

                return assessments

            diagnosis = normalize_text(value)
            return [
                {
                    "diagnosis": diagnosis,
                    "icd10_code": None,
                    "description": None,
                }
            ] if diagnosis else []

        parsed["subjective"] = normalize_text(parsed.get("subjective"))
        parsed["objective"] = normalize_text(parsed.get("objective"))
        parsed["assessment"] = normalize_assessment(parsed.get("assessment"))
        parsed["plan"] = normalize_text(parsed.get("plan"))
        parsed["missing_information"] = normalize_string_list(
            parsed.get("missing_information")
        )
        parsed["warnings"] = normalize_string_list(parsed.get("warnings"))

        return SoapNoteGenerationResult.model_validate(parsed)

    async def rewrite_soap_note_for_voice_command(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> VoiceRewriteResult:
        parsed = await self._generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_name="voice_rewrite",
        )
        return VoiceRewriteResult.model_validate(parsed)

    async def _generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_name: str,
    ) -> dict:
        request_payload = {
            "model": self.settings.ollama_model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.settings.ollama_base_url.rstrip('/')}/api/chat",
                    json=request_payload,
                )
            response.raise_for_status()
            body = response.json()
            content = body["message"]["content"]
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ValueError(f"{schema_name} response was not a JSON object.")
            return parsed
        except httpx.TimeoutException as exc:
            raise AiClientError("The local Ollama service timed out. Please retry.") from exc
        except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValueError) as exc:
            raise AiClientError(
                "The local Ollama service is unavailable or returned an invalid response."
            ) from exc


def get_openai_clinical_scribe_client() -> OpenAIClinicalScribeClient | MockClinicalScribeClient:
    settings = get_settings()
    if settings.llm_provider == "mock":
        return MockClinicalScribeClient()
    if settings.llm_provider == "ollama":
        return OllamaClinicalScribeClient(timeout_seconds=settings.ollama_timeout_seconds)
    return OpenAIClinicalScribeClient(
        timeout_seconds=settings.openai_timeout_seconds,
        max_retries=settings.openai_max_retries,
    )
