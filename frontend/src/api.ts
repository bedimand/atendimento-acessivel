import type { AvailabilitySlot, Booking, Message, UserProfile } from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function serializeProfile(profile?: UserProfile | null) {
  if (!profile) {
    return undefined;
  }
  return {
    full_name: profile.fullName,
    patient_id: profile.patientId || undefined,
    pronouns: profile.pronouns || undefined,
    disabilities: profile.disabilities,
    accessibility_needs: profile.accessibilityNeeds,
    mobility_notes: profile.mobilityNotes || undefined,
    contact_preference: profile.contactPreference || undefined,
    notes: profile.notes || undefined,
  };
}

async function handleResponse(response: Response) {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Erro ao comunicar com o backend.");
  }
  return (await response.json()) as Message[];
}
async function handleTranscriptResponse(response: Response) {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Erro ao transcrever áudio.");
  }

  const payload = (await response.json()) as { transcript: string };
  return payload.transcript;
}

export async function fetchHistory(): Promise<Message[]> {
  const response = await fetch(`${BASE_URL}/history`);
  return handleResponse(response);
}

export async function sendMessage(content: string, profile?: UserProfile | null): Promise<Message[]> {
  const response = await fetch(`${BASE_URL}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ content, profile: serializeProfile(profile) }),
  });
  return handleResponse(response);
}

export async function streamMessage(
  content: string,
  onChunk: (chunk: string) => void,
  profile?: UserProfile | null,
): Promise<void> {
  const response = await fetch(`${BASE_URL}/messages/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ content, profile: serializeProfile(profile) }),
  });

  if (!response.ok || !response.body) {
    const errorText = await response.text();
    throw new Error(errorText || "Erro ao iniciar streaming com o backend.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      onChunk(decoder.decode());
      break;
    }
    const text = decoder.decode(value, { stream: true });
    if (text) {
      onChunk(text);
    }
  }
}

export async function transcribeAudioFile(file: File): Promise<string> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${BASE_URL}/transcriptions`, {
    method: "POST",
    body: formData,
  });

  return handleTranscriptResponse(response);
}

export async function fetchAvailability(days = 7): Promise<AvailabilitySlot[]> {
  const response = await fetch(`${BASE_URL}/availability?days=${days}`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Erro ao obter disponibilidade.");
  }
  return (await response.json()) as AvailabilitySlot[];
}

export async function fetchBookings(filter?: { date?: string; slot?: string }): Promise<Booking[]> {
  const response = await fetch(`${BASE_URL}/tools/bookings`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(filter ?? {}),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Erro ao listar agendamentos.");
  }
  const payload = (await response.json()) as { bookings: Booking[] };
  return payload.bookings ?? [];
}
