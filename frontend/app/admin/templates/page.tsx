"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { ApiError } from "@/lib/api";
import {
  createAdminTemplate,
  deleteAdminTemplate,
  getAdminTemplates,
  updateAdminTemplate,
} from "@/lib/admin";
import type { TemplateMutationRequest, TemplateSummary } from "@/types/template";

const sectionOptions = ["general", "subjective", "objective", "assessment", "plan"] as const;

function createEmptyTemplateForm(): TemplateMutationRequest {
  return {
    name: "",
    description: "",
    is_active: true,
    sections: sectionOptions.map((section, index) => ({
      section,
      instructions: "",
      sort_order: index,
    })),
  };
}

export default function AdminTemplatesPage() {
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("new");
  const [form, setForm] = useState<TemplateMutationRequest>(createEmptyTemplateForm());
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function loadTemplates() {
    const response = await getAdminTemplates();
    setTemplates(response);
  }

  useEffect(() => {
    void loadTemplates().catch((error: unknown) => {
      if (error instanceof ApiError) {
        setErrorMessage(error.message);
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Unable to load templates.");
      }
    });
  }, []);

  useEffect(() => {
    if (selectedTemplateId === "new") {
      setForm(createEmptyTemplateForm());
      return;
    }

    const selectedTemplate = templates.find((template) => template.id === selectedTemplateId);
    if (!selectedTemplate) {
      return;
    }

    setForm({
      name: selectedTemplate.name,
      description: selectedTemplate.description,
      is_active: selectedTemplate.is_active,
      sections: selectedTemplate.sections.map((section) => ({
        section: section.section,
        instructions: section.instructions,
        sort_order: section.sort_order,
      })),
    });
  }, [selectedTemplateId, templates]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      if (selectedTemplateId === "new") {
        await createAdminTemplate(form);
      } else {
        await updateAdminTemplate(selectedTemplateId, form);
      }
      await loadTemplates();
      setSelectedTemplateId("new");
      setForm(createEmptyTemplateForm());
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(error.message);
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Unable to save template.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteTemplate() {
    if (selectedTemplateId === "new") {
      return;
    }

    const confirmed = window.confirm(
      "Deactivate this template? Existing encounters will keep their reference, but it will no longer be available for new active use.",
    );
    if (!confirmed) {
      return;
    }

    try {
      await deleteAdminTemplate(selectedTemplateId);
      await loadTemplates();
      setSelectedTemplateId("new");
      setForm(createEmptyTemplateForm());
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(error.message);
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Unable to delete template.");
      }
    }
  }

  return (
    <div>
      <PageHeader
        title="Note templates"
        description="Manage SOAP note templates and organization-specific documentation rules."
      />

      {errorMessage ? (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </div>
      ) : null}

      <div className="mt-8 grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-semibold text-slate-950">Templates</h2>
            <Button variant="secondary" onClick={() => setSelectedTemplateId("new")}>
              New template
            </Button>
          </div>

          <div className="mt-4 space-y-3">
            {templates.map((template) => (
              <button
                key={template.id}
                type="button"
                onClick={() => setSelectedTemplateId(template.id)}
                className={`block w-full rounded-lg border px-4 py-3 text-left ${
                  selectedTemplateId === template.id
                    ? "border-slate-900 bg-slate-100"
                    : "border-slate-200 bg-slate-50"
                }`}
              >
                <p className="font-semibold text-slate-900">{template.name}</p>
                <p className="mt-1 text-sm text-slate-600">
                  {template.description || "No description"}
                </p>
                <p className="mt-2 text-xs tracking-wide text-slate-500 uppercase">
                  {template.is_active ? "Active" : "Inactive"}
                </p>
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="font-semibold text-slate-950">
            {selectedTemplateId === "new" ? "Create template" : "Edit template"}
          </h2>

          <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
            <input
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              placeholder="Template name"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
              required
            />
            <textarea
              value={form.description ?? ""}
              onChange={(event) =>
                setForm((current) => ({ ...current, description: event.target.value }))
              }
              placeholder="Template description"
              rows={3}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
            />

            <label className="flex items-center gap-3 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) =>
                  setForm((current) => ({ ...current, is_active: event.target.checked }))
                }
              />
              Template is active
            </label>

            <div className="space-y-4">
              {form.sections.map((section, index) => (
                <div
                  key={section.section}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-4"
                >
                  <p className="text-sm font-semibold text-slate-900 capitalize">
                    {section.section}
                  </p>
                  <textarea
                    value={section.instructions}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        sections: current.sections.map((item, itemIndex) =>
                          itemIndex === index
                            ? { ...item, instructions: event.target.value }
                            : item,
                        ),
                      }))
                    }
                    rows={3}
                    className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
                    placeholder={`Instructions for ${section.section}`}
                    required
                  />
                </div>
              ))}
            </div>

            <div className="flex flex-wrap gap-3">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting
                  ? "Saving..."
                  : selectedTemplateId === "new"
                    ? "Create template"
                    : "Save changes"}
              </Button>
              {selectedTemplateId !== "new" ? (
                <Button type="button" variant="danger" onClick={() => void handleDeleteTemplate()}>
                  Deactivate template
                </Button>
              ) : null}
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
