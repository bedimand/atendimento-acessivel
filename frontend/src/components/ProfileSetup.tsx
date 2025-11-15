import { useMemo, useState } from "react";
import type { UserProfile } from "../types";

const DISABILITY_OPTIONS = ["Auditiva", "Visual", "Motora", "Intelectual", "Múltipla"];
const ACCESSIBILITY_OPTIONS = [
  { value: "libras", label: "Intérprete Libras" },
  { value: "braille", label: "Materiais em Braille" },
  { value: "locomocao", label: "Apoio à locomoção" },
  { value: "cognitiva", label: "Apoio cognitivo" },
];
const PRONOUN_OPTIONS = ["Ela/dela", "Ele/dele", "Elu/delu", "Outro"];
const CONTACT_OPTIONS = ["Telefone", "WhatsApp", "E-mail", "SMS"];

type Props = {
  initialProfile?: UserProfile | null;
  onComplete: (profile: UserProfile) => void;
  onCancel?: () => void;
};

export function ProfileSetup({ initialProfile, onComplete, onCancel }: Props) {
  const [fullName, setFullName] = useState(initialProfile?.fullName ?? "");
  const [patientId, setPatientId] = useState(initialProfile?.patientId ?? "");
  const [pronouns, setPronouns] = useState(initialProfile?.pronouns ?? "");
  const [disabilities, setDisabilities] = useState<string[]>(initialProfile?.disabilities ?? []);
  const [accessibilityNeeds, setAccessibilityNeeds] = useState<string[]>(initialProfile?.accessibilityNeeds ?? []);
  const [contactPreference, setContactPreference] = useState(initialProfile?.contactPreference ?? "");
  const [mobilityNotes, setMobilityNotes] = useState(initialProfile?.mobilityNotes ?? "");
  const [notes, setNotes] = useState(initialProfile?.notes ?? "");
  const [error, setError] = useState<string | null>(null);

  const isEditing = useMemo(() => Boolean(initialProfile), [initialProfile]);

  const toggleValue = (list: string[], value: string) => {
    if (list.includes(value)) {
      return list.filter((item) => item !== value);
    }
    return [...list, value];
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = fullName.trim();
    if (!trimmed) {
      setError("Informe seu nome completo para personalizar o atendimento.");
      return;
    }
    const profile: UserProfile = {
      fullName: trimmed,
      patientId: patientId.trim() || undefined,
      pronouns: pronouns || undefined,
      disabilities,
      accessibilityNeeds,
      contactPreference: contactPreference || undefined,
      mobilityNotes: mobilityNotes.trim() || undefined,
      notes: notes.trim() || undefined,
    };
    setError(null);
    onComplete(profile);
  };

  return (
    <div className="profile-setup-overlay" role="dialog" aria-modal="true">
      <div className="profile-setup-panel">
        <section className="profile-setup-side">
          <p className="eyebrow">Perfil inclusivo</p>
          <h2>{isEditing ? "Atualize suas preferências" : "Vamos montar seu perfil"}</h2>
          <p>Personalizamos cada resposta com base nas suas necessidades de acessibilidade e no canal preferido.</p>
          <ul className="profile-steps">
            <li>
              <strong>1.</strong> Identifique-se
            </li>
            <li>
              <strong>2.</strong> Informe recursos prioritários
            </li>
            <li>
              <strong>3.</strong> Compartilhe observações
            </li>
          </ul>
          {isEditing && onCancel && (
            <button type="button" className="pill-button secondary" onClick={onCancel}>
              Fechar sem alterar
            </button>
          )}
        </section>

        <form className="profile-form" onSubmit={handleSubmit}>
          <div className="field-grid">
            <label>
              Nome completo*
              <input value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Ex.: Ana Clara" />
            </label>
            <label>
              Identificador do paciente
              <input value={patientId} onChange={(event) => setPatientId(event.target.value)} placeholder="SUS, prontuário..." />
            </label>
          </div>

          <div className="field-grid">
            <label>
              Pronomes preferidos
              <select value={pronouns} onChange={(event) => setPronouns(event.target.value)}>
                <option value="">Selecione</option>
                {PRONOUN_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Preferência de contato
              <select value={contactPreference} onChange={(event) => setContactPreference(event.target.value)}>
                <option value="">Selecione</option>
                {CONTACT_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <fieldset>
            <legend>Quais deficiências deseja informar?</legend>
            <div className="chip-grid">
              {DISABILITY_OPTIONS.map((option) => (
                <label key={option} className={disabilities.includes(option) ? "chip active" : "chip"}>
                  <input
                    type="checkbox"
                    checked={disabilities.includes(option)}
                    onChange={() => setDisabilities((prev) => toggleValue(prev, option))}
                  />
                  {option}
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset>
            <legend>Escolha os recursos de acessibilidade necessários</legend>
            <div className="chip-grid">
              {ACCESSIBILITY_OPTIONS.map((option) => (
                <label key={option.value} className={accessibilityNeeds.includes(option.value) ? "chip active" : "chip"}>
                  <input
                    type="checkbox"
                    checked={accessibilityNeeds.includes(option.value)}
                    onChange={() => setAccessibilityNeeds((prev) => toggleValue(prev, option.value))}
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </fieldset>

          <div className="field-grid">
            <label>
              Observações de mobilidade ou apoio
              <textarea value={mobilityNotes} onChange={(event) => setMobilityNotes(event.target.value)} rows={3} />
            </label>
            <label>
              Mais informações que deseja compartilhar
              <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} />
            </label>
          </div>

          {error && <p className="error-text">{error}</p>}

          <div className="profile-form-actions">
            <button type="submit" className="pill-button primary">
              {isEditing ? "Salvar alterações" : "Começar atendimento"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
