# Technical Docs – Noise Simulation, Ground Truth & Ranking Metrics

## 1. Mục đích và phạm vi

Dự án **rank-based-backend-recommendation** cần đề xuất backend lượng tử phù hợp cho một quantum circuit. Bản mở rộng này dựa **trực tiếp** trên các mạch và bảng calibration có trong repository được cung cấp; không thay thế mã gốc.

Pipeline mới gồm:

```text
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

- `data/circuits/*.qpy`: GHZ_3/5, QFT_3/5, RANDOM_3/5 với seed 42/100/202 (**10 circuits**).
- `data/circuits/circuit_features.csv`: đặc trưng của từng mạch; mã `circuit_id` phải trùng stem file `.qpy`.
- `data/calibration/backend_summary.csv`: backend, số qubit, coupling map, basis gates.
- `data/calibration/qubit_calibration.csv`: T1, T2, readout error.
- `data/calibration/gate_calibration.csv`: error của gate và duration.
- Fake devices hiện có trong base: `fake_manila`, `fake_lima`, `fake_athens`, `fake_belem`, mỗi backend **5 qubit**.

**Nguồn noise:** simulator lấy mô hình noise bằng `AerSimulator.from_backend(fake_backend)`; mô hình backend/calibration được Qiskit Aer xây dựng từ dữ liệu fake backend, gồm lỗi gate, readout và các thông số relaxation được hỗ trợ. **Không phải kết quả đo từ máy IBM thật trong thời gian thực**. CSV calibration còn được dùng cho baseline độc lập.

## 3. Chạy dự án

Đứng tại **thư mục gốc** repo (nơi có `src`, `data`, `scripts`). Dùng Python 3.11 theo `enviroment.yaml` của dự án.

```bash
python -m venv .venv
source .venv/bin/activate            # macOS/Linux
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install -U pip
python -m pip install numpy pandas scipy 'qiskit>=2,<3' 'qiskit-aer>=0.15' 'qiskit-ibm-runtime>=0.35'
python -m unittest discover -s tests -v
python -m scripts.run_pipeline --shots 4096 --seeds 42 100 202 --optimization-level 1
```

**Quan trọng:** File `requirements.txt` gốc là UTF-16 (không phải UTF-8), và bản dependency hiện có có thể không đồng bộ với Qiskit Aer. Khuyến nghị dùng các lệnh cài tối thiểu bên trên hoặc chuẩn hóa riêng dependency khi tích hợp CI. Việc import fake backend thuộc phiên bản `qiskit_ibm_runtime` tương thích; nếu các lớp fake backend bị loại bỏ trong bản tương lai, cần cập nhật provider tương ứng và kiểm chứng lại mô hình nhiễu.

**Kết quả chạy mô phỏng phụ thuộc môi trường/Qiskit:** Có thể thay số shots và seeds, nhưng phải giữ cấu hình giữa các backend khi so sánh.

## 4. Noise Simulation

File: `src/simulation/noise.py`.

Với mỗi `(circuit_id, backend_name)`:

1. Đọc mạch QPY, tính phân phối xác suất đo lý tưởng `p(x)` bằng `Statevector.from_instruction` (trước measurement).
2. Sao chép circuit, thêm đo tất cả qubit logic, `transpile` theo topology, basis gates của backend với `optimization_level` và `seed_transpiler=42`.
3. Tạo `AerSimulator.from_backend(backend)` để áp dụng noise từ fake backend.
4. Chạy nhiều lần với `seed_simulator` khác nhau, mỗi lần `shots=4096` mặc định, lấy `counts` và chuẩn hóa thành phân phối quan sát `q(x)`.
5. Tính độ tương đồng phân phối (classical distribution fidelity), TVD, lưu cả counts gốc và thống kê mean/std.

Công thức:

- **Distribution fidelity**: `F(p,q) = (Σ_x sqrt(p(x) q(x)))²` (0..1; **không phải** quantum state fidelity).
- **Total variation distance**: `TVD(p,q) = 1/2 Σ_x |p(x)-q(x)|` (0..1, càng thấp càng tốt).

Lưu ý: chỉ số dựa trên phân phối đo ở computational basis; nó không đo được đầy đủ sự khác biệt quantum phase/coherence. Với mạch QFT cụ thể, distribution fidelity vẫn là một proxy thực nghiệm, không thay cho state/process fidelity. Circuit có gate count nhiều, topology không khớp có thể cần SWAP và noise cao hơn.

**Shot noise:** kết quả đo hữu hạn shots có sai số thống kê; ngay cả mô phỏng lý tưởng cũng có thể có `F < 1`. Nên dùng nhiều seeds và phân tích CI khi đánh giá chính thức. Cùng số shots, seeds, optimization level được dùng cho tất cả backend.

## 5. Ground Truth

File: `src/ranking/ground_truth.py`.

Ground truth **không** được định nghĩa bằng calibration heuristic hoặc label sinh từ thuật toán dự đoán. Nó lấy từ kết quả simulation độc lập: đối với mỗi circuit, xếp backend theo `mean_fidelity` **giảm dần**, nếu hòa theo `mean_tvd` **tăng dần**, sau cùng theo `backend_name` (đảm bảo reproducible). Gán `ground_truth_rank = 1..N`. `ground_truth_relevance = mean_fidelity` để NDCG dùng được relevance liên tục.

Đây là **simulation-derived proxy ground truth**, không phải ground truth đo trên hardware thực. Các backend có fidelity cực sát nhau có thể hoán đổi vị trí do shot noise; khi báo cáo học thuật nên kiểm tra khoảng tin cậy hoặc độ ổn định thứ hạng.

## 6. Baseline độc lập

File: `src/ranking/baseline.py`.

Baseline từ **đặc trưng mạch + trung bình calibration**, không đọc kết quả mô phỏng/nhãn:

`predicted_score = (1 - e_1)^n_1 × (1 - e_2)^n_2 × (1 - e_readout)^n_qubits`

Trong đó `e_1`, `e_2` là gate error trung bình của gate 1/2 qubit, `e_readout` là readout error trung bình của backend; `n_1`, `n_2` lấy từ mạch gốc. Điểm cao hơn xếp hạng cao hơn. Đây là baseline **rất đơn giản**; chưa tính SWAP bổ sung do routing, thời lượng gate, decoherence cụ thể từng qubit hoặc mapping layout thực, nên không coi đây là mô hình vật lý chính xác.

## 7. Ranking metrics

File: `src/ranking/metrics.py`, `src/ranking/evaluate.py`.

Đánh giá **trên từng circuit**, so sánh danh sách backend dự đoán với danh sách ground truth, sau đó lấy trung bình không trọng số qua các circuit (macro-average). Các cột:

| Metric | Diễn giải | Tốt nhất |
|---|---|---|
| `spearman_rho` | Tương quan thứ hạng (hoàn toàn đảo ngược = -1) | 1 |
| `kendall_tau` | Tỷ lệ cặp backend đồng thuận trừ bất đồng | 1 |
| `top1_accuracy` | Backend ground-truth tốt nhất có đứng vị trí 1 không | 1 |
| `top2_hit` | Backend ground-truth tốt nhất có xuất hiện trong 2 gợi ý đầu | 1 |
| `precision_at_2` | Tỷ lệ giao nhau giữa top-2 dự đoán và top-2 ground truth | 1 |
| `mrr` | Nghịch đảo vị trí của backend tốt nhất thật sự | 1 |
| `ndcg_at_2` | NDCG@2 dùng fidelity làm relevance | 1 |
| `ndcg_at_all` | NDCG toàn bộ danh sách backend | 1 |

Định nghĩa `top2_hit` **khác** `precision_at_2`; danh sách ít hơn 2 backend thì tính `min(2,N)`. NDCG dùng gain `2^relevance - 1` và discount `log2(rank+1)`. Với relevance rất gần nhau, NDCG có thể cao ngay cả khi thứ hạng sai; nên báo cáo kèm Spearman/Kendall/Top1.

Các hàm có validation: thiếu backend, thừa backend, lặp tên, ranks không liên tiếp, missing relevance → lỗi rõ ràng; không tự bỏ dòng và làm méo kết quả.

## 8. Artifact / output

| Tệp | Nội dung |
|---|---|
| `data/results/noise_simulation_runs.csv` | Từng `(circuit, backend, seed)` với shots, fidelity, TVD, counts |
| `data/results/noise_simulation_summary.csv` | Fidelity mean/std, mean TVD và số runs |
| `data/results/ground_truth.csv` | Rank và relevance đo theo noisy simulation |
| `data/results/baseline_predictions.csv` | Điểm/rank ước lượng không dùng nhãn |
| `data/results/ranking_metrics_per_circuit.csv` | Metrics mỗi circuit |
| `data/results/ranking_metrics_summary.csv` | Macro-average metrics trên tất cả circuit |

Không tự tạo file GT/metrics từ dữ liệu giả trước khi simulation chạy thành công. `baseline_predictions.csv` có thể chạy riêng không cần Qiskit nếu đã có 3 CSV calibration và `circuit_features.csv`.

## 9. Kiểm thử và tình trạng thực thi

- Test thuần Python: `python -m unittest tests.test_ranking -v`.
- Test tích hợp Qiskit: `python -m unittest tests.test_qiskit_integration -v`; tự **SKIP** nếu thiếu thư viện, không coi là PASS.
- Trong môi trường tạo bản bàn giao, `qiskit`/`qiskit_aer`/`qiskit_ibm_runtime` **chưa được cài** do môi trường không truy cập package index; vì vậy **chưa có số liệu noisy simulation hoặc ranking metrics thực nghiệm thật**.
- `baseline_predictions.csv` được tính **thật** từ CSV calibration của ZIP, tách biệt với ground truth.

## 10. Giới hạn và bước mở rộng

1. **Measurement-only proxy:** bổ sung nhiều measurement bases / observables nếu đánh giá độ trung thực quantum đầy đủ.
2. **Statistical stability:** tăng shots, seeds; bootstrap CI và kiểm tra khi 2 backend gần như đồng hạng.
3. **Calibration drift:** fake backend snapshots không mô tả chính xác hardware live; ghi timestamp/version trong báo cáo thí nghiệm.
4. **Prediction quality:** mở rộng baseline thành ranking model học có giám sát với circuit-level train/test split, tránh data leakage bằng cách tách toàn bộ circuit family nếu cần đánh giá out-of-distribution.
5. **Architecture:** mô phỏng có thể rất nặng khi tăng số circuit, số seed, shots; cần cache, logging, và batch/parallel có kiểm soát.
