"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { createEncounter } from "@/lib/encounters";
import { getActiveTemplates } from "@/lib/templates";
import type { TemplateSummary } from "@/types/template";

interface FormState {
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  templateId: string;
}

const initialFormState: FormState = {
  firstName: "",
  lastName: "",
  dateOfBirth: "",
  templateId: "",
};

export function NewEncounterForm() {
  const router = useRouter();
  const [formState, setFormState] = useState<FormState>(initialFormState);
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadTemplates() {
      try {
        const response = await getActiveTemplates();
        if (!isMounted) {
          return;
        }

        setTemplates(response);
        setFormState((current) => ({
          ...current,
          templateId: current.templateId || response[0]?.id || "",
        }));
      } catch (error) {
        if (!isMounted) {
          return;
        }

        if (error instanceof ApiError) {
          setErrorMessage(error.message);
        } else if (error instanceof Error) {
          setErrorMessage(error.message);
        } else {
          setErrorMessage("Unable to load templates.");
        }
      } finally {
        if (isMounted) {
          setIsLoadingTemplates(false);
        }
      }
    }

    void loadTemplates();

    return () => {
      isMounted = false;
    };
  }, []);

  const isFormValid = useMemo(() => {
    return (
      formState.firstName.trim().length > 0 &&
      formState.lastName.trim().length > 0 &&
      formState.dateOfBirth.length > 0 &&
      formState.templateId.length > 0
    );
  }, [formState]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isFormValid) {
      setErrorMessage("Complete all required fields before creating the encounter.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const response = await createEncounter({
        first_name: formState.firstName.trim(),
        last_name: formState.lastName.trim(),
        date_of_birth: formState.dateOfBirth,
        template_id: formState.templateId,
      });

      const params = new URLSearchParams({
        created: "1",
        reused: String(response.reused_existing_patient),
        priorHistory: String(response.has_prior_history),
        priorCount: String(response.prior_encounter_count),
      });
      router.push(`/provider/encounters/${response.encounter_id}?${params.toString()}`);
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(error.message);
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Unable to create the encounter.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mt-8 grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
      <section
        className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
        data-testid="new-encounter-form"
      >
        {errorMessage ? (
          <div
            className="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            role="alert"
          >
            {errorMessage}
          </div>
        ) : null}

        <form className="space-y-5" onSubmit={handleSubmit}>
          <div className="grid gap-5 sm:grid-cols-2">
            <div>
              <label htmlFor="firstName" className="block text-sm font-semibold text-slate-800">
                Patient first name
              </label>
              <input
                id="firstName"
                name="firstName"
                type="text"
                value={formState.firstName}
                data-testid="patient-first-name-input"
                onChange={(event) =>
                  setFormState((current) => ({ ...current, firstName: event.target.value }))
                }
                placeholder="Jordan"
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
                required
              />
            </div>

            <div>
              <label htmlFor="lastName" className="block text-sm font-semibold text-slate-800">
                Patient last name
              </label>
              <input
                id="lastName"
                name="lastName"
                type="text"
                value={formState.lastName}
                data-testid="patient-last-name-input"
                onChange={(event) =>
                  setFormState((current) => ({ ...current, lastName: event.target.value }))
                }
                placeholder="Test"
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
                required
              />
            </div>
          </div>

          <div>
            <label htmlFor="dateOfBirth" className="block text-sm font-semibold text-slate-800">
              Date of birth
            </label>
            <input
              id="dateOfBirth"
              name="dateOfBirth"
              type="date"
              value={formState.dateOfBirth}
              data-testid="patient-dob-input"
              onChange={(event) =>
                setFormState((current) => ({ ...current, dateOfBirth: event.target.value }))
              }
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
              required
            />
          </div>

          <div>
            <label htmlFor="templateId" className="block text-sm font-semibold text-slate-800">
              Note template
            </label>
            <select
              id="templateId"
              name="templateId"
              value={formState.templateId}
              data-testid="template-select"
              onChange={(event) =>
                setFormState((current) => ({ ...current, templateId: event.target.value }))
              }
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
              disabled={isLoadingTemplates || templates.length === 0}
              required
            >
              {templates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.name}
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs leading-5 text-slate-500" id="new-encounter-template-help">
              Use fictional patient information during development and demos.
            </p>
          </div>

          <Button
            type="submit"
            data-testid="create-encounter-button"
            disabled={isSubmitting || isLoadingTemplates || !isFormValid}
          >
            {isSubmitting ? "Creating encounter..." : "Create encounter"}
          </Button>
        </form>
      </section>

      <div className="space-y-6">
        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="font-semibold text-slate-950">What this creates</h2>
          <ul className="mt-4 space-y-3 text-sm text-slate-600">
            <li>An encounter in Draft status for the selected patient.</li>
            <li>An autosaved draft where transcript, observations, and SOAP content live.</li>
            <li>A workspace where you can document manually or generate the note with AI help.</li>
          </ul>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="font-semibold text-slate-950">Recommended next steps</h2>
          <ol className="mt-4 space-y-3 text-sm text-slate-600">
            <li>1. Add or capture the encounter transcript.</li>
            <li>2. Record clinical observations and exam findings.</li>
            <li>3. Generate or write the SOAP note, then review every section.</li>
            <li>4. Confirm ICD-10 codes and save a note version before finalizing.</li>
          </ol>
        </section>

        <section className="rounded-lg border border-slate-200 bg-slate-50 p-6">
          <p className="text-sm font-medium text-slate-900">Provider note</p>
          <p className="mt-2 text-sm text-slate-600">
            Voice dictation and voice editing are optional helpers. The encounter should still feel
            complete even if you type everything manually.
          </p>
        </section>
      </div>
    </div>
  );
}
