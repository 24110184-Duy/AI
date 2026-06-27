# core/models.py

from dataclasses import dataclass, field


@dataclass
class TileVisual:
    tile: str
    asset_key: str = ""
    rotation: int = 0
    variant: int = 0
    height: int = 1
    footprint: tuple = (1, 1)
    anchor: tuple = (0, 0)
    lot_id: int = 0
    district: str = "mixed"


@dataclass
class CityLot:
    id: int
    tile: str
    anchor: tuple
    footprint: tuple
    cells: list = field(default_factory=list)
    district: str = "mixed"
    height: int = 1
    asset_key: str = ""
    rotation: int = 0
    fire_id: str = ""


@dataclass
class FireIncident:
    id: str
    cell: tuple
    target: tuple
    severity: int
    danger_zone: str = "normal"  # normal / hospital / gas
    required_units: int = 1
    base_score: int = 100

    @property
    def label(self):
        return self.id


@dataclass
class TruckSpec:
    id: str
    station_index: int
    start: tuple
    speed: int
    water: int
    capacity: int
    heavy: bool = False


@dataclass
class SearchResult:
    algorithm: str
    path: list = field(default_factory=list)
    visited: list = field(default_factory=list)
    cost: float = 0
    success: bool = False
    logs: list = field(default_factory=list)
    message: str = ""
    expanded_snapshots: list = field(default_factory=list)
    runtime_ms: float = 0
    metrics: dict = field(default_factory=dict)

    @property
    def path_length(self):
        return max(0, len(self.path) - 1)

    @property
    def visited_count(self):
        return len(self.visited)


@dataclass
class ComboChoice:
    dispatch_ai: str
    priority_ai: str
    route_ai: str
    risk_ai: str

    def as_tuple(self):
        return self.dispatch_ai, self.priority_ai, self.route_ai, self.risk_ai

    def label(self):
        return f"{self.dispatch_ai} | {self.priority_ai} | {self.route_ai} | {self.risk_ai}"


@dataclass
class TruckPlan:
    truck_id: str
    start: tuple
    assigned_fires: list = field(default_factory=list)  # fire ids
    full_path: list = field(default_factory=list)
    path_segments: list = field(default_factory=list)   # (kind, label, path)
    travel_cost: float = 0
    arrival_times: dict = field(default_factory=dict)
    traffic_tiles: int = 0
    risky_tiles: int = 0
    success: bool = True


@dataclass
class PlanReport:
    choice: ComboChoice
    compare_algorithm: str = ""
    truck_plans: dict = field(default_factory=dict)     # truck id -> TruckPlan
    fire_to_trucks: dict = field(default_factory=dict)  # fire id -> [truck ids]
    fire_order: list = field(default_factory=list)      # fire ids
    route_visited: list = field(default_factory=list)
    route_searches: list = field(default_factory=list)
    route_path_preview: list = field(default_factory=list)
    backup_paths: list = field(default_factory=list)
    dispatch_logs: list = field(default_factory=list)
    priority_logs: list = field(default_factory=list)
    route_logs: list = field(default_factory=list)
    risk_logs: list = field(default_factory=list)
    score: int = 0
    pass_score: int = 0
    benchmark_score: int = 0
    extinguished_count: int = 0
    total_fires: int = 0
    win: bool = False
    fail_reason: str = ""
    computation_nodes: int = 0
    total_travel_cost: float = 0
    planning_penalty: int = 0
    planning_runtime_ms: float = 0
    timed_out: bool = False

    def all_logs(self):
        out = []
        out.extend(["[ĐIỀU XE] " + x for x in self.dispatch_logs])
        out.extend(["[ƯU TIÊN] " + x for x in self.priority_logs])
        out.extend(["[ĐƯỜNG ĐI] " + x for x in self.route_logs])
        out.extend(["[RỦI RO] " + x for x in self.risk_logs])
        return out
