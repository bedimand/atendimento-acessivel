import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchAvailability, fetchBookings, fetchHistory, streamMessage, transcribeAudioFile } from "./api";
import { AudioRecorderButton, type RecordedAudio } from "./components/AudioRecorderButton";
import { AvailabilityBoard } from "./components/AvailabilityBoard";
import { BookingsBoard } from "./components/BookingsBoard";
import { MessageInput } from "./components/MessageInput";
import { MessageList } from "./components/MessageList";
import { ProfileSetup } from "./components/ProfileSetup";
import { VLibrasWidget } from "./components/VLibrasWidget";
import type { AvailabilitySlot, Booking, Message, UserProfile } from "./types";
import "./App.css";

function App() {
  const [renderedMessages, setRenderedMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastAudioUrl, setLastAudioUrl] = useState<string | null>(null);
  const [recordedAudio, setRecordedAudio] = useState<RecordedAudio | null>(null);
  const [transcribing, setTranscribing] = useState(false);
  const [historyVersion, setHistoryVersion] = useState(0);
  const [availabilityVisible, setAvailabilityVisible] = useState(false);
  const [availabilitySlots, setAvailabilitySlots] = useState<AvailabilitySlot[]>([]);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [bookingsVisible, setBookingsVisible] = useState(false);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [bookingsLoading, setBookingsLoading] = useState(false);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [showProfileModal, setShowProfileModal] = useState(false);

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
      .catch(() => setError("Nao foi possivel carregar o historico."))
      .finally(() => setLoading(false));
  }, [historyVersion]);

  useEffect(() => {
    const stored = window.localStorage.getItem("aurora-profile");
    if (stored) {
      try {
        setProfile(JSON.parse(stored) as UserProfile);
      } catch (err) {
        console.error("Erro ao carregar perfil", err);
        setShowProfileModal(true);
      }
    } else {
      setShowProfileModal(true);
    }
  }, []);

  const handleProfileComplete = useCallback((data: UserProfile) => {
    setProfile(data);
    window.localStorage.setItem("aurora-profile", JSON.stringify(data));
    setShowProfileModal(false);
    setHistoryVersion((value) => value + 1);
    setError(null);
  }, []);

  const ensureProfile = useCallback(() => {
    if (profile) {
      return true;
    }
    setError("Finalize seu perfil inclusivo antes de conversar com Aurora.");
    setShowProfileModal(true);
    return false;
  }, [profile]);

  const loadAvailability = useCallback(async () => {
    setAvailabilityLoading(true);
    try {
      const snapshot = await fetchAvailability(10);
      setAvailabilitySlots(snapshot);
    } catch (err) {
      console.error(err);
      setError("Nao foi possivel carregar a disponibilidade.");
    } finally {
      setAvailabilityLoading(false);
    }
  }, []);

  const loadBookings = useCallback(async () => {
    setBookingsLoading(true);
    try {
      const snapshot = await fetchBookings();
      setBookings(snapshot);
    } catch (err) {
      console.error(err);
      setError("Nao foi possivel carregar os agendamentos ativos.");
    } finally {
      setBookingsLoading(false);
    }
  }, []);

  const handleSubmit = useCallback(
    async (content: string) => {
      const sanitized = content.trim();
      if (!sanitized || !ensureProfile()) return;

      const userMessage = createLocalMessage("user", sanitized);
      setRenderedMessages((prev) => [...prev, userMessage]);

      const botMessage = createLocalMessage("bot", "");
      setRenderedMessages((prev) => [...prev, botMessage]);

      setSending(true);
      setError(null);
      try {
        await streamMessage(
          sanitized,
          (chunk) => {
            if (!chunk) return;
            setRenderedMessages((prev) =>
              prev.map((message) =>
                message.id === botMessage.id ? { ...message, content: message.content + chunk } : message,
              ),
            );
          },
          profile,
        );
        setHistoryVersion((value) => value + 1);
      } catch {
        setError("Falha ao enviar mensagem.");
        setRenderedMessages((prev) => prev.filter((message) => message.id !== botMessage.id));
      } finally {
        setSending(false);
      }
    },
    [createLocalMessage, ensureProfile, profile],
  );

  const handleAudioReady = useCallback((audio: RecordedAudio | null) => {
    setRecordedAudio(audio);
    setLastAudioUrl(audio?.url ?? null);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const runTranscription = async () => {
      if (!recordedAudio) {
        return;
      }
      setTranscribing(true);
      setError(null);
      try {
        const file = new File([recordedAudio.blob], `audio-${Date.now()}.webm`, {
          type: recordedAudio.mimeType || "audio/webm",
        });
        const transcript = await transcribeAudioFile(file);
        if (!cancelled) {
          setRecordedAudio(null);
          setLastAudioUrl(null);
          if (transcript.trim()) {
            await handleSubmit(transcript);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError("Falha ao transcrever audio.");
        }
      } finally {
        if (!cancelled) {
          setTranscribing(false);
        }
      }
    };

    void runTranscription();
    return () => {
      cancelled = true;
    };
  }, [handleSubmit, recordedAudio]);

  const nextSlot = useMemo(() => {
    if (!availabilitySlots.length) return null;
    return availabilitySlots.find((slot) => slot.capacity_left > 0) ?? availabilitySlots[0];
  }, [availabilitySlots]);

  const toggleAvailabilityPanel = () => {
    const next = !availabilityVisible;
    setAvailabilityVisible(next);
    if (next) {
      setBookingsVisible(false);
      void loadAvailability();
    }
  };

  const toggleBookingsPanel = () => {
    const next = !bookingsVisible;
    setBookingsVisible(next);
    if (next) {
      setAvailabilityVisible(false);
      void loadBookings();
    }
  };

  return (
    <div className="app-shell">
      <VLibrasWidget />
      {(!profile || showProfileModal) && (
        <ProfileSetup
          initialProfile={profile}
          onComplete={handleProfileComplete}
          onCancel={profile ? () => setShowProfileModal(false) : undefined}
        />
      )}
      <div className="app-grid">
        <aside className="identity-panel">
          <div className="identity-card">
            <div className="avatar pulse">CI</div>
            <div className="identity-copy">
              <p className="eyebrow">Aurora</p>
              <h1>Chat inclusivo em tempo real</h1>
              <p>Texto, audio, TTS e VLibras em uma experiencia ultrarrapida.</p>
            </div>
          </div>
          <div className="panel-section">
            <div className="section-head">
              <span>Status do perfil</span>
              <button type="button" className="text-link" onClick={() => setShowProfileModal(true)}>
                {profile ? "Revisar" : "Criar"}
              </button>
            </div>
            {profile ? (
              <div className="profile-summary">
                <strong>{profile.fullName}</strong>
                <p>{profile.accessibilityNeeds?.[0] || "Preferencias inclusivas configuradas"}</p>
                <span className="micro-copy">Atualizado automaticamente apos cada ajuste.</span>
              </div>
            ) : (
              <div className="profile-summary empty">
                <p>Configure suas necessidades de acessibilidade para personalizar respostas.</p>
                <button type="button" className="pill-button primary" onClick={() => setShowProfileModal(true)}>
                  Criar perfil inclusivo
                </button>
              </div>
            )}
          </div>
          <div className="panel-section compact">
            <div className="section-head">
              <span>Proxima disponibilidade</span>
              <button type="button" className="icon-button ghost" aria-label="Abrir agenda" onClick={toggleAvailabilityPanel}>
                ⇲
              </button>
            </div>
            {nextSlot ? (
              <div className="slot-preview">
                <strong>{nextSlot.slot}</strong>
                <p>
                  {new Date(nextSlot.date).toLocaleDateString([], { day: "2-digit", month: "short" })} ·{" "}
                  {nextSlot.capacity_left} vagas
                </p>
              </div>
            ) : (
              <p className="micro-copy">Nenhuma vaga carregada ainda.</p>
            )}
            <button type="button" className="pill-button secondary full" onClick={toggleAvailabilityPanel}>
              {availabilityVisible ? "Ocultar agenda" : "Ver agenda completa"}
            </button>
          </div>
        </aside>
        <section className="chat-panel">
          <header className="chat-top-bar">
            <div>
              <p className="eyebrow">Conversas</p>
              <h2>Fale com Aurora</h2>
            </div>
            <div className="top-actions">
              <button type="button" className="chip-button" onClick={toggleBookingsPanel}>
                {bookingsVisible ? "Agendamentos abertos" : "Agendamentos"}
              </button>
              <button type="button" className="chip-button" onClick={toggleAvailabilityPanel}>
                {availabilityVisible ? "Agenda aberta" : "Agenda"}
              </button>
              <button type="button" className="chip-button" onClick={() => setShowProfileModal(true)}>
                {profile ? "Perfil" : "Comecar"}
              </button>
            </div>
          </header>
          <div className="chat-scroll-area">
            {loading ? (
              <div className="message-skeletons">
                <div />
                <div />
                <div />
              </div>
            ) : (
              <MessageList messages={renderedMessages} />
            )}
          </div>
          {error && (
            <div className="inline-alert" role="alert">
              {error}
            </div>
          )}
          <div className="composer">
            {profile ? (
              <AudioRecorderButton onAudioReady={handleAudioReady} compact />
            ) : (
              <p className="micro-copy muted">Conclua o perfil para liberar a gravacao e ajustes inclusivos.</p>
            )}
            <MessageInput onSubmit={handleSubmit} disabled={sending || !profile} lastAudioUrl={lastAudioUrl} transcribing={transcribing} />
          </div>
        </section>
      </div>
      {availabilityVisible && (
        <div className="overlay-panel" role="dialog" aria-modal="true">
          <div className="overlay-card">
            <header>
              <div>
                <p className="eyebrow">Calendario inclusivo</p>
                <h3>Visualize as vagas por dia e horario</h3>
                <p className="micro-copy">Acompanhe capacidade restante com destaque para recursos acessiveis.</p>
              </div>
              <button type="button" className="icon-button ghost" aria-label="Fechar agenda" onClick={toggleAvailabilityPanel}>
                ×
              </button>
            </header>
            <AvailabilityBoard slots={availabilitySlots} loading={availabilityLoading} onRefresh={loadAvailability} />
          </div>
        </div>
      )}
      {bookingsVisible && (
        <div className="overlay-panel" role="dialog" aria-modal="true">
          <div className="overlay-card">
            <header>
              <div>
                <p className="eyebrow">Linha do tempo de consultas</p>
                <h3>Confira seus agendamentos ativos</h3>
                <p className="micro-copy">Cada cartao mostra horario, profissional e recursos inclusivos confirmados.</p>
              </div>
              <button type="button" className="icon-button ghost" aria-label="Fechar agendamentos" onClick={toggleBookingsPanel}>
                ×
              </button>
            </header>
            <BookingsBoard bookings={bookings} loading={bookingsLoading} onRefresh={loadBookings} />
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
