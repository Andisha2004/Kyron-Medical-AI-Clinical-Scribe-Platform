import { api } from "@/lib/api";
import type { NoteVersion } from "@/types/note";

export async function getNoteVersions(noteId: string): Promise<NoteVersion[]> {
  return api.get<NoteVersion[]>(`/api/notes/${noteId}/versions`);
}
