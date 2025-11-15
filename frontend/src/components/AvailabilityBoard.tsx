import { useMemo } from "react";
import type { AvailabilitySlot } from "../types";

type Props = {
  slots: AvailabilitySlot[];
  loading?: boolean;
  onRefresh: () => void;
};

const SLOT_LABELS: Record<string, string> = {
  "07-09": "07h-09h",
  "09-11": "09h-11h",
  "11-13": "11h-13h",
  "13-15": "13h-15h",
  "15-17": "15h-17h",
  "17-19": "17h-19h",
  "19-21": "19h-21h",
};

type CalendarDay = {
  date: string;
  dateObj: Date;
  items: AvailabilitySlot[];
};

export function AvailabilityBoard({ slots, loading = false, onRefresh }: Props) {
  const calendarDays = useMemo<CalendarDay[]>(() => {
    const map = new Map<string, AvailabilitySlot[]>();
    slots.forEach((slot) => {
      if (!map.has(slot.date)) {
        map.set(slot.date, []);
      }
      map.get(slot.date)?.push(slot);
    });

    return Array.from(map.entries())
      .map(([date, items]) => ({
        date,
        dateObj: new Date(`${date}T00:00:00`),
        items: items.sort((a, b) => a.slot.localeCompare(b.slot)),
      }))
      .sort((a, b) => a.dateObj.getTime() - b.dateObj.getTime());
  }, [slots]);

  return (
    <div className="availability-board">
      <header>
        <div>
          <p className="eyebrow">Calendário de disponibilidade</p>
          <h4>Escolha dias e faixas com recursos inclusivos garantidos.</h4>
        </div>
        <button type="button" className="pill-button secondary" onClick={onRefresh} disabled={loading}>
          {loading ? "Atualizando..." : "Atualizar"}
        </button>
      </header>

      {loading ? (
        <p className="loading-state">Carregando disponibilidade...</p>
      ) : calendarDays.length === 0 ? (
        <p className="empty-state">Sem dados de disponibilidade.</p>
      ) : (
        <div className="calendar-scroll">
          <div className="calendar-grid">
            {calendarDays.map((day) => {
              const weekday = day.dateObj.toLocaleDateString("pt-BR", { weekday: "short" });
              const dayNumber = day.dateObj.getDate();
              const monthLabel = day.dateObj.toLocaleDateString("pt-BR", { month: "short" });
              return (
                <article key={day.date} className="calendar-column">
                  <div className="calendar-column-head">
                    <span className="weekday">{weekday}</span>
                    <strong>{dayNumber}</strong>
                    <span className="month">{monthLabel}</span>
                  </div>
                  <ul className="calendar-slots">
                    {day.items.map((slot) => {
                      const capacity = slot.capacity_left;
                      const status = capacity > 4 ? "ok" : capacity > 0 ? "warn" : "full";
                      const resources = Object.entries(slot.resources || {});
                      return (
                        <li key={`${day.date}-${slot.slot}`} className={`calendar-slot ${status}`}>
                          <div className="slot-time">
                            <span>{SLOT_LABELS[slot.slot] ?? slot.slot}</span>
                            <strong>{capacity}</strong>
                          </div>
                          {resources.length > 0 ? (
                            <ul className="slot-resources">
                              {resources.map(([key, value]) => (
                                <li key={key}>
                                  <span>{key}</span>
                                  <strong>{value}</strong>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="micro-copy">Sem recursos extras cadastrados.</p>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </article>
              );
            })}
          </div>
        </div>
      )}
      <footer className="calendar-legend">
        <span>Legenda:</span>
        <div>
          <span className="legend-pill ok">5+ vagas</span>
          <span className="legend-pill warn">1-4 vagas</span>
          <span className="legend-pill full">Sem vagas</span>
        </div>
      </footer>
    </div>
  );
}
