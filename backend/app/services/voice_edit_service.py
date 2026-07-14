import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.openai_client import AiClientError, get_openai_clinical_scribe_client
from app.core.config import get_settings
from app.db.models.encounter import Encounter
from app.db.models.encounter_draft import EncounterDraft
from app.schemas.voice import SoapSection, VoiceCommandRequest, VoiceEditOperation, VoiceRewriteResult
from app.services.audit_service import AuditService

SECTION_FIELDS: tuple[SoapSection, ...] = ("subjective", "objective", "assessment", "plan")
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


@dataclass
class VoiceEditResult:
    operation: VoiceEditOperation
    updated_section: SoapSection | None
    updated_text: str | None
    changed: bool
    assistant_response: str
    draft: EncounterDraft


class VoiceRewriteClient(Protocol):
    async def rewrite_soap_note_for_voice_command(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> VoiceRewriteResult: ...


class VoiceEditService:
    def __init__(self, *, ai_client: VoiceRewriteClient | None = None) -> None:
        self.ai_client = ai_client

    def ensure_draft(self, encounter: Encounter, draft: EncounterDraft | None) -> EncounterDraft:
        if draft is not None:
            return draft

        return EncounterDraft(
            encounter_id=encounter.id,
            transcript="",
            observations="",
            subjective="",
            objective="",
            assessment="",
            plan="",
            selected_icd10_codes=[],
            draft_revision=1,
        )

    async def apply_voice_command(
        self,
        *,
        session: AsyncSession,
        encounter: Encounter,
        payload: VoiceCommandRequest,
        actor_user_id: str,
    ) -> VoiceEditResult:
        draft = await session.scalar(
            select(EncounterDraft).where(EncounterDraft.encounter_id == encounter.id)
        )
        draft = self.ensure_draft(encounter, draft)

        if draft.id is None:
            session.add(draft)
            await session.flush()

        if payload.base_revision is not None and payload.base_revision != draft.draft_revision:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Draft revision conflict.",
            )

        if self.should_use_ai_rewrite(payload.command):
            updated_section = None
            updated_text = None
            operation = VoiceEditOperation(operation="rewrite_note")
            changed, assistant_response = await self.apply_ai_rewrite(
                encounter=encounter,
                draft=draft,
                command=payload.command,
            )
        else:
            operation = self.interpret_command(payload.command, draft)
            updated_section, updated_text, changed = self.apply_operation(draft, operation)
            assistant_response = self.build_assistant_response(operation, updated_section, changed)

        encounter.updated_at = draft.updated_at
        await AuditService.log_event(
            session,
            actor_user_id=actor_user_id,
            action="VOICE_EDIT_APPLIED",
            entity_type="encounter_draft",
            entity_id=draft.id,
            metadata_json={
                "encounter_id": encounter.id,
                "operation": operation.operation,
                "updated_section": updated_section,
            },
        )
        await session.commit()
        await session.refresh(draft)

        return VoiceEditResult(
            operation=operation,
            updated_section=updated_section,
            updated_text=updated_text,
            changed=changed,
            assistant_response=assistant_response,
            draft=draft,
        )

    def interpret_command(self, command: str, draft: EncounterDraft) -> VoiceEditOperation:
        normalized_command = " ".join(command.strip().split())
        lowered = normalized_command.lower().rstrip(".")

        if self.is_meta_revision_request(lowered):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "This request needs a rewrite-style model. Switch LLM_PROVIDER to ollama for "
                    "local note rewrites, or use a specific command like 'Add that the patient "
                    "denies fever', 'Move the knee pain into Subjective', or 'Shorten the Plan.'"
                ),
            )

        add_match = re.match(
            r"^(?:add|append|include)(?: that)? (.+?)(?: (?:to|into) (?:the )?(subjective|objective|assessment|plan))?$",
            lowered,
        )
        if add_match:
            content = self.normalize_inserted_text(add_match.group(1))
            target_section = add_match.group(2) or self.infer_default_append_section(content)
            return VoiceEditOperation(
                operation="append",
                target_section=target_section,
                new_text=content,
            )

        move_match = re.match(
            r"^move (.+?) (?:to|into) (?:the )?(subjective|objective|assessment|plan)$",
            lowered,
        )
        if move_match:
            requested_text = self.resolve_requested_text(move_match.group(1), draft)
            source_section = self.find_unique_section_containing_text(draft, requested_text)
            return VoiceEditOperation(
                operation="move",
                source_section=source_section,
                target_section=move_match.group(2),
                target_text=requested_text,
            )

        remove_match = re.match(r"^remove (.+)$", lowered)
        if remove_match:
            requested_text = self.resolve_requested_text(remove_match.group(1), draft)
            source_section = self.find_unique_section_containing_text(draft, requested_text)
            return VoiceEditOperation(
                operation="remove",
                target_section=source_section,
                target_text=requested_text,
            )

        replace_match = re.match(
            r"^replace (.+?) with (.+?)(?: in (?:the )?(subjective|objective|assessment|plan))?$",
            lowered,
        )
        if replace_match:
            replacement_text = self.normalize_inserted_text(replace_match.group(2))
            explicit_section = replace_match.group(3)
            target_text = self.resolve_requested_text(replace_match.group(1), draft, explicit_section)
            target_section = explicit_section or self.find_unique_section_containing_text(
                draft, target_text
            )
            return VoiceEditOperation(
                operation="replace",
                target_section=target_section,
                target_text=target_text,
                new_text=replacement_text,
            )

        shorten_match = re.match(
            r"^shorten (?:the )?(subjective|objective|assessment|plan)$",
            lowered,
        )
        if shorten_match:
            return VoiceEditOperation(operation="shorten", target_section=shorten_match.group(1))

        if self.looks_like_direct_note_content(lowered):
            normalized_content = self.normalize_spoken_content(normalized_command)
            target_section = self.infer_default_append_section(normalized_content)
            return VoiceEditOperation(
                operation="append",
                target_section=target_section,
                new_text=normalized_content,
            )

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Unsupported or ambiguous voice command. Try commands like "
                "'Add that the patient denies fever' or 'Move the knee pain into Subjective.'"
            ),
        )

    def normalize_inserted_text(self, content: str) -> str:
        cleaned = content.strip().strip(".")
        if not cleaned:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Voice command content cannot be empty.",
            )

        if "<" in cleaned or ">" in cleaned:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Voice edit text cannot contain HTML or code-like markup.",
            )

        if cleaned.startswith("the patient "):
            sentence = "Patient " + cleaned[len("the patient ") :]
        elif cleaned.startswith("patient "):
            sentence = cleaned.capitalize()
        else:
            sentence = cleaned[0].upper() + cleaned[1:]

        if not sentence.endswith("."):
            sentence += "."

        return sentence

    def looks_like_direct_note_content(self, command: str) -> bool:
        lowered = command.strip().lower()
        if not lowered:
            return False

        if len(lowered.split()) < 4:
            return False

        imperative_prefixes = (
            "add ",
            "append ",
            "include ",
            "move ",
            "remove ",
            "replace ",
            "shorten ",
        )
        if lowered.startswith(imperative_prefixes):
            return False

        content_markers = (
            "patient ",
            "the patient ",
            "patient is saying that ",
            "patient says that ",
            "patient said that ",
            "the patient is saying that ",
            "the patient says that ",
            "the patient said that ",
            "provider ",
            "exam ",
            "examination ",
            "blood pressure ",
            "bp ",
            "heart rate ",
            "temperature ",
            "reports ",
            "denies ",
            "complains ",
            "follow up ",
        )
        return lowered.startswith(content_markers)

    def is_meta_revision_request(self, command: str) -> bool:
        lowered = command.strip().lower()
        meta_phrases = (
            "make it better",
            "improve this",
            "improve the note",
            "fix the note",
            "rewrite the note",
            "rewrite this note",
            "clean up the note",
            "add all the notes",
            "soap note",
            "soap notes",
            "summarize everything",
        )
        return any(phrase in lowered for phrase in meta_phrases)

    def should_use_ai_rewrite(self, command: str) -> bool:
        return self.ai_client is not None and self.is_meta_revision_request(command)

    def normalize_spoken_content(self, command: str) -> str:
        cleaned = " ".join(command.strip().split())
        lowered = cleaned.lower()

        replacements = (
            ("the patient is saying that ", "patient reports "),
            ("the patient says that ", "patient reports "),
            ("the patient said that ", "patient reports "),
            ("patient is saying that ", "patient reports "),
            ("patient says that ", "patient reports "),
            ("patient said that ", "patient reports "),
            ("the patient is talking that ", "patient reports "),
            ("the patient talking that ", "patient reports "),
            ("the patient reports that ", "patient reports "),
            ("patient reports that ", "patient reports "),
            ("provider says ", ""),
            ("provider said ", ""),
        )

        for source, target in replacements:
            if lowered.startswith(source):
                cleaned = target + cleaned[len(source) :]
                lowered = cleaned.lower()
                break

        cleaned = re.sub(r"\bthey're\b", "they are", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bcan't\b", "cannot", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bwon't\b", "will not", cleaned, flags=re.IGNORECASE)

        return self.normalize_inserted_text(cleaned)

    def infer_default_append_section(self, content: str) -> SoapSection:
        lowered = content.lower()
        if any(keyword in lowered for keyword in ("plan", "follow up", "return", "medication")):
            return "plan"
        if any(keyword in lowered for keyword in ("diagnosis", "osteoarthritis", "assessment")):
            return "assessment"
        if any(keyword in lowered for keyword in ("vital", "blood pressure", "exam", "objective")):
            return "objective"
        return "subjective"

    def resolve_requested_text(
        self,
        raw_target: str,
        draft: EncounterDraft,
        explicit_section: SoapSection | None = None,
    ) -> str:
        cleaned = raw_target.strip().strip(".")
        lowered = cleaned.lower()
        if lowered.startswith("the sentence about "):
            keyword = cleaned[len("the sentence about ") :]
            return self.find_sentence_by_keyword(draft, keyword, explicit_section)
        if lowered.startswith("sentence about "):
            keyword = cleaned[len("sentence about ") :]
            return self.find_sentence_by_keyword(draft, keyword, explicit_section)
        if lowered.startswith("the "):
            candidate = cleaned[4:]
            if explicit_section:
                section_text = self.get_section_text(draft, explicit_section)
                if candidate.lower() in section_text.lower():
                    return candidate
            try:
                return self.find_sentence_by_keyword(draft, candidate, explicit_section)
            except HTTPException:
                return candidate
        return cleaned

    def find_sentence_by_keyword(
        self,
        draft: EncounterDraft,
        keyword: str,
        explicit_section: SoapSection | None = None,
    ) -> str:
        keyword_lower = keyword.strip().lower()
        matches: list[str] = []
        sections = (explicit_section,) if explicit_section else SECTION_FIELDS

        for section in sections:
            if section is None:
                continue
            sentences = self.split_sentences(self.get_section_text(draft, section))
            for sentence in sentences:
                if keyword_lower in sentence.lower():
                    matches.append(sentence)

        unique_matches = list(dict.fromkeys(matches))
        if len(unique_matches) == 1:
            return unique_matches[0]
        if len(unique_matches) > 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The voice request matches multiple sentences. Please be more specific.",
            )

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The requested text could not be found in the current note.",
        )

    def find_unique_section_containing_text(
        self,
        draft: EncounterDraft,
        target_text: str,
    ) -> SoapSection:
        matching_sections = [
            section
            for section in SECTION_FIELDS
            if target_text.lower() in self.get_section_text(draft, section).lower()
        ]

        if len(matching_sections) == 1:
            return matching_sections[0]
        if len(matching_sections) > 1:
            ranked_matches: list[tuple[int, int, SoapSection]] = []
            for section in matching_sections:
                section_text = self.get_section_text(draft, section)
                sentences = self.split_sentences(self.get_section_text(draft, section))
                best_sentence_length = max(
                    (
                        len(sentence)
                        for sentence in sentences
                        if target_text.lower() in sentence.lower()
                    ),
                    default=0,
                )
                ranked_matches.append((best_sentence_length, len(section_text), section))

            ranked_matches.sort(reverse=True)
            if len(ranked_matches) >= 2:
                first = ranked_matches[0]
                second = ranked_matches[1]
                if first[0] > second[0] or (first[0] == second[0] and first[1] > second[1]):
                    return first[2]

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The voice request is ambiguous because the text appears in multiple sections.",
            )

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The requested text could not be found in the current note.",
        )

    def apply_operation(
        self,
        draft: EncounterDraft,
        operation: VoiceEditOperation,
    ) -> tuple[SoapSection, str, bool]:
        if operation.operation == "append":
            assert operation.target_section and operation.new_text
            current = self.get_section_text(draft, operation.target_section)
            if operation.new_text.lower() in current.lower():
                return operation.target_section, current, False
            updated = current.rstrip()
            if updated:
                updated = f"{updated}\n{operation.new_text}"
            else:
                updated = operation.new_text
            self.set_section_text(draft, operation.target_section, updated)
            return operation.target_section, updated, True

        if operation.operation == "replace":
            assert operation.target_section and operation.target_text and operation.new_text
            current = self.get_section_text(draft, operation.target_section)
            if operation.target_text.lower() not in current.lower():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="The text to replace was not found in the selected section.",
                )
            updated = self.replace_first_case_insensitive(
                current, operation.target_text, operation.new_text
            )
            self.set_section_text(draft, operation.target_section, updated)
            return operation.target_section, updated, updated != current

        if operation.operation == "remove":
            assert operation.target_section and operation.target_text
            current = self.get_section_text(draft, operation.target_section)
            updated = self.remove_first_case_insensitive(current, operation.target_text)
            self.set_section_text(draft, operation.target_section, updated)
            return operation.target_section, updated, updated != current

        if operation.operation == "move":
            assert operation.source_section and operation.target_section and operation.target_text
            source = self.get_section_text(draft, operation.source_section)
            matched_text = self.extract_first_case_insensitive_match(source, operation.target_text)
            updated_source = self.remove_first_case_insensitive(source, operation.target_text)
            self.set_section_text(draft, operation.source_section, updated_source)

            target = self.get_section_text(draft, operation.target_section).rstrip()
            updated_target = (
                f"{target}\n{matched_text}" if target else matched_text
            )
            self.set_section_text(draft, operation.target_section, updated_target)
            return operation.target_section, updated_target, updated_target != target

        if operation.operation == "shorten":
            assert operation.target_section
            current = self.get_section_text(draft, operation.target_section)
            updated = self.shorten_section_text(current)
            self.set_section_text(draft, operation.target_section, updated)
            return operation.target_section, updated, updated != current

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported voice edit operation.",
        )

    def get_section_text(self, draft: EncounterDraft, section: SoapSection) -> str:
        return getattr(draft, section) or ""

    def set_section_text(self, draft: EncounterDraft, section: SoapSection, value: str) -> None:
        setattr(draft, section, self.clean_multiline_text(value))

    def split_sentences(self, text: str) -> list[str]:
        cleaned = text.strip()
        if not cleaned:
            return []

        pieces = re.split(r"(?<=[.!?])\s+|\n+", cleaned)
        return [piece.strip() for piece in pieces if piece.strip()]

    def shorten_section_text(self, text: str) -> str:
        sentences = self.split_sentences(text)
        if len(sentences) <= 1:
            return text.strip()

        shortened = " ".join(sentences[:2]).strip()
        if len(shortened) > 220:
            shortened = shortened[:217].rstrip() + "..."
        return shortened

    def replace_first_case_insensitive(self, text: str, old: str, new: str) -> str:
        pattern = re.compile(re.escape(old), re.IGNORECASE)
        replaced, count = pattern.subn(new, text, count=1)
        if count == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The requested text could not be found for replacement.",
            )
        return self.clean_multiline_text(replaced)

    def remove_first_case_insensitive(self, text: str, target: str) -> str:
        pattern = re.compile(re.escape(target), re.IGNORECASE)
        replaced, count = pattern.subn("", text, count=1)
        if count == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The requested text could not be found for removal.",
            )
        return self.clean_multiline_text(replaced)

    def extract_first_case_insensitive_match(self, text: str, target: str) -> str:
        pattern = re.compile(re.escape(target), re.IGNORECASE)
        match = pattern.search(text)
        if not match:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The requested text could not be found for movement.",
            )
        return text[match.start() : match.end()]

    def clean_multiline_text(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines()]
        compact_lines = [line for line in lines if line]
        return "\n".join(compact_lines).strip()

    async def apply_ai_rewrite(
        self,
        *,
        encounter: Encounter,
        draft: EncounterDraft,
        command: str,
    ) -> tuple[bool, str]:
        if self.ai_client is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Local rewrite support is not configured.",
            )

        system_prompt = (PROMPTS_DIR / "voice_rewrite.txt").read_text()
        user_prompt = self.build_voice_rewrite_prompt(encounter=encounter, draft=draft, command=command)

        try:
            rewrite = await self.ai_client.rewrite_soap_note_for_voice_command(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        except AiClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

        changed = False
        for section in SECTION_FIELDS:
            new_value = self.clean_multiline_text(getattr(rewrite, section))
            current_value = self.get_section_text(draft, section)
            if new_value != current_value:
                self.set_section_text(draft, section, new_value)
                changed = True

        return changed, rewrite.assistant_response

    def build_voice_rewrite_prompt(
        self,
        *,
        encounter: Encounter,
        draft: EncounterDraft,
        command: str,
    ) -> str:
        transcript = (draft.transcript or "").strip() or "Not provided."
        observations = (draft.observations or "").strip() or "Not provided."
        subjective = (draft.subjective or "").strip() or "Not provided."
        objective = (draft.objective or "").strip() or "Not provided."
        assessment = (draft.assessment or "").strip() or "Not provided."
        plan = (draft.plan or "").strip() or "Not provided."
        return (
            f"Encounter ID: {encounter.id}\n"
            f"Provider voice edit request:\n{command.strip()}\n\n"
            f"Transcript:\n{transcript}\n\n"
            f"Clinical observations:\n{observations}\n\n"
            f"Current SOAP note:\n"
            f"Subjective:\n{subjective}\n\n"
            f"Objective:\n{objective}\n\n"
            f"Assessment:\n{assessment}\n\n"
            f"Plan:\n{plan}\n\n"
            "Return JSON with keys subjective, objective, assessment, plan, assistant_response."
        )

    def build_assistant_response(
        self,
        operation: VoiceEditOperation,
        updated_section: SoapSection | None,
        changed: bool,
    ) -> str:
        section_label = updated_section.title() if updated_section else "the note"
        if not changed:
            if operation.operation == "append":
                return f"That content was already in {section_label}, so I left it unchanged."
            if operation.operation == "shorten":
                return f"{section_label} was already concise, so I left it unchanged."
            if operation.operation == "rewrite_note":
                return "I reviewed the SOAP note, but the local model did not make any safe changes."
            return f"I reviewed {section_label}, but nothing changed."

        if operation.operation == "append":
            return f"I added that to {section_label}."
        if operation.operation == "move":
            return f"I moved that content into {section_label}."
        if operation.operation == "remove":
            return f"I removed that from {section_label}."
        if operation.operation == "replace":
            return f"I updated the wording in {section_label}."
        if operation.operation == "shorten":
            return f"I shortened {section_label}."
        if operation.operation == "rewrite_note":
            return "I revised the SOAP note using the current transcript and observations."
        return "I updated the note."


def get_voice_edit_service() -> VoiceEditService:
    settings = get_settings()
    ai_client = get_openai_clinical_scribe_client() if settings.llm_provider in {"ollama", "mock"} else None
    return VoiceEditService(ai_client=ai_client)
