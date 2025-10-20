import sys
print(sys.executable)

# ==========================================
#  DISCRETE-EVENT SIMULATION – ED PATIENT FLOW
# ==========================================

import simpy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats as st

# ----------------------------
# 1. Load dataset for parameters
# ----------------------------
df = pd.read_csv("../data/emergency_service.csv", delimiter=";", encoding="latin1")

for col in ["Length of stay_min", "KTAS duration_min"]:
    df[col] = df[col].astype(str).str.replace(",", ".", regex=False).astype(float)

df = df.dropna(subset=["Length of stay_min", "KTAS duration_min"])
df = df[df["Length of stay_min"] <= 720]  # realistic cap

# estimating realistic averages for process steps
triage_mean = df["KTAS duration_min"].mean()             # triage time (VA)
wait_mean = (df["Length of stay_min"] - df["KTAS duration_min"]).mean()  # total waiting time
service_mean = 30                                        # doctor's service (approximation)
arrival_rate = 10                                        # mean interarrival (patients per hour)
arrival_interval = 60 / arrival_rate                     # minutes between arrivals

print(f"Average triage: {triage_mean:.2f} min, Mean waiting: {wait_mean:.2f} min")

# ----------------------------
# 2. Define the Simulation Environment
# ----------------------------
RANDOM_SEED = 42
SIM_TIME = 480   # minutes (8-hour shift)

class EmergencyDepartment:
    """Hospital ED simulation with triage nurses and doctors."""
    def __init__(self, env, n_nurses, n_doctors):
        self.env = env
        self.nurse = simpy.Resource(env, n_nurses)
        self.doctor = simpy.Resource(env, n_doctors)
        self.wait_times = []
        self.los = []

    def triage(self, patient_id):
        yield self.env.timeout(np.random.exponential(triage_mean))

    def doctor_eval(self, patient_id):
        yield self.env.timeout(np.random.exponential(service_mean))

# ----------------------------
# 3. Patient Process
# ----------------------------
def patient(env, patient_id, ed):
    """Full patient journey through ED"""
    arrival_time = env.now

    # ---- step 1: wait for nurse (triage)
    with ed.nurse.request() as req:
        yield req
        yield env.process(ed.triage(patient_id))

    # ---- step 2: wait for doctor
    with ed.doctor.request() as req:
        wait_start = env.now
        yield req
        wait_time = env.now - wait_start
        yield env.process(ed.doctor_eval(patient_id))

    total_time = env.now - arrival_time
    ed.wait_times.append(wait_time)
    ed.los.append(total_time)

# ----------------------------
# 4. Patient Arrival Generator
# ----------------------------
def patient_arrivals(env, ed):
    patient_id = 0
    while True:
        yield env.timeout(np.random.exponential(arrival_interval))
        patient_id += 1
        env.process(patient(env, patient_id, ed))

# ----------------------------
# 5. Run Base Scenario Simulation
# ----------------------------
def run_simulation(n_nurses=2, n_doctors=2, sim_time=SIM_TIME):
    np.random.seed(RANDOM_SEED)
    env = simpy.Environment()
    ed = EmergencyDepartment(env, n_nurses, n_doctors)
    env.process(patient_arrivals(env, ed))
    env.run(until=sim_time)
    return ed

ed_base = run_simulation()

# ----------------------------
# 6. Analyze Base Results
# ----------------------------
def summarize(ed, label):
    wait_mean = np.mean(ed.wait_times)
    los_mean = np.mean(ed.los)
    print(f"\n--- {label} ---")
    print(f"Average Wait Time: {wait_mean:.2f} min")
    print(f"Average Length of Stay (LOS): {los_mean:.2f} min")
    print(f"Total Patients Served: {len(ed.los)}")

summarize(ed_base, "BASELINE")

plt.figure(figsize=(8,4))
plt.hist(ed_base.los, bins=30, color="#4d908e", edgecolor="black")
plt.title("Distribution of Patient LOS (Baseline)")
plt.xlabel("Length of Stay (min)")
plt.ylabel("Number of Patients")
plt.show()

# ----------------------------
# 7. What-if Scenarios  (FIXED: no 'global' needed)
# ----------------------------
scenarios = [
    ("Base", 2, 2, 1.0),                  # factor 1.0 = no change
    ("Add 1 Doctor", 2, 3, 1.0),
    ("Add 1 Nurse", 3, 2, 1.0),
    ("Add 1 Doctor + Automation (triage 50% faster)", 2, 3, 0.5)  # triage 50% time
]

results = []

for label, n_nurse, n_doc, triage_factor in scenarios:
    # compute scenario-specific triage mean without touching the global value
    triage_mean_scn = triage_mean * triage_factor

    # run the scenario using this effective triage mean
    env = simpy.Environment()
    ed = EmergencyDepartment(env, n_nurse, n_doc)

    # monkey-patch the per-scenario triage time by shadowing the global via closure
    def triage_scn(self, patient_id, _m=triage_mean_scn):
        yield self.env.timeout(np.random.exponential(_m))
    # bind this triage function to the specific ed instance
    from types import MethodType
    ed.triage = MethodType(triage_scn, ed)

    env.process(patient_arrivals(env, ed))
    env.run(until=SIM_TIME)

    results.append({
        "Scenario": label,
        "Avg Wait (min)": np.mean(ed.wait_times),
        "Avg LOS (min)": np.mean(ed.los),
        "Patients": len(ed.los)
    })

results_df = pd.DataFrame(results)
print("\n--- Scenario Comparison ---")
print(results_df)

plt.figure(figsize=(8,5))
plt.bar(results_df["Scenario"], results_df["Avg LOS (min)"], color="#90be6d")
plt.title("Scenario Comparison – Avg Length of Stay")
plt.ylabel("Avg LOS (min)")
plt.xticks(rotation=45)
plt.show()


# ==========================================
# 8. Extended Analysis – Replications + CI
# ==========================================
def run_replications(n_runs=20, n_nurses=2, n_doctors=2):
    waits, losses, counts = [], [], []
    for seed in range(n_runs):
        np.random.seed(seed)
        env = simpy.Environment()
        ed = EmergencyDepartment(env, n_nurses, n_doctors)
        env.process(patient_arrivals(env, ed))
        env.run(until=SIM_TIME)
        waits.append(np.mean(ed.wait_times))
        losses.append(np.mean(ed.los))
        counts.append(len(ed.los))

    def ci(data):
        data = np.array(data, dtype=float)
        mean = np.nanmean(data)
        se = np.nanstd(data, ddof=1) / np.sqrt(len(data))
        h = st.t.ppf(0.975, len(data)-1) * se
        return mean, mean-h, mean+h

    return {
        "Wait (min)": ci(waits),
        "LOS (min)": ci(losses),
        "Patients": ci(counts)
    }

replication_summary = []
for label, n_nurse, n_doc in scenarios:
    stats = run_replications(n_runs=10, n_nurses=n_nurse, n_doctors=n_doc)
    replication_summary.append({
        "Scenario": label,
        "Avg Wait (95% CI)": f"{stats['Wait (min)'][0]:.1f} ({stats['Wait (min)'][1]:.1f}, {stats['Wait (min)'][2]:.1f})",
        "Avg LOS (95% CI)": f"{stats['LOS (min)'][0]:.1f} ({stats['LOS (min)'][1]:.1f}, {stats['LOS (min)'][2]:.1f})",
        "Patients (95% CI)": f"{stats['Patients'][0]:.0f} ({stats['Patients'][1]:.0f}, {stats['Patients'][2]:.0f})"
    })

rep_df = pd.DataFrame(replication_summary)
print("\n--- Replicated Simulation Summary ---")
print(rep_df.to_string(index=False))

rep_df.to_csv("../data/ed_simulation_replications.csv", index=False)
print("Saved detailed replication results.")

# ==========================================
# 9. Visualization – LOS Comparison with 95% CI
# ==========================================
means = [float(row.split()[0]) for row in rep_df["Avg LOS (95% CI)"]]
ci_lows = [float(row.split("(")[1].split(",")[0]) for row in rep_df["Avg LOS (95% CI)"]]
ci_highs = [float(row.split(",")[1].split(")")[0]) for row in rep_df["Avg LOS (95% CI)"]]
yerr = [np.array(means) - np.array(ci_lows), np.array(ci_highs) - np.array(means)]

plt.figure(figsize=(9,5))
plt.bar(rep_df["Scenario"], means, yerr=yerr, capsize=6, color="#90be6d")
plt.ylabel("Average LOS (min)")
plt.title("Scenario Comparison with 95% Confidence Intervals")
plt.xticks(rotation=35, ha="right")
plt.show()

# ==========================================
# 10. Resource Utilization Diagnostics
# ==========================================
class UtilizationTracker:
    def __init__(self, env, capacity):
        self.env = env
        self.capacity = capacity
        self.busy = 0
        self.last_change = env.now
        self.busy_time = 0

    def change(self, delta):
        now = self.env.now
        self.busy_time += (now - self.last_change) * self.busy
        self.last_change = now
        self.busy += delta

    def utilization(self, until):
        return (self.busy_time / (until * self.capacity)) * 100

def run_with_utilization(n_nurses=2, n_doctors=2, sim_time=SIM_TIME):
    env = simpy.Environment()
    nurse_mon = UtilizationTracker(env, n_nurses)
    doc_mon   = UtilizationTracker(env, n_doctors)
    ed = EmergencyDepartment(env, n_nurses, n_doctors)

    def monitored_patient(env, pid, ed):
        arrival = env.now
        with ed.nurse.request() as req:
            yield req; nurse_mon.change(+1)
            yield env.process(ed.triage(pid))
            nurse_mon.change(-1)
        with ed.doctor.request() as req:
            yield req; doc_mon.change(+1)
            yield env.process(ed.doctor_eval(pid))
            doc_mon.change(-1)
        ed.los.append(env.now - arrival)

    def arrivals():
        pid = 0
        while True:
            yield env.timeout(np.random.exponential(arrival_interval))
            pid += 1
            env.process(monitored_patient(env, pid, ed))

    env.process(arrivals())
    env.run(until=sim_time)
    print(f"Nurse Utilization: {nurse_mon.utilization(sim_time):.1f}%")
    print(f"Doctor Utilization: {doc_mon.utilization(sim_time):.1f}%")

run_with_utilization(2, 2)

# ==========================================
# 11. Doctor Staffing Sweep (Experimental)
# ==========================================
def ci_mean(vals):
    x = np.array(vals, dtype=float)
    m = np.nanmean(x); s = np.nanstd(x, ddof=1)
    h = st.t.ppf(0.975, len(x)-1)*s/np.sqrt(len(x))
    return m, m-h, m+h

def run_one_with_util(n_nurses, n_doctors, sim_time=SIM_TIME):
    env = simpy.Environment()
    class Mon:
        def __init__(self, env, cap):
            self.env=env; self.cap=cap; self.busy=0; self.t0=env.now; self.busy_time=0
        def ch(self, d):
            now=self.env.now; self.busy_time += (now-self.t0)*self.busy; self.t0=now; self.busy += d
        def util(self, until): return (self.busy_time/(until*self.cap))*100 if until>0 else 0

    nurse_mon = Mon(env, n_nurses)
    doc_mon   = Mon(env, n_doctors)
    ed = EmergencyDepartment(env, n_nurses, n_doctors)

    def pat(env, pid, ed):
        arr = env.now
        with ed.nurse.request() as r:
            yield r; nurse_mon.ch(+1)
            yield env.process(ed.triage(pid))
            nurse_mon.ch(-1)
        with ed.doctor.request() as r:
            w0 = env.now
            yield r; doc_mon.ch(+1)
            yield env.process(ed.doctor_eval(pid))
            doc_mon.ch(-1)
            wait = env.now - w0
            ed.wait_times.append(wait)
        ed.los.append(env.now - arr)

    def arrivals():
        pid=0
        while True:
            yield env.timeout(np.random.exponential(arrival_interval))
            pid += 1
            env.process(pat(env, pid, ed))

    env.process(arrivals())
    env.run(until=sim_time)
    return {
        "avg_wait": float(np.mean(ed.wait_times)) if ed.wait_times else np.nan,
        "avg_los": float(np.mean(ed.los)) if ed.los else np.nan,
        "served": len(ed.los),
        "nurse_util": nurse_mon.util(sim_time),
        "doc_util": doc_mon.util(sim_time),
    }

rows=[]
for docs in range(2, 7):
    waits, losses, served, dutil = [], [], [], []
    for seed in range(10):
        res = run_one_with_util(n_nurses=2, n_doctors=docs)
        waits.append(res["avg_wait"]); losses.append(res["avg_los"])
        served.append(res["served"]); dutil.append(res["doc_util"])
    rows.append({
        "Doctors": docs,
        "Avg LOS (95% CI)": f"{ci_mean(losses)[0]:.1f} ({ci_mean(losses)[1]:.1f}, {ci_mean(losses)[2]:.1f})",
        "Avg Wait (95% CI)": f"{ci_mean(waits)[0]:.1f} ({ci_mean(waits)[1]:.1f}, {ci_mean(waits)[2]:.1f})",
        "Patients/run (95% CI)": f"{ci_mean(served)[0]:.0f} ({ci_mean(served)[1]:.0f}, {ci_mean(served)[2]:.0f})",
        "Doctor util % (95% CI)": f"{ci_mean(dutil)[0]:.1f} ({ci_mean(dutil)[1]:.1f}, {ci_mean(dutil)[2]:.1f})",
    })

sweep_df = pd.DataFrame(rows)
print(sweep_df.to_string(index=False))
