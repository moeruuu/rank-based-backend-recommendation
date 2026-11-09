## 1. Mục đích và phạm vi
 
Dự án **rank-based-backend-recommendation** cần đề xuất backend lượng tử
phù hợp cho một quantum circuit. Bản mở rộng này dựa **trực tiếp** trên
các mạch và bảng calibration có trong repository được cung cấp; không
thay thế mã gốc.
 
Pipeline mới gồm:
 
```
10 quantum circuits (.qpy) ──────┐
                                 ├── Noise Simulation (AerSimulator.from_backend)
4 fake backends (calibration) ────┘         │
                                          ▼
                      noise_simulation_runs.csv (mỗi seed)
                                          │
                                          ▼
                      noise_simulation_summary.csv (mean/std)
                                          │
                                          ▼
                      ground_truth.csv (xếp hạng đo bằng simulation)
 
circuit_features.csv + calibration/*.csv
                  │
                  ▼
       baseline_predictions.csv (ước lượng từ calibration, độc lập labels)
                  │
                  └──────────┬────────── ground_truth.csv
                             ▼
                     ranking/evaluate.py
                             ▼
        ranking_metrics_per_circuit.csv + ranking_metrics_summary.csv
```
 
## 2. Dữ liệu đầu vào
 
-   `data/circuits/*.qpy`: GHZ_3/5, QFT_3/5, RANDOM_3/5 với seed
    42/100/202 (**10 circuits**).
-   `data/circuits/circuit_features.csv`: đặc trưng của từng mạch; mã
    `circuit_id` phải trùng stem file `.qpy`.
-   `data/calibration/backend_summary.csv`: backend, số qubit, coupling
    map, basis gates.
-   `data/calibration/qubit_calibration.csv`: T1, T2, readout error.
-   `data/calibration/gate_calibration.csv`: error của gate và duration.
-   Fake devices hiện có trong base: `fake_manila`, `fake_lima`,
    `fake_athens`, `fake_belem`, mỗi backend **5 qubit**.
**Nguồn noise:** simulator lấy mô hình noise bằng
`AerSimulator.from_backend(fake_backend)`; mô hình backend/calibration
được Qiskit Aer xây dựng từ dữ liệu fake backend, gồm lỗi gate, readout
và các thông số relaxation được hỗ trợ. **Không phải kết quả đo từ máy
IBM thật trong thời gian thực**. CSV calibration còn được dùng cho
baseline độc lập.
 
## 3. Phần công việc Member 1 -- Backend Calibration và Quantum Circuit Dataset
 
Member 1 phụ trách chuẩn bị dữ liệu đầu vào cho toàn bộ pipeline: thu
thập thông số calibration từ bốn fake backends, tạo bộ quantum circuits,
trích xuất đặc trưng mạch và lưu mạch ở định dạng QPY để các thành viên
khác có thể tái sử dụng.
 
### 3.1. Kiểm tra và lựa chọn fake backends
 
Dự án sử dụng bốn backend giả lập có sẵn trong `qiskit-ibm-runtime`:
 
| Backend | Số qubit | Đặc điểm topology |
|---------|---------:|-------------------|
| `fake_manila` | 5 | Coupling map dạng tuyến tính |
| `fake_lima` | 5 | Coupling map có nhánh |
| `fake_athens` | 5 | Coupling map dạng tuyến tính |
| `fake_belem` | 5 | Coupling map có nhánh |
 
Các backend được khởi tạo trực tiếp từ các lớp fake provider, không cần
tải riêng thiết bị hoặc calibration file từ IBM Quantum. Mục đích của
bước kiểm tra là xác nhận có thể import backend, đọc số qubit, basis
gates và coupling map trước khi thu thập dữ liệu.
 
Ví dụ import:
 
```python
from qiskit_ibm_runtime.fake_provider import (
    FakeManilaV2,
    FakeLimaV2,
    FakeAthensV2,
    FakeBelemV2,
)
 
backends = {
    "fake_manila": FakeManilaV2(),
    "fake_lima": FakeLimaV2(),
    "fake_athens": FakeAthensV2(),
    "fake_belem": FakeBelemV2(),
}
```
 
### 3.2. Thu thập backend calibration
 
Mã thu thập calibration nằm trong
`src/calibration/collect_calibration.py`. Thông tin được đọc từ cấu hình
backend (`backend.target`) và thuộc tính qubit mà Qiskit cung cấp.
 
Dữ liệu được xuất thành ba tệp:
 
| Tệp | Nội dung |
|-----|----------|
| `data/calibration/backend_summary.csv` | Tên backend, số qubit, coupling map và basis gates |
| `data/calibration/qubit_calibration.csv` | Thông số từng qubit như T1, T2 và readout error |
| `data/calibration/gate_calibration.csv` | Gate, qubit liên quan, gate error và duration nếu backend cung cấp |
 
Ý nghĩa các thông số chính:
 
-   **T1:** thời gian thư giãn năng lượng của qubit.
-   **T2:** thời gian mất coherence/pha của qubit.
-   **Readout error:** xác suất phép đo đọc sai trạng thái qubit.
-   **Gate error:** mức lỗi được mô tả cho một phép toán lượng tử trên
    backend.
-   **Gate duration:** thời gian thực thi gate nếu thông tin này có
    trong calibration.
Các giá trị được thu thập từ fake backend snapshot, không phải dữ liệu
calibration trực tiếp theo thời gian thực của máy lượng tử IBM. Một số
trường có thể không được backend cung cấp; khi đó cần giữ giá trị thiếu
thay vì tự gán một giá trị giả.
 
### 3.3. Tạo bộ quantum circuits
 
Các hàm tạo mạch được tổ chức trong `src/circuits/`:
 
-   `ghz.py`: tạo mạch GHZ.
-   `qft.py`: tạo mạch Quantum Fourier Transform.
-   `random_circuit.py`: tạo mạch ngẫu nhiên có seed cố định.
Bộ dữ liệu gồm 10 mạch:
 
| Circuit ID | Loại mạch | Số qubit | Cấu hình |
|------------|-----------|---------:|----------|
| `GHZ_3` | GHZ | 3 | 3 qubit |
| `GHZ_5` | GHZ | 5 | 5 qubit |
| `QFT_3` | QFT | 3 | 3 qubit |
| `QFT_5` | QFT | 5 | 5 qubit |
| `RANDOM_3_42` | Random | 3 | Seed 42 |
| `RANDOM_3_100` | Random | 3 | Seed 100 |
| `RANDOM_3_202` | Random | 3 | Seed 202 |
| `RANDOM_5_42` | Random | 5 | Seed 42 |
| `RANDOM_5_100` | Random | 5 | Seed 100 |
| `RANDOM_5_202` | Random | 5 | Seed 202 |
 
**GHZ circuit:** áp dụng Hadamard lên qubit đầu tiên, sau đó dùng các
cổng CNOT nối tuần tự các qubit để tạo trạng thái liên đới GHZ.
 
**QFT circuit:** sử dụng Hadamard và controlled-phase (`cp`) theo từng
cặp qubit, sau đó hoán đổi các qubit đối xứng để hoàn thành thứ tự đầu
ra theo cách cài đặt của dự án.
 
**Random circuit:** sử dụng `qiskit.circuit.random.random_circuit`, với
số qubit, độ sâu và seed được chỉ định. Seed cố định giúp tái tạo cùng
một mạch khi chạy lại hoặc khi các thành viên khác cần sử dụng dữ liệu.
 
Các mạch được tạo chưa gắn measurement ở bước lưu QPY. Measurement được
thêm trong bước noise simulation để có thể tính phân phối kết quả đo.
 
### 3.4. Trích xuất đặc trưng circuit
 
File `src/circuits/extract_features.py` đọc/tạo các mạch và trích xuất
thông tin để tạo `data/circuits/circuit_features.csv`.
 
Các trường đặc trưng gồm:
 
| Trường | Ý nghĩa |
|--------|---------|
| `circuit_id` | Mã định danh duy nhất của circuit |
| `circuit_type` | Loại mạch: GHZ, QFT hoặc RANDOM |
| `num_qubits` | Số qubit logic |
| `depth` | Độ sâu mạch theo Qiskit |
| `num_gates` | Tổng số gate được tính, không bao gồm barrier, measure và delay |
| `single_qubit_gates` | Số gate một qubit |
| `two_qubit_gates` | Số gate hai qubit |
| `h_count`, `cx_count`, `cp_count`, `swap_count` | Số lần xuất hiện của các gate tương ứng |
| `gate_composition` | Phân bố các loại gate, lưu dưới dạng JSON string |
| `random_seed` | Seed đối với random circuit; để trống với mạch không ngẫu nhiên |
 
Các đặc trưng này mô tả độ phức tạp và thành phần gate của mạch. Chúng
được dùng làm đầu vào cho baseline và các mô hình ranking ở những phần
tiếp theo. `circuit_id` phải trùng với tên file QPY tương ứng để ghép dữ
liệu chính xác.
 
### 3.5. Lưu và chia sẻ circuit bằng QPY
 
File `src/circuits/save_circuits.py` lưu từng circuit thành một tệp
`.qpy` trong `data/circuits/`, ví dụ `GHZ_3.qpy` hoặc `QFT_5.qpy`.
 
QPY là định dạng tuần tự hóa của Qiskit, giúp lưu cấu trúc circuit để
thành viên khác có thể nạp lại mà không cần tự viết lại hàm tạo mạch. Ví
dụ:
 
```python
from qiskit import qpy
 
with open("data/circuits/GHZ_3.qpy", "rb") as file:
    circuit = qpy.load(file)[0]
```
 
Khi chia sẻ repository, nhóm cần commit mã nguồn tạo mạch, file đặc
trưng CSV và các file QPY cần thiết. Không cần tải hoặc commit riêng các
lớp fake backend từ IBM vì chúng được cung cấp thông qua package
`qiskit-ibm-runtime`.
 
### 3.6. Kiểm tra tính nhất quán và bàn giao
 
Trước khi bàn giao dữ liệu cho các thành viên khác, cần kiểm tra:
 
1.  Có đủ 4 backend và mỗi backend có 5 qubit.
2.  Ba CSV calibration có đúng tên và nằm trong `data/calibration/`.
3.  Có đủ 10 file `.qpy` và tên file khớp với `circuit_id`.
4.  `circuit_features.csv` có 10 dòng dữ liệu tương ứng với 10 circuit.
5.  Có thể nạp lại ít nhất một file QPY và đọc được `num_qubits`,
    `depth` và `count_ops()`.
Các artifact của Member 1 là đầu vào cho noise simulation, baseline và
ranking evaluation. Vì vậy, cần giữ thống nhất tên backend,
`circuit_id`, cấu trúc thư mục và phiên bản Qiskit giữa các thành viên.
 
## 4. Phần công việc Member 2 -- Baseline Models và Backend Ranking
 
> **Member 2 điền phần này.** Thay các nội dung trong dấu `[Điền ...]`
> bằng thông tin đúng với code và kết quả thực tế. Nếu một chức năng
> chưa hoàn thành, ghi rõ `Chưa triển khai` hoặc `Chưa kiểm thử`; không
> ghi kết quả dự kiến như kết quả thực nghiệm.
>
> Mô tả kỹ thuật chung của baseline độc lập hiện có xem ở mục 9.
 
### 4.1. Mục tiêu và phạm vi
 
Member 2 phụ trách xây dựng các phương pháp dự đoán điểm backend và xếp
hạng backend cho từng quantum circuit, dựa trên calibration data và
circuit features do Member 1 bàn giao.
 
**Phạm vi thực hiện:**
[Điền các chức năng Member 2 thực sự phụ trách.]
 
### 4.2. Dữ liệu đầu vào
 
| Tệp dữ liệu | Mục đích sử dụng | Trạng thái |
|-------------|------------------|------------|
| `data/calibration/backend_summary.csv` | Thông tin tổng quan backend | [Đã dùng/Chưa dùng/Ghi chú] |
| `data/calibration/qubit_calibration.csv` | Thông số calibration từng qubit | [Đã dùng/Chưa dùng/Ghi chú] |
| `data/calibration/gate_calibration.csv` | Gate error và duration | [Đã dùng/Chưa dùng/Ghi chú] |
| `data/circuits/circuit_features.csv` | Đặc trưng của từng circuit | [Đã dùng/Chưa dùng/Ghi chú] |
| `data/results/ground_truth.csv` | Nhãn đánh giá từ simulation | [Có dùng hay không; giải thích] |
 
### 4.3. Baseline A -- Gate và Readout Error
 
-   **File triển khai:**
    `[Điền đường dẫn file, ví dụ src/ranking/baseline.py]`
-   **Ý tưởng:** [Mô tả cách tính điểm.]
-   **Công thức:** [Điền công thức đúng theo code.]
-   **Các feature sử dụng:** [Điền feature thực tế.]
-   **Cách chuyển score thành ranking:** [Điền quy tắc sắp xếp và xử lý
    trường hợp bằng điểm.]
### 4.4. Baseline B -- EPLG-like / Circuit-aware Baseline
 
-   **File triển khai:** `[Điền đường dẫn file]`
-   **Ý tưởng:** [Giải thích cách baseline xem xét cấu trúc/layer của
    circuit.]
-   **Công thức hoặc thuật toán:** [Điền công thức/diễn giải từng
    bước.]
-   **Các thông số calibration sử dụng:** [Điền các trường thực tế.]
-   **Điểm khác biệt so với Baseline A:** [Điền phần khác biệt.]
### 4.5. Model C -- Machine Learning (Random Forest)
 
-   **File triển khai:** `[Điền đường dẫn file]`
-   **Thư viện và phiên bản:**
    `[Điền scikit-learn và phiên bản thực tế]`
-   **Input features:** [Liệt kê feature circuit và backend được đưa
    vào model.]
-   **Target/label:** [Nêu rõ model dự đoán score, fidelity, rank hay
    nhãn nào.]
-   **Cách chia train/test:** [Điền cách chia dữ liệu, random state và
    lý do.]
-   **Các tham số Random Forest:** [Điền n_estimators, max_depth và các
    tham số đã cấu hình.]
-   **Cách tạo ranking:** [Mô tả cách chuyển prediction thành thứ hạng
    backend.]
### 4.6. Kết quả và kiểm thử
 
| Nội dung kiểm tra | Kết quả thực tế | Bằng chứng / tệp output |
|-------------------|-----------------|-------------------------|
| Baseline A chạy thành công | [Điền] | [Điền] |
| Baseline B chạy thành công | [Điền] | [Điền] |
| Random Forest chạy thành công | [Điền] | [Điền] |
| Tạo ranking cho mỗi circuit | [Điền] | [Điền] |
| Xử lý missing/invalid data | [Điền] | [Điền] |
 
**Nhận xét:**
[So sánh sơ bộ ba phương pháp. Chỉ nhận xét dựa trên kết quả đã chạy.]
 
### 4.7. Artifact bàn giao
 
| Tệp | Nội dung | Trạng thái |
|-----|----------|------------|
| `[Điền file]` | [Mô tả] | [Hoàn thành/Chưa hoàn thành] |
| `[Điền file]` | [Mô tả] | [Hoàn thành/Chưa hoàn thành] |
 
### 4.8. Giới hạn và hướng cải thiện
 
[Điền các giả định, hạn chế của baseline/model, vấn đề dữ liệu hoặc
hướng cải thiện.]
 
## 5. Phần công việc Member 3 -- Noise Simulation, Ground Truth và Ranking Evaluation
 
> **Member 3 điền phần này.** Nội dung bên dưới là khung báo cáo. Cần
> xác nhận theo implementation và kết quả chạy thực tế trước khi hoàn
> thiện. Mô tả kỹ thuật chung xem ở các mục 7, 8 và 10.
 
### 5.1. Mục tiêu và phạm vi
 
Member 3 phụ trách mô phỏng ảnh hưởng của noise lên quantum circuits,
tạo simulation-derived ground truth và đánh giá chất lượng thứ hạng
backend.
 
**Phạm vi thực hiện:**
[Điền các chức năng Member 3 thực sự phụ trách.]
 
### 5.2. Noise Simulation
 
-   **File triển khai:**
    `[Điền đường dẫn file, ví dụ src/simulation/noise.py]`
-   **Simulator:** `[Điền simulator và phiên bản thực tế]`
-   **Backend noise model:** [Giải thích cách lấy noise model từ fake
    backend.]
-   **Circuit input:** [Nêu cách đọc QPY và thêm measurement.]
-   **Cấu hình mô phỏng:** [Điền shots, seeds, optimization level,
    transpiler seed.]
-   **Chỉ số tính toán:** [Nêu fidelity/TVD hoặc các chỉ số thực sự
    được code tính.]
-   **Cách lưu kết quả:** [Điền tên CSV và các cột quan trọng.]
### 5.3. Ground Truth Generation
 
-   **File triển khai:**
    `[Điền đường dẫn file, ví dụ src/ranking/ground_truth.py]`
-   **Định nghĩa ground truth:** [Giải thích ground truth được suy ra
    từ kết quả mô phỏng như thế nào.]
-   **Tiêu chí sắp xếp backend:** [Điền metric chính, chiều sắp xếp và
    quy tắc tie-break.]
-   **Relevance/label:** [Giải thích giá trị được dùng làm relevance
    hoặc label.]
-   **Lưu ý:** Nêu rõ đây là ground truth từ mô phỏng hay từ phần cứng
    thật; không gọi kết quả mô phỏng là số đo hardware thật.
### 5.4. Ranking Evaluation Metrics
 
-   **File triển khai:** `[Điền đường dẫn file metrics/evaluate]`
| Metric | Ý nghĩa trong project | Kết quả / ghi chú |
|--------|-----------------------|-------------------|
| Spearman correlation | [Điền cách diễn giải] | [Điền] |
| Kendall tau | [Điền cách diễn giải] | [Điền] |
| Top-1 accuracy | [Điền cách diễn giải] | [Điền] |
| Top-2 hit | [Điền cách diễn giải] | [Điền] |
| Precision@2 | [Điền cách diễn giải] | [Điền] |
| MRR | [Điền cách diễn giải] | [Điền] |
| NDCG@2 | [Điền cách diễn giải] | [Điền] |
| NDCG@all | [Điền cách diễn giải] | [Điền] |
 
**Cách đánh giá:**
[Điền cách ghép predicted ranking với ground-truth ranking, cách xử lý
thiếu backend/tie và cách tính trung bình.]
 
### 5.5. Pipeline và cách chạy
 
**Lệnh chạy:**
 
```bash
[Điền lệnh chạy thực tế từ thư mục gốc repository]
```
 
**Thứ tự thực thi:**
 
1.  [Điền bước đầu tiên.]
2.  [Điền bước tiếp theo.]
3.  [Điền bước tạo ground truth.]
4.  [Điền bước đánh giá ranking.]
### 5.6. Kết quả thực nghiệm
 
| Tệp output | Nội dung | Trạng thái |
|------------|----------|------------|
| `data/results/noise_simulation_runs.csv` | [Điền nội dung thực tế] | [Đã tạo/Chưa tạo] |
| `data/results/noise_simulation_summary.csv` | [Điền nội dung thực tế] | [Đã tạo/Chưa tạo] |
| `data/results/ground_truth.csv` | [Điền nội dung thực tế] | [Đã tạo/Chưa tạo] |
| `data/results/ranking_metrics_per_circuit.csv` | [Điền nội dung thực tế] | [Đã tạo/Chưa tạo] |
| `data/results/ranking_metrics_summary.csv` | [Điền nội dung thực tế] | [Đã tạo/Chưa tạo] |
 
**Kết quả nổi bật:**
[Điền số liệu thực tế, backend đứng đầu theo từng circuit hoặc metric
tổng hợp. Nếu chưa chạy được, ghi rõ nguyên nhân.]
 
**Nhận xét:**
[Phân tích kết quả, độ ổn định giữa các seeds, ảnh hưởng của shots và
các trường hợp ranking khác nhau.]
 
### 5.7. Kiểm thử và xác minh
 
| Kiểm thử | Kết quả thực tế | Ghi chú |
|----------|-----------------|---------|
| Unit tests | [PASS/FAIL/SKIP] | [Điền] |
| Qiskit integration tests | [PASS/FAIL/SKIP] | [Điền] |
| Simulation chạy với đủ backend | [Điền] | [Điền] |
| Ground truth có đủ circuit/backend | [Điền] | [Điền] |
| Ranking metrics được tính | [Điền] | [Điền] |
 
### 5.8. Giới hạn và hướng cải thiện
 
[Điền giới hạn của noise model, shot noise, fake backend calibration
snapshot, measurement basis, runtime và hướng cải thiện.]
 
## 6. Chạy dự án
 
Đứng tại **thư mục gốc** repo (nơi có `src`, `data`, `scripts`). Dùng
Python 3.11 theo `enviroment.yaml` của dự án.
 
```bash
python -m venv .venv
source .venv/bin/activate            # macOS/Linux
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install numpy pandas scipy 'qiskit>=2,<3' 'qiskit-aer>=0.15' 'qiskit-ibm-runtime>=0.35'
python -m unittest discover -s tests -v
python -m scripts.run_pipeline --shots 4096 --seeds 42 100 202 --optimization-level 1
```
 
**Quan trọng:** File `requirements.txt` gốc là UTF-16 (không phải
UTF-8), và bản dependency hiện có có thể không đồng bộ với Qiskit Aer.
Khuyến nghị dùng các lệnh cài tối thiểu bên trên hoặc chuẩn hóa riêng
dependency khi tích hợp CI. Việc import fake backend thuộc phiên bản
`qiskit_ibm_runtime` tương thích; nếu các lớp fake backend bị loại bỏ
trong bản tương lai, cần cập nhật provider tương ứng và kiểm chứng lại
mô hình nhiễu.
 
**Kết quả chạy mô phỏng phụ thuộc môi trường/Qiskit:** Có thể thay số
shots và seeds, nhưng phải giữ cấu hình giữa các backend khi so sánh.
 
## 7. Noise Simulation
 
File: `src/simulation/noise.py`.
 
Với mỗi `(circuit_id, backend_name)`:
 
1.  Đọc mạch QPY, tính phân phối xác suất đo lý tưởng `p(x)` bằng
    `Statevector.from_instruction` (trước measurement).
2.  Sao chép circuit, thêm đo tất cả qubit logic, `transpile` theo
    topology, basis gates của backend với `optimization_level` và
    `seed_transpiler=42`.
3.  Tạo `AerSimulator.from_backend(backend)` để áp dụng noise từ fake
    backend.
4.  Chạy nhiều lần với `seed_simulator` khác nhau, mỗi lần `shots=4096`
    mặc định, lấy `counts` và chuẩn hóa thành phân phối quan sát `q(x)`.
5.  Tính độ tương đồng phân phối (classical distribution fidelity), TVD,
    lưu cả counts gốc và thống kê mean/std.
Công thức:
 
-   **Distribution fidelity**: `F(p,q) = (Σ_x sqrt(p(x) q(x)))²` (0..1;
    **không phải** quantum state fidelity).
-   **Total variation distance**: `TVD(p,q) = 1/2 Σ_x |p(x)-q(x)|`
    (0..1, càng thấp càng tốt).
Lưu ý: chỉ số dựa trên phân phối đo ở computational basis; nó không đo
được đầy đủ sự khác biệt quantum phase/coherence. Với mạch QFT cụ thể,
distribution fidelity vẫn là một proxy thực nghiệm, không thay cho
state/process fidelity. Circuit có gate count nhiều, topology không khớp
có thể cần SWAP và noise cao hơn.
 
**Shot noise:** kết quả đo hữu hạn shots có sai số thống kê; ngay cả mô
phỏng lý tưởng cũng có thể có `F < 1`. Nên dùng nhiều seeds và phân tích
CI khi đánh giá chính thức. Cùng số shots, seeds, optimization level
được dùng cho tất cả backend.
 
## 8. Ground Truth
 
File: `src/ranking/ground_truth.py`.
 
Ground truth **không** được định nghĩa bằng calibration heuristic hoặc
label sinh từ thuật toán dự đoán. Nó lấy từ kết quả simulation độc lập:
đối với mỗi circuit, xếp backend theo `mean_fidelity` **giảm dần**, nếu
hòa theo `mean_tvd` **tăng dần**, sau cùng theo `backend_name` (đảm bảo
reproducible). Gán `ground_truth_rank = 1..N`.
`ground_truth_relevance = mean_fidelity` để NDCG dùng được relevance
liên tục.
 
Đây là **simulation-derived proxy ground truth**, không phải ground
truth đo trên hardware thực. Các backend có fidelity cực sát nhau có thể
hoán đổi vị trí do shot noise; khi báo cáo học thuật nên kiểm tra khoảng
tin cậy hoặc độ ổn định thứ hạng.
 
## 9. Baseline độc lập
 
File: `src/ranking/baseline.py`.
 
Baseline từ **đặc trưng mạch + trung bình calibration**, không đọc kết
quả mô phỏng/nhãn:
 
`predicted_score = (1 - e_1)^n_1 × (1 - e_2)^n_2 × (1 - e_readout)^n_qubits`
 
Trong đó `e_1`, `e_2` là gate error trung bình của gate 1/2 qubit,
`e_readout` là readout error trung bình của backend; `n_1`, `n_2` lấy từ
mạch gốc. Điểm cao hơn xếp hạng cao hơn. Đây là baseline **rất đơn
giản**; chưa tính SWAP bổ sung do routing, thời lượng gate, decoherence
cụ thể từng qubit hoặc mapping layout thực, nên không coi đây là mô hình
vật lý chính xác.
 
## 10. Ranking metrics
 
File: `src/ranking/metrics.py`, `src/ranking/evaluate.py`.
 
Đánh giá **trên từng circuit**, so sánh danh sách backend dự đoán với
danh sách ground truth, sau đó lấy trung bình không trọng số qua các
circuit (macro-average). Các cột:
 
| Metric | Diễn giải | Tốt nhất |
|--------|-----------|---------:|
| `spearman_rho` | Tương quan thứ hạng (hoàn toàn đảo ngược = -1) | 1 |
| `kendall_tau` | Tỷ lệ cặp backend đồng thuận trừ bất đồng | 1 |
| `top1_accuracy` | Backend ground-truth tốt nhất có đứng vị trí 1 không | 1 |
| `top2_hit` | Backend ground-truth tốt nhất có xuất hiện trong 2 gợi ý đầu | 1 |
| `precision_at_2` | Tỷ lệ giao nhau giữa top-2 dự đoán và top-2 ground truth | 1 |
| `mrr` | Nghịch đảo vị trí của backend tốt nhất thật sự | 1 |
| `ndcg_at_2` | NDCG@2 dùng fidelity làm relevance | 1 |
| `ndcg_at_all` | NDCG toàn bộ danh sách backend | 1 |
 
Định nghĩa `top2_hit` **khác** `precision_at_2`; danh sách ít hơn 2
backend thì tính `min(2,N)`. NDCG dùng gain `2^relevance - 1` và
discount `log2(rank+1)`. Với relevance rất gần nhau, NDCG có thể cao
ngay cả khi thứ hạng sai; nên báo cáo kèm Spearman/Kendall/Top1.
 
Các hàm có validation: thiếu backend, thừa backend, lặp tên, ranks không
liên tiếp, missing relevance → lỗi rõ ràng; không tự bỏ dòng và làm méo
kết quả.
 
## 11. Artifact / output
 
| Tệp | Nội dung |
|-----|----------|
| `data/results/noise_simulation_runs.csv` | Từng `(circuit, backend, seed)` với shots, fidelity, TVD, counts |
| `data/results/noise_simulation_summary.csv` | Fidelity mean/std, mean TVD và số runs |
| `data/results/ground_truth.csv` | Rank và relevance đo theo noisy simulation |
| `data/results/baseline_predictions.csv` | Điểm/rank ước lượng không dùng nhãn |
| `data/results/ranking_metrics_per_circuit.csv` | Metrics mỗi circuit |
| `data/results/ranking_metrics_summary.csv` | Macro-average metrics trên tất cả circuit |
 
Không tự tạo file GT/metrics từ dữ liệu giả trước khi simulation chạy
thành công. `baseline_predictions.csv` có thể chạy riêng không cần
Qiskit nếu đã có 3 CSV calibration và `circuit_features.csv`.
 
## 12. Kiểm thử và tình trạng thực thi
 
-   Test thuần Python: `python -m unittest tests.test_ranking -v`.
-   Test tích hợp Qiskit:
    `python -m unittest tests.test_qiskit_integration -v`; tự **SKIP**
    nếu thiếu thư viện, không coi là PASS.
-   Trong môi trường tạo bản bàn giao,
    `qiskit`/`qiskit_aer`/`qiskit_ibm_runtime` **chưa được cài** do môi
    trường không truy cập package index; vì vậy **chưa có số liệu noisy
    simulation hoặc ranking metrics thực nghiệm thật**.
-   `baseline_predictions.csv` được tính **thật** từ CSV calibration của
    ZIP, tách biệt với ground truth.
## 13. Giới hạn và bước mở rộng
 
1.  **Measurement-only proxy:** bổ sung nhiều measurement bases /
    observables nếu đánh giá độ trung thực quantum đầy đủ.
2.  **Statistical stability:** tăng shots, seeds; bootstrap CI và kiểm
    tra khi 2 backend gần như đồng hạng.
3.  **Calibration drift:** fake backend snapshots không mô tả chính xác
    hardware live; ghi timestamp/version trong báo cáo thí nghiệm.
4.  **Prediction quality:** mở rộng baseline thành ranking model học có
    giám sát với circuit-level train/test split, tránh data leakage bằng
    cách tách toàn bộ circuit family nếu cần đánh giá
    out-of-distribution.
5.  **Architecture:** mô phỏng có thể rất nặng khi tăng số circuit, số
    seed, shots; cần cache, logging, và batch/parallel có kiểm soát.
## 14. Tổng kết đóng góp và tích hợp giữa các thành viên
 
| Thành viên | Phụ trách | Artifact bàn giao chính | Trạng thái |
|------------|-----------|-------------------------|------------|
| Member 1 (mục 3) | Backend calibration và circuit dataset | Calibration CSV, circuit QPY, `circuit_features.csv` | [Điền] |
| Member 2 (mục 4) | Baseline A/B, Random Forest và predicted ranking | [Điền các file output] | [Điền] |
| Member 3 (mục 5) | Noise simulation, ground truth và ranking evaluation | [Điền các file output] | [Điền] |
 
### 14.1. Luồng tích hợp
 
[Điền cách các thành viên ghép module, dữ liệu đầu vào/đầu ra, tên
branch hoặc pull request nếu có.]
 
### 14.2. Cách tái tạo kết quả cuối cùng
 
```bash
[Điền các lệnh cài đặt môi trường]
[Điền lệnh chạy test]
[Điền lệnh chạy pipeline hoàn chỉnh]
```
 
### 14.3. Tình trạng hoàn thành tại thời điểm nộp
 
-   **Đã hoàn thành:** [Liệt kê chức năng đã chạy và có bằng chứng.]
-   **Chưa hoàn thành:** [Liệt kê chức năng còn thiếu.]
-   **Vấn đề đã gặp và cách xử lý:** [Điền.]
-   **Hướng phát triển tiếp theo:** [Điền.]