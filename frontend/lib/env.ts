function readPublicEnvironmentVariable(name: string, value: string | undefined): string {
  if (!value) {
    throw new Error(`Missing required public environment variable: ${name}`);
  }

  return value;
}

function readBooleanEnvironmentVariable(
  name: string,
  value: string | undefined,
  defaultValue: boolean,
): boolean {
  if (value === undefined) {
    return defaultValue;
  }

  if (value === "true") {
    return true;
  }

  if (value === "false") {
    return false;
  }

  throw new Error(`${name} must be either "true" or "false".`);
}

export const publicEnv = {
  apiBaseUrl: readPublicEnvironmentVariable(
    "NEXT_PUBLIC_API_BASE_URL",
    process.env.NEXT_PUBLIC_API_BASE_URL,
  ),
  appUrl: readPublicEnvironmentVariable("NEXT_PUBLIC_APP_URL", process.env.NEXT_PUBLIC_APP_URL),
  appName: process.env.NEXT_PUBLIC_APP_NAME?.trim() || "Kyron Medical Clinical Assistant",
  enableVoiceAgent: readBooleanEnvironmentVariable(
    "NEXT_PUBLIC_ENABLE_VOICE_AGENT",
    process.env.NEXT_PUBLIC_ENABLE_VOICE_AGENT,
    false,
  ),
  enableIcdSearch: readBooleanEnvironmentVariable(
    "NEXT_PUBLIC_ENABLE_ICD_SEARCH",
    process.env.NEXT_PUBLIC_ENABLE_ICD_SEARCH,
    false,
  ),
  enableRealtimeTranscript: readBooleanEnvironmentVariable(
    "NEXT_PUBLIC_ENABLE_REALTIME_TRANSCRIPT",
    process.env.NEXT_PUBLIC_ENABLE_REALTIME_TRANSCRIPT,
    false,
  ),
} as const;
