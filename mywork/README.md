# Rank-based Backend Recommendation

Project cung cấp calibration và feature extraction cho 4 fake quantum backends và 10 circuits.

**Mới bổ sung**: Noise simulation (Qiskit Aer), Ground Truth xếp hạng từ kết quả mô phỏng, baseline calibration và Ranking Metrics.

- **Hướng dẫn chi tiết bằng tiếng Việt:** [docs/TECHNICAL_DOCS_VI.md](docs/TECHNICAL_DOCS_VI.md)
- Cài dependencies: `python -m pip install numpy pandas scipy 'qiskit>=2,<3' 'qiskit-aer>=0.15' 'qiskit-ibm-runtime>=0.35'`
- Chạy tests: `python -m unittest discover -s tests -v`
- Chạy pipeline: `python -m scripts.run_pipeline --shots 4096 --seeds 42 100 202`

Các file kết quả sinh trong `data/results/`. **Không coi dự đoán baseline là ground truth.**
