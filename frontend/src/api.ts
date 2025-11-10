import type { Message } from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function handleResponse(response: Response) {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Erro ao comunicar com o backend.");
  }
  return (await response.json()) as Message[];
}

export async function fetchHistory(): Promise<Message[]> {
  const response = await fetch(`${BASE_URL}/history`);
  return handleResponse(response);
}

export async function sendMessage(content: string): Promise<Message[]> {
  const response = await fetch(`${BASE_URL}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ content }),
  });
  return handleResponse(response);
}

export async function streamMessage(
  content: string,
  onChunk: (chunk: string) => void,
): Promise<void> {
  const response = await fetch(`${BASE_URL}/messages/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ content }),
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
