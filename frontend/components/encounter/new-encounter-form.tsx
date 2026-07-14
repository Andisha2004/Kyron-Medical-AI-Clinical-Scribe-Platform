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
    <section className="mt-8 max-w-2xl rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      {errorMessage ? (
        <div className="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
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
          <p className="mt-2 text-xs leading-5 text-slate-500">
            Use fictional patient information during development and demos.
          </p>
        </div>

        <Button type="submit" disabled={isSubmitting || isLoadingTemplates || !isFormValid}>
          {isSubmitting ? "Creating encounter..." : "Create encounter"}
        </Button>
      </form>
    </section>
  );
}
