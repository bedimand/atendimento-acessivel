import { useSpeechSynthesis } from "../hooks/useSpeechSynthesis";

type Props = {
  text: string;
};

export function TTSButton({ text }: Props) {
  const { supported, speak } = useSpeechSynthesis();

  if (!supported) {
    return null;
  }

  return (
    <button type="button" className="icon-button tts" onClick={() => speak(text)}>
      🔊
    </button>
  );
}
