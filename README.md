# 🏥 Healthcare Operations Simulation – Emergency Department Flow

## 🎯 Objective

This project explores Healthcare Operations & Systems Design using real emergency-department (ED) data to demonstrate:

- **Six Sigma**: Process capability and variation
- **Lean Thinking**: Value vs non-value-added time
- **Discrete-Event Simulation (SimPy)**: Resource bottlenecks and what-if scenarios

---

## 📘 Dataset

**File**: `data/emergency_service.csv`  
**Records**: ~1,260 anonymized ED visits

| Field                                | Example | Description               |
| ------------------------------------ | ------- | ------------------------- |
| Age, Sex                             | 68, 1   | Patient demographics      |
| KTAS duration (min)                  | 5.0     | Triage time (value-added) |
| Length of stay (min)                 | 240     | Total ED time             |
| Arrival mode, Diagnosis, Disposition | —       | Process metadata          |

---

## ⚙️ Model Structure

| Stage             | Resource  | Distribution       | Purpose              |
| ----------------- | --------- | ------------------ | -------------------- |
| Arrival           | —         | Poisson (λ ≈ 10/h) | Patient entry flow   |
| Triage            | 2 nurses  | Exp(6 min)         | Initial assessment   |
| Doctor evaluation | 2 doctors | Exp(30 min)        | Treatment / decision |
| Exit              | —         | —                  | Discharge / transfer |

---

## 🧮 Six Sigma Baseline

| Metric                 | Value     |
| ---------------------- | --------- |
| USL (target max LOS)   | 120 min   |
| Mean LOS               | 240.8 min |
| σ (standard deviation) | 170.5 min |
| Cpk                    | −0.24     |
| DPMO                   | ≈ 718,000 |

> ⚠️ Process is not capable; ~72% of cases exceed the spec limit.

---

## 🪚 Lean Value Analysis

| Category              | Time (min) | Share |
| --------------------- | ---------- | ----- |
| Value-added (VA)      | ≈ 5,942    | 2.5%  |
| Non-value-added (NVA) | ≈ 230,981  | 97.5% |

> 🚨 Huge waste from waiting; target for automation and staff balancing.

---

## 🧠 Discrete-Event Simulation (8 h shift)

| Scenario               | Avg Wait (95% CI) | Avg LOS (95% CI) | Patients (95% CI) |
| ---------------------- | ----------------- | ---------------- | ----------------- |
| Base (2 N, 2 D)        | 118 (97–140)      | 149 (127–170)    | 33 (30–36)        |
| +1 Doctor              | 87 (65–109)       | 118 (95–140)     | 47 (44–50)        |
| +1 Nurse               | 113 (86–140)      | 143 (116–170)    | 33 (30–36)        |
| +1 Doctor + Automation | ≈ 87 (65–109)     | ≈ 118 (95–140)   | 47 (44–50)        |

> 📊 Bar chart with 95% CIs confirms adding a doctor yields the only statistically significant improvement.

---

## 🩺 Resource Utilization & Capacity Sweep

| Doctors | Avg LOS (95% CI) | Doctor Util (95% CI) | Comment                 |
| ------- | ---------------- | -------------------- | ----------------------- |
| 2       | 130 (110–151)    | 93%                  | Overloaded → bottleneck |
| 3       | 113 (91–135)     | 91%                  | Still high              |
| 4       | 68 (51–85)       | 90%                  | Stable                  |
| 5       | 54 (42–66)       | 83%                  | ✅ Optimal (~80–85%)    |
| 6       | 36 (30–41)       | 69%                  | Over-staffed            |

> ✅ Doctor utilization ≈ 93% at baseline; 5 doctors balance flow (~83%).

---

## 🔍 Key Findings

- The ED is a **doctor-constrained system**.
- Adding nurses alone does not help; **triage is not the bottleneck**.
- Automation of triage only adds value **when doctor capacity is expanded**.
- **Optimal staffing**: 2 nurses + 5 doctors for 8 h shift  
  (target LOS ≤ 120 min, utilization ≤ 85%)

> 🧠 Lean + Six Sigma + Simulation integration provides a complete operations-engineering view.

---

## 💾 Project Structure

```
ai-health-ops-lab/
├─ data/
│  ├─ emergency_service.csv
│  └─ ed_simulation_replications.csv
├─ notebooks/
│  └─ 01_sixsigma_ed.ipynb
│  └─ 02_lean_vsm_ed.ipynb
│  └─ 03_simulation_ed.ipynb
├─ src/
│  ├─ sixsigma.py
│  ├─ lean.py
│  └─ sim_ed.py
└─ README.md
```

---

## 🧩 Dependencies

- pandas
- numpy
- matplotlib
- scipy
- simpy

Install via:

```bash
pip install -r requirements.txt
```

---

## ✨ How to Run

```bash
python src/sim_ed.py
```

Or open the notebook:

```bash
notebooks/03_simulation_ed.ipynb
```

Run cells sequentially.

---

## 📖 Next Steps (Future Work)

- I will add diagnostics resource (CT/X-ray) to test next bottleneck
- I will also fit empirical distributions from the dataset (`scipy.stats`)
- Automate staffing optimization with `optuna`
- Integrate results with Lean VSM visualization and Six Sigma control charts

---
