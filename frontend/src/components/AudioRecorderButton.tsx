import { useEffect, useMemo } from "react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";

export type RecordedAudio = {
  url: string;
  blob: Blob;
  mimeType: string;
};

type Props = {
  onAudioReady?: (audio: RecordedAudio | null) => void;
  compact?: boolean;
};

export function AudioRecorderButton({ onAudioReady, compact = false }: Props) {
  const recorder = useAudioRecorder();

  useEffect(() => {
    if (recorder.audioUrl && recorder.audioBlob) {
      onAudioReady?.({
        url: recorder.audioUrl,
        blob: recorder.audioBlob,
        mimeType: recorder.audioBlob.type || "audio/webm",
      });
    } else if (!recorder.audioBlob) {
      onAudioReady?.(null);
    }
  }, [recorder.audioBlob, recorder.audioUrl, onAudioReady]);

  const statusLabel = useMemo(() => {
    switch (recorder.status) {
      case "recording":
        return "Gravando...";
      case "unsupported":
        return "Navegador sem suporte";
      case "error":
        return "Erro no microfone";
      default:
        return recorder.audioUrl ? "Áudio capturado" : "Clique para gravar";
    }
  }, [recorder.audioUrl, recorder.status]);

  return (
    <div className={`audio-recorder ${compact ? "compact" : ""}`}>
      <button
        type="button"
        className={`icon-button mic ${recorder.status === "recording" ? "recording" : ""}`}
        onClick={recorder.status === "recording" ? recorder.stopRecording : recorder.startRecording}
        aria-pressed={recorder.status === "recording"}
        aria-label={recorder.status === "recording" ? "Parar gravação" : "Iniciar gravação"}
      >
        {recorder.status === "recording" ? "■" : "⏺"}
      </button>
      {!compact && (
        <>
          <div className="audio-preview">
            {recorder.audioUrl ? (
              <>
                <audio controls src={recorder.audioUrl} />
                <button type="button" className="pill-button secondary" onClick={recorder.reset}>
                  Descartar
                </button>
              </>
            ) : (
              <span className="micro-copy">{statusLabel}</span>
            )}
          </div>
        </>
      )}
      {compact && <span className="micro-copy">{statusLabel}</span>}
      {recorder.error && <p className="error-text">{recorder.error}</p>}
    </div>
  );
}
