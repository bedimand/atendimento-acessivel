import { useMemo } from "react";
import type { Booking } from "../types";

type Props = {
  bookings: Booking[];
  loading?: boolean;
  onRefresh: () => void;
};

type BookingGroup = {
  date: string;
  label: string;
  items: Booking[];
};

export function BookingsBoard({ bookings, loading = false, onRefresh }: Props) {
  const grouped = useMemo<BookingGroup[]>(() => {
    const map = new Map<string, Booking[]>();
    bookings.forEach((booking) => {
      if (!map.has(booking.date)) {
        map.set(booking.date, []);
      }
      map.get(booking.date)?.push(booking);
    });
    return Array.from(map.entries())
      .map(([date, items]) => ({
        date,
        label: new Date(`${date}T00:00:00`).toLocaleDateString("pt-BR", {
          weekday: "long",
          day: "2-digit",
          month: "short",
        }),
        items: items.sort((a, b) => a.slot.localeCompare(b.slot)),
      }))
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }, [bookings]);

  return (
    <div className="bookings-board">
      <header>
        <div>
          <p className="eyebrow">Agendamentos ativos</p>
          <h4>Veja consultas confirmadas com contexto inclusivo.</h4>
        </div>
        <button type="button" className="pill-button secondary" onClick={onRefresh} disabled={loading}>
          {loading ? "Atualizando..." : "Atualizar"}
        </button>
      </header>

      {loading ? (
        <p className="loading-state">Carregando agendamentos...</p>
      ) : grouped.length === 0 ? (
        <p className="empty-state">Nenhum agendamento ativo no momento.</p>
      ) : (
        grouped.map((group) => (
          <section key={group.date} className="booking-section">
            <div className="booking-section-head">
              <strong>{group.label}</strong>
              <span>{group.items.length} atendimento(s)</span>
            </div>
            <div className="bookings-grid">
              {group.items.map((booking) => (
                <article key={booking.booking_id} className="booking-card">
                  <div className="booking-slot">
                    <strong>{booking.slot}</strong>
                    <span>{booking.consultation_type}</span>
                  </div>
                  <div className="booking-meta">
                    <div>
                      <p className="booking-doctor">{booking.doctor_name}</p>
                      <span className="booking-specialty">{booking.specialty}</span>
                    </div>
                    <span className={`urgency-pill urgency-${booking.urgency}`}>Urgência {booking.urgency}</span>
                  </div>
                  <ul className="booking-access">
                    {booking.accessibility.length > 0 ? (
                      booking.accessibility.map((item) => (
                        <li key={item} className="access-chip">
                          {item}
                        </li>
                      ))
                    ) : (
                      <li className="access-chip muted">Sem recursos extras</li>
                    )}
                  </ul>
                  {booking.warnings && Object.keys(booking.warnings).length > 0 && (
                    <div className="booking-warning">
                      <strong>Atenção</strong>
                      <pre>{JSON.stringify(booking.warnings, null, 2)}</pre>
                    </div>
                  )}
                </article>
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  );
}
