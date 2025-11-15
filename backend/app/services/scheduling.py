from __future__ import annotations

import json
import os
import random
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


especialidades = [
    "psiquiatria",
    "fisioterapia",
    "nutricionista",
    "cardiologia",
    "dermatologia",
    "ginecologia",
    "oftalmologia",
    "pediatria",
    "endocrinologia",
    "odontologia",
]

acessibilidades = ["libras", "braille", "locomocao", "cognitiva"]
faixas_horarios = ["07-09", "09-11", "11-13", "13-15", "15-17", "17-19", "19-21"]
tipo_consulta = ["online", "presencial"]
faixa_periodo = {
    "07-09": "manha",
    "09-11": "manha",
    "11-13": "manha",
    "13-15": "tarde",
    "15-17": "tarde",
    "17-19": "noite",
    "19-21": "noite",
}
faixas_pico = ["09-11", "13-15", "15-17"]

medicos = [
    {"nome": "Dra. Ana", "esp": {"psiquiatria"}, "online": True, "disp": {"07-09", "09-11", "11-13", "13-15", "15-17"}},
    {"nome": "Dr. Bruno", "esp": {"psiquiatria"}, "online": True, "disp": {"11-13", "13-15", "17-19", "19-21"}},
    {"nome": "Dra. Carla", "esp": {"cardiologia"}, "online": False, "disp": {"09-11", "13-15", "15-17", "17-19"}},
    {"nome": "Dr. Daniel", "esp": {"fisioterapia"}, "online": True, "disp": {"09-11", "11-13", "15-17", "19-21"}},
    {"nome": "Dra. Elisa", "esp": {"nutricionista"}, "online": True, "disp": {"09-11", "11-13", "13-15", "15-17"}},
    {"nome": "Dr. Felipe", "esp": {"cardiologia"}, "online": False, "disp": {"13-15", "15-17", "17-19"}},
    {"nome": "Dra. Gabriela", "esp": {"dermatologia"}, "online": True, "disp": {"09-11", "11-13", "13-15"}},
    {"nome": "Dra. Helena", "esp": {"ginecologia"}, "online": False, "disp": {"09-11", "13-15", "15-17", "17-19"}},
    {"nome": "Dr. Igor", "esp": {"oftalmologia"}, "online": True, "disp": {"11-13", "13-15", "17-19", "19-21"}},
    {"nome": "Dra. Juliana", "esp": {"pediatria"}, "online": True, "disp": {"07-09", "09-11", "11-13", "13-15"}},
    {"nome": "Dr. Kevin", "esp": {"endocrinologia"}, "online": False, "disp": {"13-15", "15-17", "17-19"}},
    {"nome": "Dra. Laura", "esp": {"odontologia"}, "online": True, "disp": {"07-09", "09-11", "11-13", "15-17", "19-21"}},
]

recursos_qtd = {
    "07-09": {"libras": 2, "braille": 1, "locomocao": 1, "cognitiva": 1},
    "09-11": {"libras": 2, "braille": 1, "locomocao": 1, "cognitiva": 1},
    "11-13": {"libras": 1, "braille": 2, "locomocao": 1, "cognitiva": 1},
    "13-15": {"libras": 2, "braille": 1, "locomocao": 2, "cognitiva": 1},
    "15-17": {"libras": 1, "braille": 1, "locomocao": 2, "cognitiva": 1},
    "17-19": {"libras": 1, "braille": 1, "locomocao": 1, "cognitiva": 1},
    "19-21": {"libras": 1, "braille": 1, "locomocao": 1, "cognitiva": 1},
}

capacidade = {"07-09": 5, "09-11": 8, "11-13": 6, "13-15": 7, "15-17": 6, "17-19": 5, "19-21": 5}

PESO_PERIODO = 100
PESO_RECURSO = 100
PESO_ESP = 100
PESO_ONLINE = 40
PESO_PICO = 20
PESO_OVER = 1_000
MAX_ITER = 200
RESTARTS = 10
SEED = 42

DB_PATH = os.getenv("SCHEDULING_DB_PATH", "scheduling.db")


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db() -> None:
    with get_conn() as con:
        cur = con.cursor()
        cur.executescript(
            """
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            esp TEXT NOT NULL,
            periodo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            urg INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS patient_access (
            patient_id INTEGER NOT NULL,
            acc TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            faixa TEXT NOT NULL,
            doctor_name TEXT NOT NULL,
            warnings TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS capacity (
            faixa TEXT PRIMARY KEY,
            capacidade INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS resources (
            faixa TEXT NOT NULL,
            recurso TEXT NOT NULL,
            qtd INTEGER NOT NULL,
            PRIMARY KEY (faixa, recurso)
        );
        CREATE TABLE IF NOT EXISTS triage (
            patient_id INTEGER PRIMARY KEY,
            age INTEGER,
            sex TEXT,
            pain INTEGER,
            temp REAL,
            hr INTEGER,
            rr INTEGER,
            spo2 INTEGER,
            sbp INTEGER,
            bleeding TEXT,
            consciousness TEXT,
            chest_pain INTEGER,
            dyspnea INTEGER,
            dehydration INTEGER,
            comorb INTEGER,
            pregnancy_wks INTEGER,
            onset_hours INTEGER,
            notes TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        );
        """
        )
        con.commit()


def seed_static_if_empty() -> None:
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM capacity")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO capacity (faixa, capacidade) VALUES (?,?)",
                [(f, capacidade[f]) for f in capacidade],
            )
        cur.execute("SELECT COUNT(*) FROM resources")
        if cur.fetchone()[0] == 0:
            rows = []
            for faixa, recursos in recursos_qtd.items():
                for recurso, qtd in recursos.items():
                    rows.append((faixa, recurso, qtd))
            cur.executemany("INSERT INTO resources (faixa, recurso, qtd) VALUES (?,?,?)", rows)
        con.commit()


def add_patient(p: Dict[str, Any], tri: Optional[Dict[str, Any]] = None) -> int:
    with get_conn() as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO patients (data, esp, periodo, tipo, urg) VALUES (?,?,?,?,?)",
            (p["data"], p["esp"], p["periodo"], p["tipo"], int(p["urg"])),
        )
        pid = cur.lastrowid
        if p.get("acc"):
            cur.executemany(
                "INSERT INTO patient_access (patient_id, acc) VALUES (?,?)",
                [(pid, a) for a in p["acc"]],
            )
        if tri:
            cur.execute(
                """
            INSERT INTO triage (patient_id, age, sex, pain, temp, hr, rr, spo2, sbp, bleeding, consciousness,
                                chest_pain, dyspnea, dehydration, comorb, pregnancy_wks, onset_hours, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
                (
                    pid,
                    tri.get("age"),
                    tri.get("sex"),
                    tri.get("pain"),
                    tri.get("temp"),
                    tri.get("hr"),
                    tri.get("rr"),
                    tri.get("spo2"),
                    tri.get("sbp"),
                    tri.get("bleeding"),
                    tri.get("consciousness"),
                    int(tri.get("chest_pain", 0)),
                    int(tri.get("dyspnea", 0)),
                    int(tri.get("dehydration", 0)),
                    tri.get("comorb"),
                    tri.get("pregnancy_wks"),
                    tri.get("onset_hours"),
                    tri.get("notes"),
                ),
            )
        con.commit()
    return pid


def list_bookings(date_str: Optional[str] = None, faixa: Optional[str] = None) -> List[Dict[str, Any]]:
    query = """
        SELECT b.id, b.patient_id, b.data, b.faixa, b.doctor_name, b.warnings, b.created_at,
               p.esp, p.periodo, p.tipo, p.urg,
               COALESCE(GROUP_CONCAT(pa.acc, ','), '') AS acc_csv
          FROM bookings b
          JOIN patients p ON p.id = b.patient_id
          LEFT JOIN patient_access pa ON pa.patient_id = p.id
         WHERE 1=1
    """
    params: List[Any] = []
    if date_str:
        query += " AND b.data = ?"
        params.append(date_str)
    if faixa:
        query += " AND b.faixa = ?"
        params.append(faixa)
    query += " GROUP BY b.id ORDER BY b.created_at DESC"
    with get_conn() as con:
        cur = con.cursor()
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
    bookings = []
    for row in rows:
        acc_list = [a for a in (row[11] or "").split(",") if a]
        bookings.append(
            {
                "booking_id": row[0],
                "patient_id": row[1],
                "date": row[2],
                "slot": row[3],
                "doctor_name": row[4],
                "warnings": json.loads(row[5]) if row[5] else {},
                "created_at": row[6],
                "specialty": row[7],
                "period": row[8],
                "consultation_type": row[9],
                "urgency": row[10],
                "accessibility": acc_list,
            }
        )
    return bookings


def bookings_on(date_str: str, faixa: str) -> List[Dict[str, Any]]:
    return list_bookings(date_str=date_str, faixa=faixa)


def resources_left(date_str: str, faixa: str) -> Dict[str, int]:
    with get_conn() as con:
        cur = con.cursor()
        cur.execute(
            """
        SELECT recurso, qtd FROM resources WHERE faixa = ?
        """,
            (faixa,),
        )
        recursos_base = {row[0]: row[1] for row in cur.fetchall()}
        cur.execute(
            """
        SELECT pa.acc, COUNT(*) as used
          FROM bookings b
          JOIN patient_access pa ON pa.patient_id = b.patient_id
         WHERE b.data = ? AND b.faixa = ?
         GROUP BY pa.acc
        """,
            (date_str, faixa),
        )
        usados = {row[0]: row[1] for row in cur.fetchall()}
    return {k: recursos_base.get(k, 0) - usados.get(k, 0) for k in recursos_base}


def doctor_free_on(doctor_name: str, date_str: str, faixa: str) -> bool:
    with get_conn() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM bookings WHERE doctor_name = ? AND data = ? AND faixa = ?",
            (doctor_name, date_str, faixa),
        )
        used = cur.fetchone()[0]
    return used == 0


def capacity_left_on(date_str: str, faixa: str) -> int:
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("SELECT capacidade FROM capacity WHERE faixa = ?", (faixa,))
        cap = cur.fetchone()
        capacidade_total = cap[0] if cap else capacidade.get(faixa, 0)
        cur.execute("SELECT COUNT(*) FROM bookings WHERE data = ? AND faixa = ?", (date_str, faixa))
        used = cur.fetchone()[0]
    return capacidade_total - used


def available_doctors(esp: str, faixa: str, tipo: str) -> List[Dict[str, Any]]:
    docs = [m for m in medicos if esp in m["esp"] and faixa in m["disp"]]
    if tipo == "online":
        docs = [m for m in docs if m["online"]]
    return docs


def find_next_slot(
    esp: str,
    tipo: str,
    acc: Sequence[str],
    start_date: date,
    prefer_faixa: str,
    days_ahead: int = 7,
) -> Optional[Tuple[str, str, str]]:
    for delta in range(days_ahead + 1):
        dia = (start_date + timedelta(days=delta)).isoformat()
        faixas_try = [prefer_faixa] + [f for f in faixas_horarios if f != prefer_faixa]
        for faixa in faixas_try:
            if capacity_left_on(dia, faixa) <= 0:
                continue
            recursos = resources_left(dia, faixa)
            if any(recursos.get(r, 0) <= 0 for r in acc):
                continue
            docs = available_doctors(esp, faixa, tipo)
            livres = [m for m in docs if doctor_free_on(m["nome"], dia, faixa)]
            if livres:
                return dia, faixa, livres[0]["nome"]
    return None


def calc_triage_urg(tri: Dict[str, Any]) -> int:
    pain = int(tri.get("pain") or 0)
    temp = float(tri.get("temp") or 0.0)
    hr = int(tri.get("hr") or 0)
    rr = int(tri.get("rr") or 0)
    spo2 = int(tri.get("spo2") or 0)
    sbp = int(tri.get("sbp") or 0)
    bleeding = (tri.get("bleeding") or "nenhum").lower()
    avpu = (tri.get("consciousness") or "alerta").lower()
    chest_pain = bool(int(tri.get("chest_pain") or 0))
    dyspnea = bool(int(tri.get("dyspnea") or 0))
    dehydration = bool(int(tri.get("dehydration") or 0))
    comorb = int(tri.get("comorb") or 0)
    preg_wks = int(tri.get("pregnancy_wks") or 0)
    onset_h = int(tri.get("onset_hours") or 0)

    if avpu in ["dor", "inconsciente"]:
        return 5
    if sbp and sbp < 90:
        return 5
    if rr and (rr < 8 or rr > 30):
        return 5
    if hr and (hr < 40 or hr > 130):
        return 5
    if spo2 and spo2 < 90:
        return 5
    if bleeding == "grave":
        return 5
    if chest_pain and (spo2 < 94 or sbp < 100):
        return 5

    score = 0
    if pain >= 8:
        score += 2
    elif pain >= 5:
        score += 1
    if temp >= 39.0:
        score += 2
    elif temp >= 38.0:
        score += 1
    elif 0 < temp < 35.0:
        score += 2
    if hr >= 110:
        score += 2
    elif hr >= 100:
        score += 1
    if rr >= 25:
        score += 2
    elif rr >= 20:
        score += 1
    if spo2 and spo2 <= 94:
        score += 2
    if dyspnea:
        score += 1
    if dehydration:
        score += 1
    if comorb >= 2:
        score += 1
    if preg_wks >= 34:
        score += 1
    if onset_h >= 48:
        score += 1
    if bleeding == "moderado":
        score += 1

    if score >= 6:
        return 4
    if score >= 3:
        return 3
    if score >= 1:
        return 2
    return 1


def patient_access_map(patient_id: int) -> Dict[str, Any]:
    with get_conn() as con:
        cur = con.cursor()
        cur.execute(
            """
        SELECT p.id, p.data, p.esp, p.periodo, p.tipo, p.urg,
               COALESCE(GROUP_CONCAT(pa.acc, ','), '') AS acc_csv
          FROM patients p
          LEFT JOIN patient_access pa ON pa.patient_id = p.id
         WHERE p.id = ?
         GROUP BY p.id
        """,
            (patient_id,),
        )
        row = cur.fetchone()
    if not row:
        return {}
    return {
        "id": row[0],
        "date": row[1],
        "specialty": row[2],
        "period": row[3],
        "consultation_type": row[4],
        "urgency": row[5],
        "accessibility": [a for a in (row[6] or "").split(",") if a],
    }


def book_appointment(
    specialty: str,
    slot_date: str,
    slot: str,
    consultation_type: str,
    urgency: int,
    accessibility: Sequence[str],
    doctor_name: str,
    triage: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    patient_payload = {
        "data": slot_date,
        "esp": specialty,
        "periodo": faixa_periodo.get(slot, "manha"),
        "tipo": consultation_type,
        "urg": urgency,
        "acc": list(accessibility),
    }
    patient_id = add_patient(patient_payload, tri=triage)
    warnings = {}
    if slot in faixas_pico:
        warnings["slot"] = "Faixa de pico; pode haver tempo de espera adicional."
    if accessibility:
        left = resources_left(slot_date, slot)
        faltantes = [acc for acc in accessibility if left.get(acc, 0) <= 0]
        if faltantes:
            warnings["resources"] = f"Recursos limitados para: {', '.join(faltantes)}"

    with get_conn() as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO bookings (patient_id, data, faixa, doctor_name, warnings) VALUES (?,?,?,?,?)",
            (patient_id, slot_date, slot, doctor_name, json.dumps(warnings, ensure_ascii=False)),
        )
        booking_id = cur.lastrowid
        con.commit()

    return {
        "booking_id": booking_id,
        "patient_id": patient_id,
        "date": slot_date,
        "slot": slot,
        "doctor_name": doctor_name,
        "warnings": warnings,
    }


def _parse_date_input(raw: str | None, default: date | None = None) -> date:
    if raw:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
    return default or date.today()


def list_available_slots_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    esp = payload["specialty"]
    tipo = payload.get("consultation_type", "presencial")
    acc = payload.get("accessibility") or []
    prefer_faixa = payload.get("preferred_slot") or faixas_horarios[0]
    start_date = _parse_date_input(payload.get("start_date"), date.today())
    days = int(payload.get("days_ahead") or 7)
    suggestion = find_next_slot(esp, tipo, acc, start_date, prefer_faixa, days)
    if suggestion:
        dia, faixa, medico = suggestion
        return {
            "available": True,
            "date": dia,
            "slot": faixa,
            "doctor_name": medico,
            "notes": "Slot encontrado considerando recursos de acessibilidade.",
        }
    return {
        "available": False,
        "reason": "Nenhum horario com recursos disponiveis nos proximos dias.",
    }


def check_capacity_tool(date_str: str, faixa: str) -> Dict[str, Any]:
    return {"date": date_str, "slot": faixa, "capacity_left": capacity_left_on(date_str, faixa)}


def doctor_status_tool(doctor_name: str, date_str: str, faixa: str) -> Dict[str, Any]:
    return {"doctor_name": doctor_name, "date": date_str, "slot": faixa, "available": doctor_free_on(doctor_name, date_str, faixa)}


def resources_status_tool(date_str: str, faixa: str) -> Dict[str, Any]:
    return {"date": date_str, "slot": faixa, "resources": resources_left(date_str, faixa)}


def triage_score_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    score = calc_triage_urg(payload)
    return {"triage_level": score}


def list_bookings_tool(date_str: Optional[str] = None, faixa: Optional[str] = None) -> Dict[str, Any]:
    return {"bookings": list_bookings(date_str=date_str, faixa=faixa)}


def patient_requirements_tool(patient_id: int) -> Dict[str, Any]:
    return patient_access_map(patient_id)


def suggest_alternative_slot_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    prefer_faixa = payload.get("preferred_slot") or faixas_horarios[0]
    result = list_available_slots_tool(
        {
            "specialty": payload["specialty"],
            "consultation_type": payload.get("consultation_type", "presencial"),
            "accessibility": payload.get("accessibility"),
            "preferred_slot": prefer_faixa,
            "start_date": payload.get("start_date"),
            "days_ahead": payload.get("days_ahead", 14),
        }
    )
    if not result.get("available"):
        return {
            "available": False,
            "reason": result.get("reason"),
        }
    if result["slot"] == prefer_faixa:
        result["strategy"] = "Preferencia mantida, houve vaga com recursos compativeis."
    else:
        result["strategy"] = f"Alocado em {result['slot']} por disponibilidade de recursos."
    return result


def plan_appointment_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    specialty = payload["specialty"]
    consultation_type = payload.get("consultation_type", "presencial")
    accessibility = payload.get("accessibility") or []
    preferred_slot = payload.get("preferred_slot")
    preferred_date = payload.get("preferred_date")
    start_date = _parse_date_input(preferred_date, date.today())
    days_ahead = int(payload.get("days_ahead", 7) or 7)
    plan_payload = {
        "specialty": specialty,
        "consultation_type": consultation_type,
        "accessibility": accessibility,
        "preferred_slot": preferred_slot,
        "start_date": start_date.isoformat(),
        "days_ahead": days_ahead,
    }
    evaluation = list_available_slots_tool(plan_payload)
    alternative: Dict[str, Any] | None = None
    if not evaluation.get("available"):
        alt_payload = plan_payload.copy()
        alt_payload["days_ahead"] = max(days_ahead, 14)
        alternative = suggest_alternative_slot_tool(alt_payload)
    return {
        "request": {
            "specialty": specialty,
            "consultation_type": consultation_type,
            "accessibility": accessibility,
            "preferred_slot": preferred_slot,
            "preferred_date": start_date.isoformat(),
        },
        "result": evaluation,
        "alternative": alternative,
    }


def availability_snapshot(days_ahead: int = 7) -> list[dict[str, Any]]:
    days_ahead = max(1, min(days_ahead, 30))
    today = date.today()
    summary: list[dict[str, Any]] = []
    for offset in range(days_ahead):
        dia = (today + timedelta(days=offset)).isoformat()
        for faixa in faixas_horarios:
            summary.append(
                {
                    "date": dia,
                    "slot": faixa,
                    "capacity_left": capacity_left_on(dia, faixa),
                    "resources": resources_left(dia, faixa),
                }
            )
    return summary


def register():
    init_db()
    seed_static_if_empty()


register()
