import { useCallback, useEffect, useState } from "react";
import { fetchHistory, streamMessage } from "./api";
import { AudioRecorderButton } from "./components/AudioRecorderButton";
import { MessageInput } from "./components/MessageInput";
import { MessageList } from "./components/MessageList";
import { VLibrasWidget } from "./components/VLibrasWidget";
import type { Message } from "./types";
import "./App.css";

function App() {
  const [renderedMessages, setRenderedMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastAudioUrl, setLastAudioUrl] = useState<string | null>(null);
  const [historyVersion, setHistoryVersion] = useState(0);

  const createLocalMessage = useCallback(
    (origin: Message["origin"], content: string): Message => ({
      id: Date.now() + Math.floor(Math.random() * 1000),
      origin,
      content,
      created_at: new Date().toISOString(),
    }),
    [],
  );

  useEffect(() => {
    fetchHistory()
      .then((data) => {
        setRenderedMessages(data);
      })
      .catch(() => setError("Não foi possível carregar o histórico."))
      .finally(() => setLoading(false));
  }, [historyVersion]);

  const handleSubmit = useCallback(
    async (content: string) => {
      const sanitized = content.trim();
      if (!sanitized) return;

      const userMessage = createLocalMessage("user", sanitized);
      setRenderedMessages((prev) => [...prev, userMessage]);

      const botMessage = createLocalMessage("bot", "");
      setRenderedMessages((prev) => [...prev, botMessage]);

      setSending(true);
      setError(null);
      try {
        await streamMessage(sanitized, (chunk) => {
          if (!chunk) return;
          setRenderedMessages((prev) =>
            prev.map((message) =>
              message.id === botMessage.id
                ? { ...message, content: message.content + chunk }
                : message,
            ),
          );
        });
        setHistoryVersion((value) => value + 1);
      } catch {
        setError("Falha ao enviar mensagem.");
        setRenderedMessages((prev) =>
          prev.filter((message) => message.id !== botMessage.id),
        );
      } finally {
        setSending(false);
      }
    },
    [createLocalMessage],
  );

  return (
    <div className="app-frame full-chat">
      <VLibrasWidget />
      <section className="chat-shell">
        <header className="chat-header">
          <div className="chat-peer">
            <div className="avatar large">CI</div>
            <div>
              <strong>Chatbot Inclusivo</strong>
              <span>Respostas inclusivas, TTS e VLibras</span>
            </div>
          </div>
        </header>

        <div className="chat-body">
          {loading ? (
            <p className="loading-state">Carregando mensagens...</p>
          ) : (
            <MessageList messages={renderedMessages} />
          )}
        </div>

        {error && <p className="error-text">{error}</p>}

        <footer className="chat-footer">
          <AudioRecorderButton onAudioReady={setLastAudioUrl} compact />
          <MessageInput onSubmit={handleSubmit} disabled={sending} lastAudioUrl={lastAudioUrl} />
        </footer>
      </section>
    </div>
  );
}

export default App;
