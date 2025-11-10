import { type FormEvent, type KeyboardEvent, useState } from "react";

type Props = {
  onSubmit: (content: string) => Promise<void> | void;
  disabled?: boolean;
  lastAudioUrl?: string | null;
};

export function MessageInput({ onSubmit, disabled, lastAudioUrl }: Props) {
  const [value, setValue] = useState("");

  const submitMessage = async () => {
    if (!value.trim()) return;
    await onSubmit(value.trim());
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
          onChange={(event) => setValue(event.target.value)}
          placeholder="Digite uma mensagem acessível..."
          disabled={disabled}
          rows={1}
          onKeyDown={handleKeyDown}
        />
        <button type="submit" className="icon-button send" disabled={disabled || !value.trim()}>
          ➤
        </button>
      </div>
      {lastAudioUrl && (
        <p className="audio-hint">Áudio gravado pronto para upload futuro.</p>
      )}
    </form>
  );
}
