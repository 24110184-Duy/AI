﻿Code Red: AI Firetruck Commander
================================

Concept:
Bạn là trung tâm điều phối xe cứu hỏa. Mỗi map có nhiều đám cháy xảy ra cùng lúc.
Bạn có thời gian lập kế hoạch giới hạn để chọn 4 nhóm thuật toán:

1. DISPATCH AI  - phân công xe cứu hỏa cho các đám cháy
2. PRIORITY AI  - chọn thứ tự ưu tiên xử lý nhiều đám cháy
3. ROUTE AI     - tìm đường cho xe cứu hỏa
4. RISK AI      - xử lý đường rủi ro / chưa chắc chắn

Game tự benchmark map bằng nhiều combo thuật toán mạnh.
Pass score = 50% điểm benchmark tốt nhất tìm được.
Bạn thắng nếu dập đủ đám cháy và điểm >= pass score.
Nếu không đủ điểm hoặc còn cháy chưa xử lý -> thua, retry hoặc leave.

Cài và chạy:
python -m pip install pygame
python main.py

Phím tắt:
SPACE = Execute plan
C     = Compare một số combo nhanh
1     = đổi Dispatch AI
2     = đổi Priority AI
3     = đổi Route AI
4     = đổi Risk AI
R     = random map mới
ESC   = menu / thoát về menu
F11   = bật/tắt fullscreen

18 thuật toán trong game:

Route AI:
- BFS
- DFS
- UCS
- A*
- Greedy
- IDS

Priority AI:
- Simple Hill Climbing
- Best Hill Climbing
- Stochastic Hill Climbing
- Random Restart Hill Climbing
- Simulated Annealing
- Local Beam Search

Dispatch AI:
- Backtracking Search
- Forward Checking
- AC3 Search
- Min Conflicts

Risk AI:
- And-Or Search
- Belief State Search

Asset:
Chưa cần asset vẫn chạy được bằng màu/symbol placeholder.
Sau này xem assets/README.txt để thêm PNG 32x32 đúng tên.
