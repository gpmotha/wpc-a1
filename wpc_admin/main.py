import logging
import logging.handlers
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

import openpyxl

from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, SQLModel, select

from database import create_tables, engine, get_session
from models import (
    CalendarEntry, CalendarEntryType,
    Crew, Distributor, InvoiceType, JobType, Priority,
    Project, ProjectCost, ProjectLogistics, ProjectStatus,
)


# ── Logging setup ─────────────────────────────────────────────────────────────

_LOG_DIR = Path(__file__).parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

_fmt = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_fmt)

_file_handler = logging.handlers.RotatingFileHandler(
    _LOG_DIR / "wpc_admin.log",
    maxBytes=5 * 1024 * 1024,  # 5 MB
    backupCount=3,
    encoding="utf-8",
)
_file_handler.setFormatter(_fmt)

logging.basicConfig(level=logging.INFO, handlers=[_console_handler, _file_handler])

# Quieten noisy libraries
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

logger = logging.getLogger("wpc_admin")


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
    logger.info("WPC Admin starting up")
    create_tables()
    with Session(engine) as session:
        seed_projects(session)
    logger.info("WPC Admin ready")
    yield
    logger.info("WPC Admin shutting down")


app = FastAPI(title="WPC Projekt Adminisztrátor", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/icons", StaticFiles(directory="icons"), name="icons")
templates = Jinja2Templates(directory="templates")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    # Skip static assets to avoid noise
    if not request.url.path.startswith("/static"):
        logger.info(
            "%s %s %s %.0fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
    return response


def _fmt_huf(n) -> str:
    if n is None:
        return "—"
    return f"{int(n):,}".replace(",", " ") + " Ft"


templates.env.filters["huf"] = _fmt_huf


def _fmt_huf_k(n) -> str:
    """Abbreviated: 1_200_000 → '1.2M', 480_000 → '480e'"""
    if not n:
        return "0"
    if n >= 1_000_000:
        v = n / 1_000_000
        return f"{v:.1f}M" if n % 1_000_000 else f"{int(v)}M"
    if n >= 1_000:
        return f"{n // 1_000}e"
    return str(int(n))


templates.env.filters["huf_k"] = _fmt_huf_k


@app.get("/health")
def health():
    return {"status": "ok", "app": "WPC Projekt Adminisztrátor"}


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    q: str = "",
    session: Session = Depends(get_session),
):
    from collections import defaultdict

    all_projects = list(
        session.exec(select(Project).where(Project.status != ProjectStatus.torolt)).all()
    )

    today = date.today()
    stats = {
        "folyamatban": sum(1 for p in all_projects if p.status == ProjectStatus.folyamatban),
        "betervezve": sum(1 for p in all_projects if p.status == ProjectStatus.betervezve),
        "pipeline_value": sum(
            p.total_net for p in all_projects
            if p.status in (ProjectStatus.betervezve, ProjectStatus.folyamatban)
        ),
        "havi_bevetel": sum(
            p.total_net
            for p in all_projects
            if p.status == ProjectStatus.kesz
            and p.actual_end_date
            and p.actual_end_date.year == today.year
            and p.actual_end_date.month == today.month
        ),
    }

    filtered = all_projects
    if q:
        q_l = q.lower()
        filtered = [
            p for p in filtered
            if q_l in (p.client_name or "").lower()
            or q_l in (p.address or "").lower()
            or q_l in (p.varos or "").lower()
        ]

    projects_by_status: dict = defaultdict(list)
    sums_by_status: dict = defaultdict(int)
    for p in filtered:
        projects_by_status[p.status.value].append(p)
        sums_by_status[p.status.value] += p.total_net

    ctx = {
        "request": request,
        "module": "admin",
        "active_page": "projects",
        "projects": filtered,
        "projects_by_status": dict(projects_by_status),
        "sums_by_status": dict(sums_by_status),
        "stats": stats,
        "q": q,
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
        iranyitoszam=s("iranyitoszam"),
        varos=s("varos"),
        utca=s("utca"),
        hazszam=s("hazszam"),
        egyeb=s("egyeb"),
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
async def project_new_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    form = await request.form()
    project_data, cost_data, logistics_data = _parse_form(form)
    p = Project(**project_data)
    session.add(p)
    session.flush()
    session.add(ProjectCost(project_id=p.id, **cost_data))
    if any(v for v in logistics_data.values()):
        session.add(ProjectLogistics(project_id=p.id, **logistics_data))
    session.commit()
    logger.info("Project created: id=%s client=%r status=%s", p.id, p.client_name, p.status.value)
    if _needs_geocode(p):
        background_tasks.add_task(_geocode_project_by_id, p.id)
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
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    p = session.get(Project, project_id)
    if not p:
        return HTMLResponse("<p>Nem található</p>", status_code=404)
    form = await request.form()
    project_data, cost_data, logistics_data = _parse_form(form)
    address_changed = any(
        getattr(p, k) != project_data.get(k)
        for k in ("iranyitoszam", "varos", "utca", "hazszam", "address")
    )
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
    # clear stale geocode when address changes so it re-geocodes
    if address_changed and p.lat is not None:
        p.lat = None
        p.lng = None
        p.geocode_ok = 0
    session.add(p)
    session.commit()
    logger.info("Project updated: id=%s client=%r status=%s", p.id, p.client_name, p.status.value)
    if _needs_geocode(p):
        background_tasks.add_task(_geocode_project_by_id, p.id)
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
        logger.info("Project soft-deleted: id=%s client=%r", project_id, p.client_name)
    else:
        logger.warning("Delete attempted on missing project: id=%s", project_id)
    return RedirectResponse("/", status_code=303)


# ── Finance page ─────────────────────────────────────────────────────────────

_MONTH_LABELS = ["Jan", "Feb", "Már", "Ápr", "Máj", "Jún", "Júl", "Aug", "Szep", "Okt", "Nov", "Dec"]


def _prev_months(today: date, n: int) -> list[tuple[int, int]]:
    months = []
    y, m = today.year, today.month
    for _ in range(n):
        months.insert(0, (y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return months


@app.get("/finance", response_class=HTMLResponse)
def finance_view(request: Request, session: Session = Depends(get_session)):
    from collections import defaultdict

    all_projects = list(session.exec(select(Project)).all())
    today = date.today()

    done = [p for p in all_projects if p.status == ProjectStatus.kesz]
    pipeline = [p for p in all_projects if p.status in (ProjectStatus.betervezve, ProjectStatus.folyamatban)]

    this_month_done = [
        p for p in done
        if p.actual_end_date
        and p.actual_end_date.year == today.year
        and p.actual_end_date.month == today.month
    ]
    ytd_done = [p for p in done if p.actual_end_date and p.actual_end_date.year == today.year]

    stats = {
        "monthly_net": sum(p.total_net for p in this_month_done),
        "monthly_count": len(this_month_done),
        "ytd_net": sum(p.total_net for p in ytd_done),
        "ytd_count": len(ytd_done),
        "pipeline_value": sum(p.total_net for p in pipeline),
        "pipeline_count": len(pipeline),
        "total_all_time": sum(p.total_net for p in done),
    }

    monthly_breakdown = []
    for y, m in _prev_months(today, 6):
        month_done = [p for p in done if p.actual_end_date and p.actual_end_date.year == y and p.actual_end_date.month == m]
        monthly_breakdown.append({
            "year": y, "month": m,
            "label": _MONTH_LABELS[m - 1],
            "count": len(month_done),
            "net": sum(p.total_net for p in month_done),
        })

    dist_agg: dict = defaultdict(lambda: {"count": 0, "net": 0})
    crew_agg: dict = defaultdict(lambda: {"count": 0, "net": 0})
    for p in done:
        dist_agg[p.distributor.value]["count"] += 1
        dist_agg[p.distributor.value]["net"] += p.total_net
        crew_agg[p.crew.value]["count"] += 1
        crew_agg[p.crew.value]["net"] += p.total_net

    dist_stats = sorted(dist_agg.items(), key=lambda x: x[1]["net"], reverse=True)
    crew_stats = sorted(crew_agg.items(), key=lambda x: x[1]["net"], reverse=True)

    ctx = {
        "request": request,
        "module": "admin",
        "active_page": "finance",
        "today": today,
        "stats": stats,
        "monthly_breakdown": monthly_breakdown,
        "dist_stats": dist_stats,
        "crew_stats": crew_stats,
        "dist_max": max((ds["net"] for _, ds in dist_stats), default=1) or 1,
        "crew_max": max((cs["net"] for _, cs in crew_stats), default=1) or 1,
        "top_projects": sorted(done, key=lambda p: p.total_net, reverse=True)[:8],
    }
    return templates.TemplateResponse("finance.html", ctx)


# ── Ajánlatok page ────────────────────────────────────────────────────────────

@app.get("/ajanlatok", response_class=HTMLResponse)
def ajanlatok_view(request: Request, session: Session = Depends(get_session)):
    projects = list(session.exec(
        select(Project).where(
            Project.status.in_([ProjectStatus.felmerendo, ProjectStatus.lebeszélve])
        )
    ).all())
    projects.sort(key=lambda p: p.created_at, reverse=True)
    total_quoted = sum(p.total_net for p in projects)
    felmerendo_count = sum(1 for p in projects if p.status == ProjectStatus.felmerendo)
    lebeszelt_count = sum(1 for p in projects if p.status == ProjectStatus.lebeszélve)
    return templates.TemplateResponse("ajanlatok.html", {
        "request": request,
        "module": "admin",
        "active_page": "ajanlatok",
        "projects": projects,
        "total_quoted": total_quoted,
        "felmerendo_count": felmerendo_count,
        "lebeszelt_count": lebeszelt_count,
        **_ENUM_CTX,
    })


# ── Garancia page ─────────────────────────────────────────────────────────────

@app.get("/garancia", response_class=HTMLResponse)
def garancia_view(request: Request, session: Session = Depends(get_session)):
    from datetime import timedelta
    today = date.today()
    projects = list(session.exec(
        select(Project).where(
            Project.status == ProjectStatus.kesz,
            Project.actual_end_date.is_not(None),
        )
    ).all())
    # Only projects still in or recently past warranty window (730 days)
    projects.sort(key=lambda p: p.warranty_expires)

    active = sum(1 for p in projects if p.warranty_expires >= today)
    expiring_soon = sum(1 for p in projects if today <= p.warranty_expires <= today + timedelta(days=180))
    expired = sum(1 for p in projects if p.warranty_expires < today)
    days_remaining_list = [(p.warranty_expires - today).days for p in projects if p.warranty_expires >= today]
    avg_days = round(sum(days_remaining_list) / len(days_remaining_list)) if days_remaining_list else 0

    return templates.TemplateResponse("garancia.html", {
        "request": request,
        "module": "admin",
        "active_page": "garancia",
        "projects": projects,
        "today": today,
        "stats": {
            "total": len(projects),
            "active": active,
            "expiring_soon": expiring_soon,
            "expired": expired,
            "avg_days": avg_days,
        },
        **_ENUM_CTX,
    })


# ── Map page ──────────────────────────────────────────────────────────────────

@app.get("/map", response_class=HTMLResponse)
def map_view(request: Request):
    return templates.TemplateResponse(
        "map.html",
        {"request": request, "module": "admin", "active_page": "map"},
    )


# ── Map API ───────────────────────────────────────────────────────────────────

_STATUS_ORDER = [
    ProjectStatus.felmerendo,
    ProjectStatus.lebeszélve,
    ProjectStatus.betervezve,
    ProjectStatus.folyamatban,
    ProjectStatus.kesz,
    ProjectStatus.torolt,
]
_DEFAULT_HIDDEN = {ProjectStatus.kesz.value, ProjectStatus.torolt.value}


@app.get("/api/jobs/map")
def jobs_map(
    status: str = "",
    crew: str = "",
    session: Session = Depends(get_session),
):
    stmt = select(Project).where(Project.lat.is_not(None), Project.lng.is_not(None))
    projects = list(session.exec(stmt).all())

    # Parse filter params
    status_filter = {v.strip() for v in status.split(",") if v.strip()} if status else set()
    crew_filter = {v.strip() for v in crew.split(",") if v.strip()} if crew else set()

    # "all" = no status filtering; otherwise default excludes kész and törölt
    if status_filter == {"all"}:
        pass  # return all statuses
    elif not status_filter:
        projects = [p for p in projects if p.status.value not in _DEFAULT_HIDDEN]
    else:
        projects = [p for p in projects if p.status.value in status_filter]

    if crew_filter:
        projects = [p for p in projects if p.crew.value in crew_filter]

    def fmt_address(p: Project) -> str:
        parts = []
        if p.iranyitoszam:
            parts.append(p.iranyitoszam)
        if p.varos:
            parts.append(p.varos)
        if p.utca:
            parts.append(p.utca)
        if p.hazszam:
            parts.append(p.hazszam)
        if p.egyeb:
            parts.append(p.egyeb)
        return ", ".join(parts) if parts else (p.address or "")

    result = []
    for p in projects:
        result.append({
            "id": p.id,
            "client_name": p.client_name,
            "status": p.status.value,
            "job_type": p.job_type.value,
            "crew": p.crew.value,
            "phase": p.phase,
            "address": fmt_address(p),
            "planned_start_date": p.planned_start_date.isoformat() if p.planned_start_date else None,
            "planned_work_days": p.planned_work_days,
            "labor_fee": p.cost.labor_fee if p.cost else None,
            "lat": p.lat,
            "lng": p.lng,
        })
    return JSONResponse(result)


@app.get("/api/jobs/map/missing")
def jobs_map_missing(session: Session = Depends(get_session)):
    all_with_address = list(
        session.exec(
            select(Project).where(
                Project.lat.is_(None),
                (Project.iranyitoszam.is_not(None)) | (Project.address.is_not(None)),
            )
        ).all()
    )
    return JSONResponse({"count": len(all_with_address)})


# ── Geocode helpers ───────────────────────────────────────────────────────────

def _needs_geocode(p: Project) -> bool:
    if p.lat is not None:
        return False
    return bool(
        (p.iranyitoszam and p.varos and p.utca and p.hazszam) or p.address
    )


def _geocode_project_by_id(project_id: int) -> None:
    import time
    import urllib.request
    import urllib.parse
    import json as _json
    from database import engine as _engine
    from sqlmodel import Session as _Session

    with _Session(_engine) as sess:
        p = sess.get(Project, project_id)
        if not p or p.lat is not None:
            return

        if p.iranyitoszam and p.varos and p.utca and p.hazszam:
            params = {
                "street": f"{p.hazszam} {p.utca}",
                "city": p.varos,
                "postalcode": p.iranyitoszam,
                "country": "Hungary",
                "format": "json",
                "limit": "1",
            }
        elif p.address:
            params = {"q": f"{p.address}, Hungary", "format": "json", "limit": "1"}
        else:
            return

        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
        _log = logging.getLogger("wpc_admin.geocoder")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "WPC-Admin/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read())
            if data:
                p.lat = float(data[0]["lat"])
                p.lng = float(data[0]["lon"])
                p.geocode_ok = 1
                _log.info("Geocoded project id=%s: (%.5f, %.5f)", project_id, p.lat, p.lng)
            else:
                p.geocode_ok = -1
                _log.warning("Geocode returned no results for project id=%s", project_id)
        except Exception as exc:
            p.geocode_ok = -1
            _log.error("Geocode failed for project id=%s: %s", project_id, exc)

        p.geocode_at = datetime.utcnow().isoformat()
        sess.add(p)
        sess.commit()


# ── Geocode admin ─────────────────────────────────────────────────────────────

_geocode_state: dict = {"running": False, "processed": 0, "total": 0, "errors": []}


def _run_geocode_background() -> None:
    import time
    import urllib.request
    import urllib.parse
    import json as _json
    from database import engine as _engine
    from sqlmodel import Session as _Session, select as _select

    _log = logging.getLogger("wpc_admin.geocoder")

    with _Session(_engine) as sess:
        candidates = list(
            sess.exec(
                _select(Project).where(Project.lat.is_(None))
            ).all()
        )
        _geocode_state["total"] = len(candidates)
        _log.info("Bulk geocode started: %d candidates", len(candidates))

        for p in candidates:
            query: dict = {}
            if p.iranyitoszam and p.varos and p.utca and p.hazszam:
                query = {
                    "street": f"{p.hazszam} {p.utca}",
                    "city": p.varos,
                    "postalcode": p.iranyitoszam,
                    "country": "Hungary",
                    "format": "json",
                    "limit": "1",
                }
            elif p.address:
                query = {
                    "q": f"{p.address}, Hungary",
                    "format": "json",
                    "limit": "1",
                }
            else:
                p.geocode_ok = -1
                p.geocode_at = datetime.utcnow().isoformat()
                sess.add(p)
                sess.commit()
                _geocode_state["processed"] += 1
                continue

            url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(query)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "WPC-Admin/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = _json.loads(resp.read())
                if data:
                    p.lat = float(data[0]["lat"])
                    p.lng = float(data[0]["lon"])
                    p.geocode_ok = 1
                    _log.info("Geocoded id=%s: (%.5f, %.5f)", p.id, p.lat, p.lng)
                else:
                    p.geocode_ok = -1
                    label = p.address or f"id={p.id}"
                    _geocode_state["errors"].append(label)
                    _log.warning("No geocode result for %s", label)
            except Exception as exc:
                p.geocode_ok = -1
                _geocode_state["errors"].append(str(exc))
                _log.error("Geocode error for project id=%s: %s", p.id, exc)
            p.geocode_at = datetime.utcnow().isoformat()
            sess.add(p)
            sess.commit()
            _geocode_state["processed"] += 1
            time.sleep(1)

    _log.info(
        "Bulk geocode finished: %d processed, %d errors",
        _geocode_state["processed"],
        len(_geocode_state["errors"]),
    )
    _geocode_state["running"] = False


@app.post("/api/admin/geocode")
def admin_geocode_start(background_tasks: BackgroundTasks):
    if _geocode_state["running"]:
        return JSONResponse({"error": "already running"}, status_code=409)
    _geocode_state["running"] = True
    _geocode_state["processed"] = 0
    _geocode_state["errors"] = []
    background_tasks.add_task(_run_geocode_background)
    return JSONResponse({"started": True})


@app.get("/api/admin/geocode/status")
def admin_geocode_status():
    return JSONResponse(_geocode_state)


# ── Calendar ─────────────────────────────────────────────────────────────────

@app.get("/calendar", response_class=HTMLResponse)
def calendar_view(request: Request):
    return templates.TemplateResponse(
        "calendar.html",
        {"request": request, "module": "admin", "active_page": "calendar"},
    )


@app.get("/api/calendar/entries")
def calendar_entries_list(
    from_: str = "",
    to: str = "",
    session: Session = Depends(get_session),
):
    stmt = select(CalendarEntry)
    if from_:
        try:
            stmt = stmt.where(CalendarEntry.date >= date.fromisoformat(from_))
        except ValueError:
            pass
    if to:
        try:
            stmt = stmt.where(CalendarEntry.date <= date.fromisoformat(to))
        except ValueError:
            pass
    entries = list(session.exec(stmt).all())
    result = []
    for e in entries:
        project_name = None
        project_address = None
        if e.project_id:
            p = session.get(Project, e.project_id)
            if p:
                project_name = p.client_name
                project_address = p.address
        result.append({
            "id": e.id,
            "date": e.date.isoformat(),
            "crew": e.crew.value,
            "type": e.entry_type.value,
            "text": e.text,
            "project_id": e.project_id,
            "project_name": project_name,
            "project_address": project_address,
        })
    return JSONResponse(result)


class _CalEntryBody(SQLModel):
    date: str
    crew: str
    type: str
    text: str = ""
    project_id: int | None = None


@app.post("/api/calendar/entries")
def calendar_entry_upsert(
    body: _CalEntryBody,
    session: Session = Depends(get_session),
):
    try:
        entry_date = date.fromisoformat(body.date)
        crew = Crew(body.crew)
        entry_type = CalendarEntryType(body.type)
    except (ValueError, KeyError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=422)

    existing = session.exec(
        select(CalendarEntry).where(
            CalendarEntry.date == entry_date,
            CalendarEntry.crew == crew,
        )
    ).first()

    if existing:
        existing.entry_type = entry_type
        existing.text = body.text or None
        existing.project_id = body.project_id
        session.add(existing)
        session.commit()
        session.refresh(existing)
        logger.info("Calendar entry updated: id=%s date=%s crew=%s type=%s", existing.id, entry_date, crew.value, entry_type.value)
        return JSONResponse({"id": existing.id})
    else:
        entry = CalendarEntry(
            date=entry_date,
            crew=crew,
            entry_type=entry_type,
            text=body.text or None,
            project_id=body.project_id,
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        logger.info("Calendar entry created: id=%s date=%s crew=%s type=%s", entry.id, entry_date, crew.value, entry_type.value)
        return JSONResponse({"id": entry.id})


@app.delete("/api/calendar/entries/{entry_id}")
def calendar_entry_delete(
    entry_id: int,
    session: Session = Depends(get_session),
):
    entry = session.get(CalendarEntry, entry_id)
    if entry:
        session.delete(entry)
        session.commit()
        logger.info("Calendar entry deleted: id=%s", entry_id)
    return JSONResponse({"deleted": entry_id})


@app.get("/api/projects/eligible")
def projects_eligible(session: Session = Depends(get_session)):
    eligible_statuses = {
        ProjectStatus.betervezve,
        ProjectStatus.folyamatban,
        ProjectStatus.kesz,
    }
    projects = list(session.exec(select(Project)).all())
    return JSONResponse([
        {
            "id": p.id,
            "client_name": p.client_name,
            "address": p.address or "",
        }
        for p in projects
        if p.status in eligible_statuses
    ])


# ── Csapatok (crew utilization) ───────────────────────────────────────────────

_ACTIVE_CREWS = [Crew.laci, Crew.jeno, Crew.csaba, Crew.dani, Crew.alex]

_CREW_CSS = {
    Crew.laci:  "laci",
    Crew.jeno:  "jeno",
    Crew.csaba: "csaba",
    Crew.dani:  "dani",
    Crew.alex:  "alex",
}


def _workdays_in_range(start: date, end: date) -> int:
    return sum(
        1 for i in range((end - start).days + 1)
        if (start + timedelta(days=i)).weekday() < 5
    )


def _get_period_range(period: str, today: date) -> tuple[date, date, str]:
    import calendar as _cal
    y = today.year
    month_short = ["jan","feb","már","ápr","máj","jún","júl","aug","sze","okt","nov","dec"]
    if period == "q1":
        return date(y, 1, 1), date(y, 3, 31), f"Q1 · jan–már {y}"
    elif period == "q2":
        return date(y, 4, 1), date(y, 6, 30), f"Q2 · ápr–jún {y}"
    elif period == "q3":
        return date(y, 7, 1), date(y, 9, 30), f"Q3 · júl–sze {y}"
    elif period == "q4":
        return date(y, 10, 1), date(y, 12, 31), f"Q4 · okt–dec {y}"
    elif period == "month":
        last_day = _cal.monthrange(y, today.month)[1]
        return date(y, today.month, 1), date(y, today.month, last_day), f"{month_short[today.month - 1]} {y}"
    else:
        return date(y, 1, 1), date(y, 12, 31), f"{y} teljes év"


@app.get("/csapatok", response_class=HTMLResponse)
def csapatok_view(
    request: Request,
    period: str = "all",
    session: Session = Depends(get_session),
):
    today = date.today()
    date_from, date_to, period_label = _get_period_range(period, today)

    cal_entries = list(session.exec(
        select(CalendarEntry).where(
            CalendarEntry.date >= date_from,
            CalendarEntry.date <= date_to,
        )
    ).all())

    horizon_from = today + timedelta(days=1)
    horizon_to = today + timedelta(days=90)
    horizon_entries = list(session.exec(
        select(CalendarEntry).where(
            CalendarEntry.date >= horizon_from,
            CalendarEntry.date <= horizon_to,
            CalendarEntry.entry_type == CalendarEntryType.munka,
        )
    ).all())

    all_projects = list(session.exec(select(Project)).all())
    active_projects = [
        p for p in all_projects
        if p.status in (ProjectStatus.betervezve, ProjectStatus.folyamatban)
    ]

    workdays = _workdays_in_range(date_from, date_to)

    crews_data = []
    for crew in _ACTIVE_CREWS:
        counts = {t.value: 0 for t in CalendarEntryType}
        for e in cal_entries:
            if e.crew == crew:
                counts[e.entry_type.value] += 1

        n_munka = counts["munka"]
        n_szabi = counts["szabi"]
        n_eso = counts["eso"] + counts["szel"]
        n_beteg = counts["beteg"]
        n_munkaszunet = counts["munkaszunet"]

        util_pct = round(n_munka / workdays * 100) if workdays else 0
        t = max(workdays, 1)

        jobs = [p for p in active_projects if p.crew == crew]
        total_rev = sum((p.cost.labor_fee if p.cost else 0) for p in jobs)
        horizon_days = sum(1 for e in horizon_entries if e.crew == crew)

        crews_data.append({
            "name": crew.value,
            "css_key": _CREW_CSS[crew],
            "n_munka": n_munka,
            "n_szabi": n_szabi,
            "n_eso": n_eso,
            "n_beteg": n_beteg,
            "n_munkaszunet": n_munkaszunet,
            "workdays": workdays,
            "util_pct": util_pct,
            "pct_munka": round(n_munka / t * 100, 1),
            "pct_szabi": round(n_szabi / t * 100, 1),
            "pct_eso":   round(n_eso   / t * 100, 1),
            "pct_beteg": round(n_beteg / t * 100, 1),
            "pct_msz":   round(n_munkaszunet / t * 100, 1),
            "jobs": jobs[:5],
            "jobs_extra": max(0, len(jobs) - 5),
            "total_rev": total_rev,
            "horizon_days": horizon_days,
        })

    total_munka = sum(c["n_munka"] for c in crews_data)
    total_capacity = workdays * len(_ACTIVE_CREWS)
    overall_util_pct = round(total_munka / total_capacity * 100) if total_capacity else 0

    all_crew_jobs = [
        (crew.value, _CREW_CSS[crew], p)
        for crew in _ACTIVE_CREWS
        for p in active_projects
        if p.crew == crew
    ]

    ctx = {
        "request": request,
        "module": "admin",
        "active_page": "csapatok",
        "period": period,
        "period_label": period_label,
        "crews": crews_data,
        "summary": {
            "crew_count": len(_ACTIVE_CREWS),
            "workdays_per_crew": workdays,
            "overall_util_pct": overall_util_pct,
            "total_munka": total_munka,
            "total_szabi": sum(c["n_szabi"] for c in crews_data),
            "total_eso": sum(c["n_eso"] for c in crews_data),
            "total_beteg": sum(c["n_beteg"] for c in crews_data),
        },
        "all_crew_jobs": all_crew_jobs,
    }

    tmpl = "csapatok_content.html" if request.headers.get("HX-Request") else "csapatok.html"
    return templates.TemplateResponse(tmpl, ctx)


# ── Admin: XLSX backup ─────────────────────────────────────────────────────────

def _cell_value(v):
    if v is None:
        return ""
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, bool):
        return v
    if hasattr(v, "value"):  # enum
        return v.value
    return v


@app.get("/api/admin/backup")
def admin_backup(session: Session = Depends(get_session)):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    specs = [
        ("Projektek",  Project,           list(Project.__fields__)),
        ("Koltsegek",  ProjectCost,        list(ProjectCost.__fields__)),
        ("Logisztika", ProjectLogistics,   list(ProjectLogistics.__fields__)),
        ("Naptar",     CalendarEntry,      list(CalendarEntry.__fields__)),
    ]

    for sheet_name, model, fields in specs:
        ws = wb.create_sheet(sheet_name)
        ws.append(fields)
        for row in session.exec(select(model)).all():
            ws.append([_cell_value(getattr(row, f, None)) for f in fields])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"wpc_backup_{date.today().isoformat()}.xlsx"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request, "active_page": "settings"})
