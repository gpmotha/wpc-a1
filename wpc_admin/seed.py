import sys
import datetime as _dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

XLSX_PATH = Path(r"C:\Users\gynag\Downloads\WPC_Kivitelezok_v1.xlsx")
SHEET = "Munkák"

from models import Project, ProjectCost, ProjectStatus, JobType, Distributor, Crew, Priority

STATUS_MAP = {
    "Kérdőjeles":  ProjectStatus.felmerendo,
    "Ajánlatban":  ProjectStatus.lebeszélve,
    "Betervezve":  ProjectStatus.betervezve,
    "Folyamatban": ProjectStatus.folyamatban,
    "Kész":        ProjectStatus.kesz,
}

DIST_MAP = {
    "Royal":        Distributor.royal,
    "Royal Buda":   Distributor.royal_buda,
    "Royal Óbuda":  Distributor.royal_obuda,
    "Woopla":       Distributor.woopla,
    "Guru":         Distributor.guru,
    "Global":       Distributor.global_,
    "Exotic":       Distributor.exotic,
    "Exoticwood":   Distributor.exotic,
    "Márka-Mix":    Distributor.marka_mix,
    "M-Trend":      Distributor.egyeb,
    "Saját":        Distributor.sajat,
    "Saját/Exotic": Distributor.sajat,
}

CREW_MAP = {
    "Laci":  Crew.laci,
    "Jenő":  Crew.jeno,
    "Csaba": Crew.csaba,
    "Dani":  Crew.dani,
    "Alex":  Crew.alex,
}


def _str_or_none(v) -> str | None:
    if v is None or v == 0 or v == 0.0:
        return None
    s = str(v).strip()
    return s if s else None


def _bool_flag(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str) and v.strip().lower() == "nem":
        return False
    return bool(v)


def _date_or_none(v):
    if v is None:
        return None
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, _dt.date):
        return v
    return None


def _work_days(v) -> int | None:
    if v is None:
        return None
    try:
        n = int(float(v))
        return n if n >= 1 else None
    except (TypeError, ValueError):
        return None


def import_row(row: tuple, row_idx: int) -> dict | None:
    client_name = _str_or_none(row[2])
    if not client_name:
        return None

    # Status
    raw_status = row[6]
    if raw_status not in STATUS_MAP:
        if raw_status is not None:
            print(f"  [row {row_idx}] Unknown status '{raw_status}' → felmérendő")
        status = ProjectStatus.felmerendo
    else:
        status = STATUS_MAP[raw_status]

    # Job type
    raw_job = row[7]
    job_type = JobType.terasz  # default
    if raw_job is not None:
        raw_job_s = str(raw_job).strip().lower()
        for jt in JobType:
            if jt.value.lower() == raw_job_s or jt.name.lower() == raw_job_s:
                job_type = jt
                break
        else:
            if raw_job_s:
                print(f"  [row {row_idx}] Unknown job_type '{raw_job}' → Terasz")

    # Crew
    raw_crew = row[8]
    if raw_crew not in CREW_MAP:
        if raw_crew is not None:
            print(f"  [row {row_idx}] Unknown crew '{raw_crew}' → Nincs hozzárendelve")
        crew = Crew.nincs
    else:
        crew = CREW_MAP[raw_crew]

    crew_confirmed = row[9]
    crew_confirmed = isinstance(crew_confirmed, str) and crew_confirmed.strip().lower() == "igen"

    # Distributor
    raw_dist = row[10]
    if raw_dist not in DIST_MAP:
        if raw_dist is not None:
            print(f"  [row {row_idx}] Unknown distributor '{raw_dist}' → Egyéb")
        distributor = Distributor.egyeb
    else:
        distributor = DIST_MAP[raw_dist]

    # Notes
    raw_notes = row[25]
    notes = None
    if raw_notes is not None:
        s = str(raw_notes).strip()
        notes = s if s else None

    project = {
        "client_name":       client_name,
        "address":           _str_or_none(row[4]),
        "phone":             _str_or_none(row[3]),
        "status":            status,
        "job_type":          job_type,
        "distributor":       distributor,
        "crew":              crew,
        "crew_confirmed":    crew_confirmed,
        "priority":          Priority.normal,
        "planned_start_date": _date_or_none(row[16]),
        "planned_work_days": _work_days(row[17]),
        "actual_start_date": _date_or_none(row[19]),
        "actual_end_date":   _date_or_none(row[20]),
        "welding_required":  _bool_flag(row[22]),
        "covered_area":      _bool_flag(row[23]),
        "vat_invoice":       _bool_flag(row[14]),
        "notes":             notes,
    }

    def _int_fee(v) -> int:
        if v is None:
            return 0
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return 0

    cost = {
        "labor_fee":              _int_fee(row[11]),
        "travel_fee":             _int_fee(row[12]),
        "materials_fee":          _int_fee(row[13]),
        "distributor_commission": 0,
    }

    return {"project": project, "cost": cost}


def main():
    from sqlmodel import Session, select
    from database import create_tables, engine
    create_tables()

    import openpyxl
    wb = openpyxl.load_workbook(XLSX_PATH, read_only=True, data_only=True)
    ws = wb[SHEET]
    rows = list(ws.iter_rows(values_only=True))
    data_rows = rows[1:]

    imported = skipped_dup = skipped_empty = 0

    with Session(engine) as session:
        existing = {
            (p.client_name, p.address)
            for p in session.exec(select(Project)).all()
        }
        for idx, row in enumerate(data_rows, start=2):
            parsed = import_row(row, idx)
            if parsed is None:
                skipped_empty += 1
                continue
            key = (parsed["project"]["client_name"], parsed["project"].get("address"))
            if key in existing:
                skipped_dup += 1
                continue
            p = Project(**parsed["project"])
            session.add(p)
            session.flush()
            session.add(ProjectCost(project_id=p.id, **parsed["cost"]))
            existing.add(key)
            imported += 1
        session.commit()

    print(f"Done. Imported: {imported}, duplicates skipped: {skipped_dup}, empty skipped: {skipped_empty}")


if __name__ == "__main__":
    main()
