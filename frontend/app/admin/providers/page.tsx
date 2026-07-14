"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { ApiError } from "@/lib/api";
import { createProvider, getAdminProviders, updateProviderStatus } from "@/lib/admin";
import type { AdminProviderSummary, CreateProviderRequest } from "@/types/admin";

const initialForm: CreateProviderRequest = {
  first_name: "",
  last_name: "",
  email: "",
  password: "",
  specialty: "",
};

export default function AdminProvidersPage() {
  const [providers, setProviders] = useState<AdminProviderSummary[]>([]);
  const [form, setForm] = useState<CreateProviderRequest>(initialForm);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingProviders, setIsLoadingProviders] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function loadProviders() {
    setIsLoadingProviders(true);
    try {
      const response = await getAdminProviders();
      setProviders(response);
    } finally {
      setIsLoadingProviders(false);
    }
  }

  useEffect(() => {
    void loadProviders().catch((error: unknown) => {
      if (error instanceof ApiError) {
        setErrorMessage(error.message);
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Unable to load providers.");
      }
    });
  }, []);

  async function handleCreateProvider(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await createProvider({
        ...form,
        specialty: form.specialty?.trim() || undefined,
      });
      setForm(initialForm);
      await loadProviders();
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(error.message);
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Unable to create provider.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleToggleProvider(provider: AdminProviderSummary) {
    const nextActiveState = !provider.is_active;
    const confirmed = window.confirm(
      nextActiveState
        ? `Reactivate ${provider.first_name} ${provider.last_name}?`
        : `Deactivate ${provider.first_name} ${provider.last_name}?`,
    );
    if (!confirmed) {
      return;
    }

    try {
      await updateProviderStatus(provider.id, { is_active: nextActiveState });
      await loadProviders();
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(error.message);
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Unable to update provider status.");
      }
    }
  }

  return (
    <div>
      <PageHeader
        title="Manage providers"
        description="Create, activate, deactivate, and review provider accounts."
      />

      {errorMessage ? (
        <div
          className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          role="alert"
        >
          {errorMessage}
        </div>
      ) : null}

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="font-semibold text-slate-950">Providers</h2>
          {isLoadingProviders ? (
            <p className="mt-4 text-sm text-slate-600" role="status" aria-live="polite">
              Loading providers...
            </p>
          ) : null}
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-sm" data-testid="admin-provider-table">
              <thead className="text-left text-slate-500">
                <tr>
                  <th className="pb-3 font-medium">Name</th>
                  <th className="pb-3 font-medium">Email</th>
                  <th className="pb-3 font-medium">Specialty</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {providers.map((provider) => (
                  <tr key={provider.id}>
                    <td className="py-3 font-medium text-slate-900">
                      {provider.first_name} {provider.last_name}
                    </td>
                    <td className="py-3 text-slate-700">{provider.email}</td>
                    <td className="py-3 text-slate-700">{provider.specialty || "Not set"}</td>
                    <td className="py-3">
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                          provider.is_active
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {provider.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="py-3">
                      <Button
                        variant={provider.is_active ? "danger" : "secondary"}
                        onClick={() => void handleToggleProvider(provider)}
                      >
                        {provider.is_active ? "Deactivate" : "Reactivate"}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="font-semibold text-slate-950">Add provider</h2>
          <form
            className="mt-4 space-y-4"
            onSubmit={handleCreateProvider}
            data-testid="admin-provider-form"
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="provider-first-name"
                  className="block text-sm font-semibold text-slate-800"
                >
                  First name
                </label>
                <input
                  id="provider-first-name"
                  data-testid="provider-first-name-input"
                  value={form.first_name}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, first_name: event.target.value }))
                  }
                  placeholder="First name"
                  className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
                  required
                />
              </div>
              <div>
                <label
                  htmlFor="provider-last-name"
                  className="block text-sm font-semibold text-slate-800"
                >
                  Last name
                </label>
                <input
                  id="provider-last-name"
                  data-testid="provider-last-name-input"
                  value={form.last_name}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, last_name: event.target.value }))
                  }
                  placeholder="Last name"
                  className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
                  required
                />
              </div>
            </div>
            <div>
              <label
                htmlFor="provider-email"
                className="block text-sm font-semibold text-slate-800"
              >
                Email
              </label>
              <input
                id="provider-email"
                data-testid="provider-email-input"
                type="email"
                value={form.email}
                onChange={(event) =>
                  setForm((current) => ({ ...current, email: event.target.value }))
                }
                placeholder="Email"
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
                required
              />
            </div>
            <div>
              <label
                htmlFor="provider-specialty"
                className="block text-sm font-semibold text-slate-800"
              >
                Specialty
              </label>
              <input
                id="provider-specialty"
                data-testid="provider-specialty-input"
                type="text"
                value={form.specialty}
                onChange={(event) =>
                  setForm((current) => ({ ...current, specialty: event.target.value }))
                }
                placeholder="Specialty"
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
              />
            </div>
            <div>
              <label
                htmlFor="provider-password"
                className="block text-sm font-semibold text-slate-800"
              >
                Temporary password
              </label>
              <input
                id="provider-password"
                data-testid="provider-password-input"
                type="password"
                value={form.password}
                onChange={(event) =>
                  setForm((current) => ({ ...current, password: event.target.value }))
                }
                placeholder="Temporary password"
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
                required
                minLength={8}
              />
            </div>
            <Button type="submit" disabled={isSubmitting} data-testid="create-provider-button">
              {isSubmitting ? "Creating..." : "Create provider"}
            </Button>
          </form>
        </section>
      </div>
    </div>
  );
}
