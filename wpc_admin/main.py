from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from database import create_tables, engine, get_session
from models import (
    Crew, Distributor, InvoiceType, JobType, Priority,
    Project, ProjectCost, ProjectLogistics, ProjectStatus,
)


def seed_projects(session: Session) -> None:
    if session.exec(select(Project)).first():
        return

    today = date.today()
    seeds = [
        {
            "project": dict(
                client_name="Kovács Béla",
                address="Budapest, II. ker., Rózsa u. 12.",
                phone="+36 20 123 4567",
                status=ProjectStatus.folyamatban,
                job_type=JobType.terasz,
                distributor=Distributor.royal,
                crew=Crew.laci,
                crew_confirmed=True,
                priority=Priority.normal,
                planned_start_date=today - timedelta(days=5),
                actual_start_date=today - timedelta(days=5),
                planned_work_days=8,
                area_m2=28.5,
                color="Antracit",
            ),
            "cost": dict(labor_fee=480000, travel_fee=25000, distributor_commission=120000, materials_fee=85000),
            "logistics": dict(key_code="A-23", parking="Udvarban szabad", materials_to_bring="Profilok, rögzítők"),
        },
        {
            "project": dict(
                client_name="Szabó Annamária",
                address="Budaörs, Kossuth u. 45.",
                phone="+36 30 987 6543",
                status=ProjectStatus.betervezve,
                job_type=JobType.kerites,
                distributor=Distributor.royal_buda,
                crew=Crew.jeno,
                crew_confirmed=False,
                priority=Priority.normal,
                planned_start_date=today + timedelta(days=12),
                planned_work_days=4,
                area_m2=42.0,
                color="Fehér",
            ),
            "cost": dict(labor_fee=320000, travel_fee=18000, distributor_commission=95000, materials_fee=210000),
        },
        {
            "project": dict(
                client_name="Horváth Gábor",
                address="Érd, Pest u. 8.",
                phone="+36 70 555 1234",
                status=ProjectStatus.felmerendo,
                job_type=JobType.korlat,
                distributor=Distributor.woopla,
                crew=Crew.nincs,
                priority=Priority.surges,
                survey_date=today + timedelta(days=3),
                area_m2=15.0,
            ),
            "cost": dict(labor_fee=0, travel_fee=0, distributor_commission=0, materials_fee=0),
        },
        {
            "project": dict(
                client_name="Tóth Eszter",
                address="Budapest, XII. ker., Alkotás u. 77.",
                phone="+36 20 444 9876",
                status=ProjectStatus.kesz,
                job_type=JobType.lepcso,
                distributor=Distributor.guru,
                crew=Crew.csaba,
                crew_confirmed=True,
                priority=Priority.normal,
                planned_start_date=today - timedelta(days=20),
                actual_start_date=today - timedelta(days=18),
                actual_end_date=today - timedelta(days=3),
                planned_work_days=5,
                area_m2=12.0,
                color="Szürke",
                vat_invoice=True,
            ),
            "cost": dict(labor_fee=260000, travel_fee=15000, distributor_commission=75000, materials_fee=110000),
            "logistics": dict(key_code="B-07", arrival_time="08:00", parking="Kapu előtt"),
        },
        {
            "project": dict(
                client_name="Nagy Péter",
                address="Dunakeszi, Fő tér 3.",
                phone="+36 30 222 3344",
                status=ProjectStatus.folyamatban,
                job_type=JobType.falburkolat,
                distributor=Distributor.exotic,
                crew=Crew.dani,
                crew_confirmed=True,
                priority=Priority.halasztható,
                planned_start_date=today - timedelta(days=2),
                actual_start_date=today - timedelta(days=2),
                planned_work_days=6,
                area_m2=35.0,
                color="Teak",
            ),
            "cost": dict(labor_fee=390000, travel_fee=30000, distributor_commission=80000, materials_fee=165000),
        },
        {
            "project": dict(
                client_name="Kiss Katalin",
                address="Szentendre, Bogdányi út 14.",
                phone="+36 70 111 2233",
                status=ProjectStatus.betervezve,
                job_type=JobType.terasz,
                distributor=Distributor.marka_mix,
                crew=Crew.alex,
                crew_confirmed=False,
                priority=Priority.normal,
                planned_start_date=today + timedelta(days=22),
                planned_work_days=10,
                area_m2=52.0,
                color="Bangkirai",
                notes="Fedett terasz, esővédő megoldás szükséges.",
            ),
            "cost": dict(labor_fee=720000, travel_fee=40000, distributor_commission=180000, materials_fee=380000),
            "logistics": dict(special_requests="Esővédő megoldás, fedett terasz — anyagrendelés koordinálása szükséges."),
        },
        {
            "project": dict(
                client_name="Varga János",
                address="Budapest, XIV. ker., Vezér u. 56.",
                phone="+36 20 666 7788",
                status=ProjectStatus.lebeszélve,
                job_type=JobType.javitas,
                distributor=Distributor.sajat,
                crew=Crew.nincs,
                priority=Priority.normal,
                notes="Garancia javítás, csavarcsere szükséges.",
            ),
            "cost": dict(labor_fee=45000, travel_fee=8000, distributor_commission=0, materials_fee=5000),
        },
        {
            "project": dict(
                client_name="Fekete Zsuzsanna",
                address="Visegrád, Fő u. 1.",
                phone="+36 30 999 0011",
                status=ProjectStatus.kesz,
                job_type=JobType.vegyes,
                distributor=Distributor.global_,
                crew=Crew.laci,
                crew_confirmed=True,
                priority=Priority.normal,
                planned_start_date=today - timedelta(days=45),
                actual_start_date=today - timedelta(days=43),
                actual_end_date=today - timedelta(days=35),
                planned_work_days=7,
                area_m2=22.0,
                planner_project_id="PLN-2025-042",
            ),
            "cost": dict(labor_fee=450000, travel_fee=55000, distributor_commission=110000, materials_fee=145000),
            "logistics": dict(
                key_code="V-01",
                parking="Utcán szabad parkolás",
                power_access="Kert végén, hosszabbító szükséges",
            ),
        },
    ]

    for s in seeds:
        p = Project(**s["project"])
        session.add(p)
        session.flush()
        session.add(ProjectCost(project_id=p.id, **s["cost"]))
        if "logistics" in s:
            session.add(ProjectLogistics(project_id=p.id, **s["logistics"]))

    session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    with Session(engine) as session:
        seed_projects(session)
    yield


app = FastAPI(title="WPC Projekt Adminisztrátor", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def _fmt_huf(n) -> str:
    if n is None:
        return "—"
    return f"{int(n):,}".replace(",", " ") + " Ft"


templates.env.filters["huf"] = _fmt_huf


@app.get("/health")
def health():
    return {"status": "ok", "app": "WPC Projekt Adminisztrátor"}


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    q: str = "",
    status_filter: str = "",
    session: Session = Depends(get_session),
):
    all_projects = list(
        session.exec(select(Project).where(Project.status != ProjectStatus.torolt)).all()
    )

    today = date.today()
    stats = {
        "total": len(all_projects),
        "folyamatban": sum(1 for p in all_projects if p.status == ProjectStatus.folyamatban),
        "betervezve": sum(1 for p in all_projects if p.status == ProjectStatus.betervezve),
        "havi_bevetel": sum(
            p.cost.labor_fee
            for p in all_projects
            if p.status == ProjectStatus.kesz
            and p.cost
            and p.actual_end_date
            and p.actual_end_date.year == today.year
            and p.actual_end_date.month == today.month
        ),
    }

    filtered = all_projects
    if status_filter:
        filtered = [p for p in filtered if p.status.value == status_filter]
    if q:
        q_l = q.lower()
        filtered = [
            p for p in filtered
            if q_l in (p.client_name or "").lower() or q_l in (p.address or "").lower()
        ]

    ctx = {
        "request": request,
        "module": "admin",
        "projects": filtered,
        "stats": stats,
        "q": q,
        "status_filter": status_filter,
    }

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("project_table.html", ctx)

    return templates.TemplateResponse("projects.html", ctx)


@app.get("/projects/{project_id}/detail", response_class=HTMLResponse)
def project_detail(
    project_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    p = session.get(Project, project_id)
    if not p:
        return HTMLResponse("<p>Nem található</p>", status_code=404)
    return templates.TemplateResponse("project_detail.html", {"request": request, "p": p})


# ── Form context shared by both new & edit ────────────────────────────────────

_ENUM_CTX = {
    "InvoiceType": InvoiceType,
    "ProjectStatus": ProjectStatus,
    "JobType": JobType,
    "Distributor": Distributor,
    "Crew": Crew,
    "Priority": Priority,
}


def _parse_form(form) -> tuple[dict, dict, dict]:
    """Return (project_data, cost_data, logistics_data) parsed from a form submission."""
    def d(k):
        v = form.get(k, "")
        return date.fromisoformat(v) if v else None

    def i(k):
        return int(form.get(k) or 0)

    def s(k):
        v = form.get(k, "").strip()
        return v or None

    project_data = dict(
        client_name=form.get("client_name", "").strip(),
        address=s("address"),
        phone=s("phone"),
        email=s("email"),
        invoice_type=InvoiceType(form.get("invoice_type") or InvoiceType.maganszemely.value),
        status=ProjectStatus(form.get("status") or ProjectStatus.felmerendo.value),
        priority=Priority(form.get("priority") or Priority.normal.value),
        job_type=JobType(form.get("job_type") or JobType.terasz.value),
        distributor=Distributor(form.get("distributor") or Distributor.royal.value),
        crew=Crew(form.get("crew") or Crew.nincs.value),
        crew_confirmed=form.get("crew_confirmed") == "on",
        vat_invoice=form.get("vat_invoice") == "on",
        welding_required=form.get("welding_required") == "on",
        covered_area=form.get("covered_area") == "on",
        phase=s("phase"),
        area_m2=float(form["area_m2"]) if form.get("area_m2") else None,
        color=s("color"),
        survey_date=d("survey_date"),
        ideal_start_date=d("ideal_start_date"),
        planned_start_date=d("planned_start_date"),
        planned_work_days=int(form["planned_work_days"]) if form.get("planned_work_days") else None,
        actual_start_date=d("actual_start_date"),
        actual_end_date=d("actual_end_date"),
        notes=s("notes"),
    )
    cost_data = dict(
        labor_fee=i("labor_fee"),
        travel_fee=i("travel_fee"),
        distributor_commission=i("distributor_commission"),
        materials_fee=i("materials_fee"),
    )
    logistics_data = dict(
        key_code=s("key_code"),
        power_access=s("power_access"),
        arrival_time=s("arrival_time"),
        parking=s("parking"),
        materials_to_bring=s("materials_to_bring"),
        special_requests=s("special_requests"),
    )
    return project_data, cost_data, logistics_data


# ── New project ───────────────────────────────────────────────────────────────

@app.get("/projects/new", response_class=HTMLResponse)
def project_new_form(request: Request):
    return templates.TemplateResponse(
        "project_form.html",
        {"request": request, "module": "admin", "p": None, **_ENUM_CTX},
    )


@app.post("/projects/new")
async def project_new_submit(request: Request, session: Session = Depends(get_session)):
    form = await request.form()
    project_data, cost_data, logistics_data = _parse_form(form)
    p = Project(**project_data)
    session.add(p)
    session.flush()
    session.add(ProjectCost(project_id=p.id, **cost_data))
    if any(v for v in logistics_data.values()):
        session.add(ProjectLogistics(project_id=p.id, **logistics_data))
    session.commit()
    return RedirectResponse("/", status_code=303)


# ── Edit project ──────────────────────────────────────────────────────────────

@app.get("/projects/{project_id}/edit", response_class=HTMLResponse)
def project_edit_form(
    project_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    p = session.get(Project, project_id)
    if not p:
        return HTMLResponse("<p>Nem található</p>", status_code=404)
    return templates.TemplateResponse(
        "project_form.html",
        {"request": request, "module": "admin", "p": p, **_ENUM_CTX},
    )


@app.post("/projects/{project_id}/edit")
async def project_edit_submit(
    project_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    p = session.get(Project, project_id)
    if not p:
        return HTMLResponse("<p>Nem található</p>", status_code=404)
    form = await request.form()
    project_data, cost_data, logistics_data = _parse_form(form)
    for k, v in project_data.items():
        setattr(p, k, v)
    p.updated_at = datetime.utcnow()
    # upsert cost
    if p.cost:
        for k, v in cost_data.items():
            setattr(p.cost, k, v)
        session.add(p.cost)
    else:
        session.add(ProjectCost(project_id=p.id, **cost_data))
    # upsert logistics
    if p.logistics:
        for k, v in logistics_data.items():
            setattr(p.logistics, k, v)
        session.add(p.logistics)
    elif any(v for v in logistics_data.values()):
        session.add(ProjectLogistics(project_id=p.id, **logistics_data))
    session.add(p)
    session.commit()
    return RedirectResponse("/", status_code=303)


# ── Delete project (soft) ─────────────────────────────────────────────────────

@app.get("/projects/{project_id}/delete", response_class=HTMLResponse)
def project_delete_confirm(
    project_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    p = session.get(Project, project_id)
    if not p:
        return HTMLResponse("<p>Nem található</p>", status_code=404)
    return templates.TemplateResponse(
        "confirm_delete.html",
        {"request": request, "module": "admin", "p": p},
    )


@app.post("/projects/{project_id}/delete")
def project_delete_submit(
    project_id: int,
    session: Session = Depends(get_session),
):
    p = session.get(Project, project_id)
    if p:
        p.status = ProjectStatus.torolt
        session.add(p)
        session.commit()
    return RedirectResponse("/", status_code=303)
