export interface AssessmentCodeEvent {
  diagnosis: string;
  code: string | null;
  description: string | null;
}

export interface GenerationEventDataMap {
  generation_started: {
    encounter_id: string;
    status: string;
  };
  section_delta: {
    section: "subjective" | "objective" | "assessment" | "plan";
    text: string;
  };
  assessment_code: AssessmentCodeEvent;
  warning: {
    message: string;
  };
  draft_saved: {
    draft_revision: number;
    updated_at: string;
  };
  generation_complete: {
    missing_information: string[];
    warnings: string[];
  };
  generation_error: {
    code: string;
    message: string;
  };
}
