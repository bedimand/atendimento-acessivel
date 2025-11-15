import { type FormEvent, type KeyboardEvent, useState } from "react";

type Props = {
  onSubmit: (content: string) => Promise<void> | void;
  disabled?: boolean;
  lastAudioUrl?: string | null;
  transcribing?: boolean;
};

export function MessageInput({
  onSubmit,
  disabled,
  lastAudioUrl,
  transcribing = false,
}: Props) {
  const [value, setValue] = useState("");
  const characterLimit = 500;

  const submitMessage = async () => {
    const sanitized = value.trim();
    if (!sanitized) return;
    await onSubmit(sanitized);
    setValue("");
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await submitMessage();
  };

  const handleKeyDown = async (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      await submitMessage();
    }
  };

  return (
    <form className="message-input" onSubmit={handleSubmit}>
      <label htmlFor="chat-input" className="sr-only">
        Escreva sua mensagem
      </label>
      <div className="input-shell">
        <textarea
          id="chat-input"
          value={value}
          onChange={(event) => setValue(event.target.value.slice(0, characterLimit))}
          placeholder="Digite uma mensagem acessível..."
          disabled={disabled || transcribing}
          rows={1}
          onKeyDown={handleKeyDown}
        />
        <button
          type="submit"
          className="icon-button send"
          disabled={disabled || transcribing || !value.trim()}
          aria-label="Enviar mensagem"
        >
          ➤
        </button>
      </div>
      <div className="input-hints">
        {transcribing ? (
          <span className="status-pill recording">Transcrevendo áudio...</span>
        ) : lastAudioUrl ? (
          <span className="status-pill ready">Áudio pronto para transcrição</span>
        ) : null}
        <span className="micro-copy">
          {value.length}/{characterLimit}
        </span>
      </div>
    </form>
  );
}
