import { useEffect } from "react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";

type Props = {
  onAudioReady?: (audioUrl: string | null) => void;
  compact?: boolean;
};

export function AudioRecorderButton({ onAudioReady, compact = false }: Props) {
  const recorder = useAudioRecorder();

  useEffect(() => {
    onAudioReady?.(recorder.audioUrl);
  }, [recorder.audioUrl, onAudioReady]);

  return (
    <div className={`audio-recorder ${compact ? "compact" : ""}`}>
      <button
        type="button"
        className={`icon-button mic ${recorder.status === "recording" ? "recording" : ""}`}
        onClick={
          recorder.status === "recording" ? recorder.stopRecording : recorder.startRecording
        }
        aria-pressed={recorder.status === "recording"}
      >
        {recorder.status === "recording" ? "⏹" : "🎙️"}
      </button>
      {recorder.audioUrl && !compact && (
        <div className="audio-preview">
          <audio controls src={recorder.audioUrl} />
          <button type="button" className="pill-button secondary" onClick={recorder.reset}>
            Descartar
          </button>
        </div>
      )}
      {recorder.error && <p className="error-text">{recorder.error}</p>}
    </div>
  );
}
