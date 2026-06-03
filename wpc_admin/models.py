from enum import Enum
from typing import Optional
from datetime import date, datetime
from sqlmodel import Field, SQLModel, Relationship


class InvoiceType(str, Enum):
    ceg = "cég"
    maganszemely = "magánszemély"


class ProjectStatus(str, Enum):
    felmerendo = "felmérendő"
    lebeszélve = "lebeszélve"
    betervezve = "betervezve"
    folyamatban = "folyamatban"
    kesz = "kész"
    torolt = "törölt"


class JobType(str, Enum):
    terasz = "Terasz"
    kerites = "Kerítés"
    korlat = "Korlát"
    falburkolat = "Falburkolat"
    lepcso = "Lépcső"
    javitas = "Javítás/garancia"
    vegyes = "Vegyes"


class Distributor(str, Enum):
    royal = "Royal"
    royal_buda = "Royal Buda"
    royal_obuda = "Royal Óbuda"
    woopla = "Woopla"
    guru = "Guru"
    global_ = "Global"
    exotic = "Exotic"
    marka_mix = "Márka-Mix"
    sajat = "Saját"
    egyeb = "Egyéb"


class Crew(str, Enum):
    laci = "Laci"
    jeno = "Jenő"
    csaba = "Csaba"
    dani = "Dani"
    alex = "Alex"
    nincs = "Nincs hozzárendelve"


class Priority(str, Enum):
    normal = "Normal"
    surges = "Sürgős"
    halasztható = "Halasztható"


class ProjectCost(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", unique=True)
    labor_fee: int = Field(default=0)
    travel_fee: int = Field(default=0)
    distributor_commission: int = Field(default=0)
    materials_fee: int = Field(default=0)

    project: Optional["Project"] = Relationship(back_populates="cost")


class ProjectLogistics(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", unique=True)
    key_code: Optional[str] = None
    power_access: Optional[str] = None
    arrival_time: Optional[str] = None
    parking: Optional[str] = None
    materials_to_bring: Optional[str] = None
    special_requests: Optional[str] = None

    project: Optional["Project"] = Relationship(back_populates="logistics")


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Client
    client_name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    invoice_type: InvoiceType = InvoiceType.maganszemely

    # Job metadata
    status: ProjectStatus = ProjectStatus.felmerendo
    job_type: JobType = JobType.terasz
    distributor: Distributor = Distributor.royal
    crew: Crew = Crew.nincs
    crew_confirmed: bool = False
    phase: Optional[str] = None
    priority: Priority = Priority.normal

    # Dates
    survey_date: Optional[date] = None
    ideal_start_date: Optional[date] = None
    planned_start_date: Optional[date] = None
    planned_work_days: Optional[int] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None

    # Flags
    welding_required: bool = False
    covered_area: bool = False
    vat_invoice: bool = False

    # Material stub (Phase 2 hook)
    color: Optional[str] = None
    area_m2: Optional[float] = None
    planner_project_id: Optional[str] = None

    notes: Optional[str] = None

    # Address (structured, for geocoding)
    iranyitoszam: Optional[str] = None
    varos:        Optional[str] = None
    utca:         Optional[str] = None
    hazszam:      Optional[str] = None
    egyeb:        Optional[str] = None  # display only (em./ajtó), not geocoded

    # Geocoding result
    lat:          Optional[float] = None
    lng:          Optional[float] = None
    geocode_ok:   Optional[int] = Field(default=0)  # 0=not tried, 1=ok, -1=failed
    geocode_at:   Optional[str] = None              # ISO timestamp of last attempt

    # Relationships
    cost: Optional[ProjectCost] = Relationship(back_populates="project")
    logistics: Optional[ProjectLogistics] = Relationship(back_populates="project")

    @property
    def total_net(self) -> int:
        if not self.cost:
            return 0
        c = self.cost
        return c.labor_fee + c.travel_fee + c.distributor_commission + c.materials_fee

    @property
    def total_gross(self) -> int:
        return round(self.total_net * 1.27) if self.vat_invoice else self.total_net

    @property
    def warranty_expires(self) -> Optional[date]:
        from datetime import timedelta
        return self.actual_end_date + timedelta(days=730) if self.actual_end_date else None


class CalendarEntryType(str, Enum):
    munka       = "munka"
    szabi       = "szabi"
    eso         = "eso"
    szel        = "szel"
    munkaszunet = "munkaszunet"
    beteg       = "beteg"
    lebeszelt   = "lebeszelt"


class CalendarEntry(SQLModel, table=True):
    id:         Optional[int] = Field(default=None, primary_key=True)
    date:       date
    crew:       Crew
    entry_type: CalendarEntryType
    text:       Optional[str] = None
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
