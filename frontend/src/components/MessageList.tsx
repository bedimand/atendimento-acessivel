import type { Message } from "../types";
import { TTSButton } from "./TTSButton";

type Props = {
  messages: Message[];
};

function renderWithBold(content: string) {
  const pattern = /(\*\*[^*]+\*\*)/g;
  const segments = content.split(pattern);
  return segments.map((segment, index) => {
    if (segment.startsWith("**") && segment.endsWith("**") && segment.length > 4) {
      return (
        <strong key={`${index}-${segment}`}>
          {segment.slice(2, -2)}
        </strong>
      );
    }
    return <span key={`${index}-${segment}`}>{segment}</span>;
  });
}

export function MessageList({ messages }: Props) {
  return (
    <div className="message-list" role="log" aria-live="polite">
      {messages.length === 0 && <p className="empty-state">Envie uma mensagem para iniciar a conversa.</p>}
      {messages.map((message) => {
        const date = new Date(message.created_at);
        const label = message.origin === "bot" ? "Aurora" : "Você";
        return (
          <div key={message.id} className={`message-row ${message.origin}`}>
            <div className="bubble">
              <div className="bubble-header">
                <span>{label}</span>
                <span>{date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
              </div>
              <p>{renderWithBold(message.content)}</p>
              {message.origin === "bot" && (
                <div className="bubble-meta">
                  <TTSButton text={message.content} />
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
