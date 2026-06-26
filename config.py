# config.py
# Code Red: AI Firetruck Commander
# Core game framework without required assets. Add PNGs later using assets/README.txt.

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_ROOT = os.path.join(BASE_DIR, "assets")

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800
FPS = 60
TITLE = "Mã Đỏ: Chỉ Huy Xe Cứu Hỏa AI"
FULLSCREEN = True

TILE_SIZE = 32
ROWS = 22
COLS = 28
MAP_WIDTH = COLS * TILE_SIZE
MAP_HEIGHT = ROWS * TILE_SIZE
PANEL_X = MAP_WIDTH
PANEL_WIDTH = SCREEN_WIDTH - MAP_WIDTH
PANEL_CONTENT_WIDTH = PANEL_WIDTH - 42
SHOW_LOT_MODELS = False

# Road/lane rendering. Vehicles use right-hand traffic:
# moving direction keeps to the right lane, opposite direction appears on the left side.
ROAD_LANE_OFFSET = 6
ROUTE_LINE_WIDTH = 2
ROUTE_LINE_OUTLINE_WIDTH = 4
ROUTE_SLOT_SPACING = 5
ROUTE_PARALLEL_SPACING = 7
ROUTE_LANE_COUNT = 8
ROUTE_DASH_LENGTH = 8
ROUTE_GAP_LENGTH = 6
TRUCK_RENDER_WIDTH = 18
TRUCK_RENDER_HEIGHT = 14
TRUCK_ASSET_SIZE = 22

STATE_MENU = "menu"
STATE_PLANNING = "planning"
STATE_EXECUTING = "executing"
STATE_RESULT = "result"

# Tiles
ROAD = "road"
BUILDING = "building"
BUILDING_1 = "building_1"
BUILDING_2 = "building_2"
BUILDING_3 = "building_3"
BUILDING_4 = "building_4"
BUILDING_5 = "building_5"
BUILDING_6 = "building_6"
HOSPITAL = "hospital"
GAS_STATION = "gas_station"
PARK = "park"
STATION = "station"
HYDRANT = "hydrant"
FIRE = "fire"
TRAFFIC = "traffic"
BLOCKED = "blocked"
RISKY = "risky"

NORMAL_BUILDINGS = [BUILDING_1, BUILDING_2, BUILDING_3, BUILDING_4, BUILDING_5, BUILDING_6]
BUILDING_TILES = NORMAL_BUILDINGS + [HOSPITAL, GAS_STATION, PARK]
WALKABLE_TILES = {ROAD, STATION, HYDRANT, TRAFFIC, RISKY}

# Colors
WHITE = (245, 245, 245)
BLACK = (10, 10, 10)
DARK_BG = (18, 18, 24)
PANEL_BG = (23, 23, 31)
CARD_BG = (35, 35, 46)
GRID_COLOR = (35, 35, 44)
TEXT_MUTED = (184, 184, 194)
SUCCESS = (82, 220, 132)
WARNING = (255, 174, 74)
DANGER = (255, 86, 64)
CYAN = (95, 216, 255)
PURPLE = (170, 130, 255)
YELLOW = (255, 235, 95)

ROAD_COLOR = (116, 116, 122)
BUILDING_COLOR = (55, 55, 78)
HOSPITAL_COLOR = (85, 105, 145)
GAS_COLOR = (125, 92, 55)
PARK_COLOR = (54, 92, 66)
STATION_COLOR = (30, 135, 240)
HYDRANT_COLOR = (40, 180, 230)
FIRE_COLOR = (255, 76, 34)
TRAFFIC_COLOR = (255, 190, 60)
BLOCKED_COLOR = (16, 16, 18)
RISKY_COLOR = (150, 100, 220)

VISITED_COLOR = (72, 145, 255)
PATH_COLOR = (72, 230, 130)
ALT_PATH_COLOR = (255, 205, 80)
TRUCK_COLORS = [
    (225, 38, 58),
    (245, 125, 40),
    (235, 215, 65),
    (90, 210, 255),
]

BUTTON_COLOR = (55, 55, 74)
BUTTON_HOVER = (82, 82, 110)
BUTTON_ACTIVE = (35, 120, 210)

TILE_COLORS = {
    ROAD: ROAD_COLOR,
    BUILDING: BUILDING_COLOR,
    BUILDING_1: BUILDING_COLOR,
    BUILDING_2: BUILDING_COLOR,
    BUILDING_3: BUILDING_COLOR,
    BUILDING_4: BUILDING_COLOR,
    BUILDING_5: BUILDING_COLOR,
    BUILDING_6: BUILDING_COLOR,
    HOSPITAL: HOSPITAL_COLOR,
    GAS_STATION: GAS_COLOR,
    PARK: PARK_COLOR,
    STATION: STATION_COLOR,
    HYDRANT: HYDRANT_COLOR,
    FIRE: FIRE_COLOR,
    TRAFFIC: TRAFFIC_COLOR,
    BLOCKED: BLOCKED_COLOR,
    RISKY: RISKY_COLOR,
}

TILE_COST = {
    ROAD: 1,
    STATION: 1,
    HYDRANT: 1,
    RISKY: 2,
    TRAFFIC: 5,
}

# Gameplay
PLANNING_SECONDS = 120
DEFAULT_TURN_LIMIT = 12
PASS_RATIO = 0.73
STAR_2_RATIO = 0.78
STAR_3_RATIO = 0.96
PERFECT_RATIO = 0.99

ON_TIME_BONUS = 60
LATE_TURN_PENALTY = 85
GAS_LATE_PENALTY = 250
HOSPITAL_LATE_PENALTY = 200
TRAVEL_COST_SCORE_PENALTY = 2.3
COMPUTATION_NODE_SCORE_DIVISOR = 22
TRAFFIC_TILE_SCORE_PENALTY = 11
RISKY_TILE_SCORE_PENALTY_AND_OR = 15
RISKY_TILE_SCORE_PENALTY_BELIEF = 7
MISSING_FIRE_SCORE_PENALTY = 420

# Algorithm groups: allowed by assignment list.
ROUTE_ALGORITHMS = ["BFS", "DFS", "UCS", "Greedy", "A*"]
PRIORITY_ALGORITHMS = [
    "Random Restart Hill Climbing",
    "Simulated Annealing",
    "Local Beam Search",
]
DISPATCH_ALGORITHMS = [
    "Backtracking Search",
    "Forward Checking",
    "AC3 Search",
]
RISK_ALGORITHMS = [
    "And-Or Search",
    "Belief State Search",
    "Minimax",
    "Alpha-Beta Pruning",
    "Expectimax",
]

EASY_ALGORITHMS = ROUTE_ALGORITHMS + PRIORITY_ALGORITHMS + DISPATCH_ALGORITHMS + RISK_ALGORITHMS

ALGORITHM_INFO = {
    "BFS": ("Đường đi", "Tìm đường ngắn nhất theo số ô. Hợp khi mọi đường có chi phí như nhau."),
    "DFS": ("Đường đi", "Đi sâu trước. Chạy nhanh nhưng không đảm bảo tối ưu."),
    "UCS": ("Đường đi", "Tìm đường rẻ nhất theo chi phí. Hợp với bản đồ nhiều kẹt xe."),
    "A*": ("Đường đi", "Dùng f(n)=g(n)+h(n). Cân bằng tốt giữa tốc độ và chất lượng."),
    "Greedy": ("Đường đi", "Ưu tiên ô có vẻ gần đích nhất. Nhanh nhưng dễ mắc kẹt."),
    "IDS": ("Đường đi", "DFS giới hạn độ sâu lặp lại. Dễ thấy quá trình tăng độ sâu."),

    "Simple Hill Climbing": ("Ưu tiên", "Cải thiện thứ tự cháy bằng hoán đổi tốt đầu tiên."),
    "Best Hill Climbing": ("Ưu tiên", "So toàn bộ hoán đổi lân cận và chọn bước tốt nhất."),
    "Stochastic Hill Climbing": ("Ưu tiên", "Chọn ngẫu nhiên một thứ tự tốt hơn."),
    "Random Restart Hill Climbing": ("Ưu tiên", "Thử nhiều điểm bắt đầu để tránh kẹt cục bộ."),
    "Simulated Annealing": ("Ưu tiên", "Có thể nhận bước tệ lúc đầu để thoát bẫy."),
    "Local Beam Search": ("Ưu tiên", "Giữ nhiều kế hoạch tốt cùng lúc."),

    "Backtracking Search": ("Điều xe", "Thử phân công xe cho đám cháy bằng đệ quy."),
    "Forward Checking": ("Điều xe", "Gán xe và kiểm tra sớm các lựa chọn còn lại."),
    "AC3 Search": ("Điều xe", "Thu hẹp miền lựa chọn bằng ràng buộc trước khi gán xe."),
    "Min Conflicts": ("Điều xe", "Sửa phân công đang xung đột bằng thay đổi cục bộ."),

    "And-Or Search": ("Rủi ro", "Lập phương án dự phòng cho đường rủi ro."),
    "Belief State Search": ("Rủi ro", "Ưu tiên tuyến an toàn khi đường có trạng thái chưa chắc chắn."),
    "Minimax": ("Rủi ro", "Chọn tuyến theo trường hợp xấu nhất của đường rủi ro và kẹt xe."),
    "Alpha-Beta Pruning": ("Rủi ro", "Minimax có cắt tỉa nhánh kém để tính nhanh hơn."),
    "Expectimax": ("Rủi ro", "Chọn tuyến theo kỳ vọng khi rủi ro có xác suất xảy ra."),
}

ALGORITHM_LABELS = {
    "BFS": "BFS",
    "DFS": "DFS",
    "UCS": "UCS",
    "A*": "A*",
    "Greedy": "Greedy",
    "IDS": "IDS",
    "Simple Hill Climbing": "Simple Hill Climbing",
    "Best Hill Climbing": "Best Hill Climbing",
    "Stochastic Hill Climbing": "Stochastic Hill Climbing",
    "Random Restart Hill Climbing": "Random Restart Hill Climbing",
    "Simulated Annealing": "Simulated Annealing",
    "Local Beam Search": "Local Beam Search",
    "Backtracking Search": "Backtracking",
    "Forward Checking": "Forwardcheck",
    "AC3 Search": "AC-3",
    "Min Conflicts": "Min Conflicts",
    "And-Or Search": "And-Or Search",
    "Belief State Search": "Belief State Search",
    "Minimax": "Minimax",
    "Alpha-Beta Pruning": "Alpha-Beta",
    "Expectimax": "Expectimax",
}

ALGORITHM_DETAILS = {
    "BFS": [
        "Xem bản đồ theo từng lớp từ xe cứu hỏa: ô gần được thử trước, ô xa thử sau.",
        "Điểm mạnh là tìm tuyến có ít ô nhất. Điểm yếu là không quan tâm kẹt xe hay rủi ro, nên chi phí có thể cao.",
        "Trong log, 'mở rộng' là số ô AI đã thử trước khi tới đám cháy.",
    ],
    "DFS": [
        "Đi thật sâu theo một nhánh trước khi quay lại thử nhánh khác.",
        "Điểm mạnh là đơn giản và chạy nhanh trên một số bản đồ. Điểm yếu là đường tìm được có thể vòng vèo, không tối ưu.",
        "Nếu điểm thấp, DFS thường là nguyên nhân vì xe đi xa hơn cần thiết.",
    ],
    "UCS": [
        "Luôn chọn nhánh có tổng chi phí đã đi thấp nhất.",
        "Kẹt xe bị tính chi phí cao, nên UCS thường tránh đường kẹt nếu có đường vòng rẻ hơn.",
        "Trong log, g(n) là tổng chi phí từ xe tới ô đang xét; g càng thấp càng tốt.",
    ],
    "A*": [
        "Kết hợp chi phí đã đi g(n) và khoảng cách ước lượng còn lại h(n).",
        "Điểm mạnh là cân bằng giữa nhanh và tốt, thường hợp nhất cho đường xe cứu hỏa.",
        "Trong log, f(n)=g(n)+h(n). AI ưu tiên ô có f thấp vì vừa gần, vừa ít tốn chi phí.",
    ],
    "Greedy": [
        "Chỉ nhìn ô nào có vẻ gần đích nhất theo h(n), rồi chạy về hướng đó.",
        "Điểm mạnh là nhanh. Điểm yếu là dễ lao vào kẹt xe hoặc đường rủi ro vì bỏ qua chi phí đã đi.",
        "Nếu tuyến ngắn nhưng điểm không cao, Greedy có thể đã chọn đường nhìn gần nhưng tốn chi phí.",
    ],
    "IDS": [
        "Chạy DFS nhiều lần với giới hạn độ sâu tăng dần: sâu 1, sâu 2, sâu 3...",
        "Điểm mạnh là kiểm soát bộ nhớ tốt và cho thấy quá trình tăng độ sâu. Điểm yếu là phải thử lại nhiều lần.",
        "Trong log, 'độ sâu' là số bước tối đa AI cho phép trước khi thử mức sâu hơn.",
    ],
    "Simple Hill Climbing": [
        "Bắt đầu từ một thứ tự dập cháy, sau đó đổi chỗ hai đám cháy nếu thấy tốt hơn.",
        "Nó nhận bước cải thiện đầu tiên nên khá nhanh, nhưng dễ kẹt ở phương án chỉ tốt cục bộ.",
        "Trong log, 'lân cận' là một thứ tự mới tạo bằng cách hoán đổi hai đám cháy.",
    ],
    "Best Hill Climbing": [
        "Thử nhiều hoán đổi lân cận rồi chọn hoán đổi tốt nhất trong vòng đó.",
        "Thường chắc hơn leo đồi đơn giản, nhưng tốn thêm thời gian vì phải so nhiều phương án.",
        "Trong log, 'chi phí tốt nhất' càng thấp thì thứ tự dập cháy càng hợp lý.",
    ],
    "Stochastic Hill Climbing": [
        "Tìm các thứ tự tốt hơn rồi chọn ngẫu nhiên một thứ tự trong số đó.",
        "Có tính ngẫu nhiên nên đôi khi thoát được đường mòn, nhưng kết quả có thể thay đổi giữa các lần chạy.",
        "Trong log, mỗi bước là một thứ tự mới được chọn vì tốt hơn thứ tự hiện tại.",
    ],
    "Random Restart Hill Climbing": [
        "Chạy leo đồi nhiều lần từ nhiều thứ tự ban đầu khác nhau.",
        "Điểm mạnh là giảm nguy cơ kẹt ở phương án xấu. Điểm yếu là kiểm thử nhiều lượt hơn.",
        "Trong log, 'khởi động' là một lần thử mới; AI giữ phương án tốt nhất toàn cục.",
    ],
    "Simulated Annealing": [
        "Giống leo đồi nhưng lúc đầu có thể nhận cả bước tệ hơn để thoát bẫy cục bộ.",
        "Khi nhiệt độ giảm, AI ngày càng khó chấp nhận bước tệ và ổn định về phương án tốt.",
        "Trong log, T là nhiệt độ; T cao nghĩa là AI còn đang khám phá mạnh.",
    ],
    "Local Beam Search": [
        "Giữ nhiều thứ tự dập cháy tốt cùng lúc thay vì chỉ giữ một thứ tự.",
        "Mỗi vòng tạo các phương án lân cận, rồi chỉ giữ lại vài phương án có chi phí thấp nhất.",
        "Trong log, các dòng 'chùm' là nhóm phương án đang được AI giữ để so sánh.",
    ],
    "Backtracking Search": [
        "Thử gán xe cho từng đám cháy bằng đệ quy; nếu lựa chọn không ổn thì quay lui để thử lựa chọn khác.",
        "Điểm mạnh là dễ hiểu và có thể tìm phân công tốt. Điểm yếu là có thể chậm nếu nhiều lựa chọn.",
        "Trong log, 'thiếu xe' hoặc 'phân công tốt hơn' cho biết nhánh hiện tại có dùng được không.",
    ],
    "Forward Checking": [
        "Sau khi gán xe cho một đám cháy, AI kiểm tra ngay các đám cháy còn lại còn xe hợp lệ không.",
        "Nó loại sớm lựa chọn xấu nên thường nhanh hơn quay lui thuần.",
        "Trong log, nếu một đám cháy 'không còn xe hợp lệ' thì AI biết nhánh đó cần bỏ.",
    ],
    "AC3 Search": [
        "Cắt bớt miền lựa chọn trước khi gán xe, dựa trên ràng buộc nước, tốc độ và loại xe.",
        "Nó giúp danh sách xe hợp lệ gọn hơn, nên bước phân công sau đó dễ và rõ hơn.",
        "Trong log, 'miền ban đầu' là các xe có thể chọn; 'miền cuối' là các xe còn lại sau khi lọc.",
    ],
    "Min Conflicts": [
        "Bắt đầu bằng một phân công tạm, sau đó sửa dần phần đang xung đột nhiều nhất.",
        "Phù hợp khi muốn có lời giải nhanh bằng cách chỉnh cục bộ, nhưng không đảm bảo tối ưu tuyệt đối.",
        "Trong log, 'xung đột' càng thấp thì phân công càng ít vi phạm yêu cầu.",
    ],
    "And-Or Search": [
        "Tạo kế hoạch chính và thêm tuyến dự phòng nếu đường rủi ro bị chặn.",
        "Nhánh OR là khi đường rủi ro dùng được. Nhánh AND là trường hợp xấu cần phương án thay thế.",
        "Trên bản đồ, tuyến dự phòng được vẽ nét đứt để phân biệt với đường xe đang chạy.",
    ],
    "Belief State Search": [
        "Xem đường rủi ro như trạng thái chưa chắc chắn: có thể mở, có thể bị chặn.",
        "AI phạt rủi ro cao hơn để ưu tiên đường an toàn, dù đường đó có thể dài hơn.",
        "Nếu điểm ổn định hơn nhưng chi phí đường cao hơn, đó là vì AI đang chọn phương án ít rủi ro.",
    ],
    "Minimax": [
        "Xem đường rủi ro như đối thủ luôn chọn tình huống xấu nhất cho xe cứu hỏa.",
        "AI chọn phương án có thiệt hại tối đa thấp nhất, nên thường tránh vùng nhiều '?' hoặc kẹt xe.",
        "Phù hợp khi muốn mô phỏng quyết định rất thận trọng trước các tình huống bất lợi.",
    ],
    "Alpha-Beta Pruning": [
        "Dùng cùng tư duy Minimax nhưng bỏ sớm các nhánh đã chắc chắn không thể tốt hơn.",
        "Kết quả vẫn thiên về phương án an toàn, nhưng log cho thấy quá trình cắt tỉa để giảm tính toán.",
        "Phù hợp khi muốn minh họa Minimax chạy hiệu quả hơn nhờ loại nhánh không cần xét.",
    ],
    "Expectimax": [
        "Xem rủi ro như sự kiện có xác suất thay vì luôn giả định tình huống xấu nhất.",
        "AI tính điểm kỳ vọng giữa đường mở, đường bị chặn, kẹt nhẹ và kẹt nặng.",
        "Phù hợp khi muốn phương án cân bằng hơn giữa tốc độ và độ an toàn.",
    ],
}

# Asset paths. If missing, game draws placeholder colors/symbols.
ASSET_PATHS = {
    ROAD: os.path.join(ASSET_ROOT, "roads", "road.png"),
    BUILDING_1: os.path.join(ASSET_ROOT, "buildings", "building_1.png"),
    BUILDING_2: os.path.join(ASSET_ROOT, "buildings", "building_2.png"),
    BUILDING_3: os.path.join(ASSET_ROOT, "buildings", "building_3.png"),
    BUILDING_4: os.path.join(ASSET_ROOT, "buildings", "building_4.png"),
    BUILDING_5: os.path.join(ASSET_ROOT, "buildings", "building_5.png"),
    BUILDING_6: os.path.join(ASSET_ROOT, "buildings", "building_6.png"),
    HOSPITAL: os.path.join(ASSET_ROOT, "buildings", "hospital.png"),
    GAS_STATION: os.path.join(ASSET_ROOT, "buildings", "gas_station.png"),
    PARK: os.path.join(ASSET_ROOT, "buildings", "park.png"),
    STATION: os.path.join(ASSET_ROOT, "buildings", "fire_station.png"),
    HYDRANT: os.path.join(ASSET_ROOT, "effects", "hydrant.png"),
    FIRE: os.path.join(ASSET_ROOT, "effects", "fire.png"),
    TRAFFIC: os.path.join(ASSET_ROOT, "effects", "traffic.png"),
    BLOCKED: os.path.join(ASSET_ROOT, "effects", "blocked.png"),
    RISKY: os.path.join(ASSET_ROOT, "effects", "risky_road.png"),
    "truck_1": os.path.join(ASSET_ROOT, "vehicles", "truck_1.png"),
    "truck_2": os.path.join(ASSET_ROOT, "vehicles", "truck_2.png"),
    "truck_3": os.path.join(ASSET_ROOT, "vehicles", "truck_3.png"),
    "start_bg": os.path.join(ASSET_ROOT, "ui", "start_bg.png"),
    "panel_bg": os.path.join(ASSET_ROOT, "ui", "panel_bg.png"),
}

TILE_ASSET_KEYS = set(ASSET_PATHS.keys()) - {"start_bg", "panel_bg"}
