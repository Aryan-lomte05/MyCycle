"""Personal-baseline detectors and the rule layer (package A2).

Every detector has the same streaming interface:
    det = make_detector("cusum", h=5.0)
    out = det.update(cycle)   # cycle log object (contract 5.3), returns screening output (contract 5.2)

A detector turns each cycle into per-feature signals (for example cycle_length_high, acne_high).
The rule layer, shared by all detectors, maps signals to one screening flag. So detectors differ only
in how they decide that a feature has left the personal baseline, which keeps the comparison fair.

Detectors:
  fixed_threshold   population cutoffs, no personal baseline ("what most apps do" reference)
  zscore            EWMA mean and SD per feature, flag when |z| >= threshold
  ewma              EWMA control chart on the standardized series against a fixed personal reference
  cusum             one-sided CUSUM (upper, and lower for cycle length) against a fixed personal reference
  isolation_forest  per-user Isolation Forest refit on the user's past cycles (comparison only)
  hybrid            Tier 1 used by the app: union of zscore and cusum signals, then the rule layer

Missing values are skipped: no signal and no baseline update for that feature in that cycle.
A feature that signals does not update its baseline, so a sustained drift is not absorbed.

Only zscore, cusum and hybrid outputs satisfy contract 5.2 (its detector enum is zscore | cusum | gru).
The other detectors are evaluation-only and put their own name in the detector field.
"""
from __future__ import annotations

import math
from collections import deque

import numpy as np

from sim.common import SYMPTOMS

CONTRACT_DETECTORS = {"zscore", "cusum", "gru"}

# (input field, signal prefix, directions checked)
FEATURE_SPECS = [("cycle_length_days", "cycle_length", ("high", "low")), ("flow", "flow", ("high",)),
                 ("pain", "pain", ("high",))] + [(s, s, ("high",)) for s in SYMPTOMS]
INPUTS = [f for f, _, _ in FEATURE_SPECS]
SIGNAL_ORDER = [f"{p}_{d}" for _, p, dirs in FEATURE_SPECS for d in dirs]
LENGTH_SIGNALS = {"cycle_length_high", "cycle_length_low"}

# Minimum SD per feature, in feature units. Stops a flat history from turning tiny changes into huge z.
# Design constants (sim/DETECTORS.md), not tuned.
SD_FLOOR = {"cycle_length_days": 1.0, "flow": 0.3, "pain": 1.0, **{s: 0.5 for s in SYMPTOMS}}

PATTERNS = [  # (flag, cycle-level signals, symptom set). Order breaks ties.
    ("pcos_pattern", {"cycle_length_high"}, ["acne", "excess_hair", "hair_loss"]),
    ("anemia_pattern", {"flow_high"}, ["fatigue", "dizziness", "pallor"]),
    ("thyroid_pattern", {"cycle_length_high", "cycle_length_low"}, ["fatigue", "weight_change", "mood"]),
]


def flatten(cycle: dict) -> dict[str, float | None]:
    """Cycle log object (nested symptoms) or flat row -> {input field: value or None}."""
    src = dict(cycle)
    if isinstance(src.get("symptoms"), dict):
        src.update(src.pop("symptoms"))
    out: dict[str, float | None] = {}
    for f in INPUTS:
        v = src.get(f)
        out[f] = None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)
    return out


def ordered(signals) -> list[str]:
    return [s for s in SIGNAL_ORDER if s in signals]


class RuleLayer:
    """Maps per-cycle signals to one flag.

    A pattern flag needs a cycle-level signal in the current cycle (cycle length or flow) AND at least one
    of its symptom signals within the last `window` cycles. With no pattern, a cycle length signal gives
    irregularity. Symptom or flow signals alone give none.
    Confidence: high if two or more pattern symptoms and the cycle signal in two of the last `window`
    cycles, medium if one of those holds, low otherwise.
    """

    def __init__(self, window: int = 3):
        self.window = window
        self.hist: deque[set[str]] = deque(maxlen=window)

    def step(self, signals) -> tuple[str, str, list[str]]:
        current = set(signals)
        self.hist.append(current)
        recent = set().union(*self.hist)
        best = None
        for order, (flag, cyc, syms) in enumerate(PATTERNS):
            cur_cyc = cyc & current
            hits = {f"{s}_high" for s in syms} & recent
            if cur_cyc and hits:
                key = (len(hits), -order)
                if best is None or key > best[0]:
                    best = (key, flag, cyc, cur_cyc, hits)
        if best is not None:
            _, flag, cyc, cur_cyc, hits = best
            persist = sum(1 for h in self.hist if h & cyc)
            strong = [len(hits) >= 2, persist >= 2]
            conf = "high" if all(strong) else "medium" if any(strong) else "low"
            return flag, conf, ordered(cur_cyc | hits)
        length = current & LENGTH_SIGNALS
        if length:
            persist = sum(1 for h in self.hist if h & LENGTH_SIGNALS)
            return "irregularity", "medium" if persist >= 2 else "low", ordered(length)
        return "none", "low", []


class Detector:
    name = "base"

    def __init__(self, window: int = 3):
        self.rules = RuleLayer(window)

    def _step(self, x: dict[str, float | None]) -> tuple[dict[str, float], dict[str, str]]:
        """Return (strength per signal name, 1.0 = at threshold; source detector per fired signal)."""
        raise NotImplementedError

    def _fired(self, strengths: dict[str, float], sources: dict[str, str]) -> set[str]:
        return set(sources)

    def _label(self, contributing: list[str], sources: dict[str, str]) -> str:
        return self.name

    def update(self, cycle: dict) -> dict:
        strengths, sources = self._step(flatten(cycle))
        flag, conf, contributing = self.rules.step(self._fired(strengths, sources))
        return {
            "cycle_index": int(cycle["cycle_index"]),
            "flag": flag,
            "score": round(max(strengths.values(), default=0.0), 4),
            "confidence": conf,
            "contributing_signals": contributing,
            "message_key": f"flag.{flag}.v1",
            "detector": self._label(contributing, sources),
            "simulated": True,
        }


class FixedThresholdDetector(Detector):
    """Population cutoffs: cycle length outside 21..35 days, flow heavy (3), pain 7 or more, symptom moderate (2) or more."""
    name = "fixed_threshold"

    def __init__(self, length_low: float = 21, length_high: float = 35, flow_high: float = 3, pain_high: float = 7,
                 symptom_high: float = 2, window: int = 3):
        super().__init__(window)
        self.cut = {"cycle_length_days": length_high, "flow": flow_high, "pain": pain_high, **{s: symptom_high for s in SYMPTOMS}}
        self.length_low = length_low

    def _step(self, x):
        strengths, sources = {}, {}
        for f, p, dirs in FEATURE_SPECS:
            v = x[f]
            if v is None:
                continue
            if f == "cycle_length_days":
                strengths[f"{p}_high"] = v / self.cut[f]
                strengths[f"{p}_low"] = self.length_low / v
                if v > self.cut[f]:
                    sources[f"{p}_high"] = self.name
                if v < self.length_low:
                    sources[f"{p}_low"] = self.name
            else:
                strengths[f"{p}_high"] = v / self.cut[f]
                if v >= self.cut[f]:
                    sources[f"{p}_high"] = self.name
        return strengths, sources


def _directional(prefix: str, dirs, stat_high: float, stat_low: float, limit: float, name: str,
                 strengths: dict, sources: dict) -> bool:
    """Record strengths for a feature and mark fired signals. Returns True if any fired."""
    fired = False
    for d, stat in (("high", stat_high), ("low", stat_low)):
        if d not in dirs:
            continue
        strengths[f"{prefix}_{d}"] = max(stat, 0.0) / limit
        if stat >= limit:
            sources[f"{prefix}_{d}"] = name
            fired = True
    return fired


class ZScoreDetector(Detector):
    """Adaptive personal baseline: EWMA mean and variance per feature (weight alpha), z against it."""
    name = "zscore"

    def __init__(self, threshold: float = 2.0, alpha: float = 0.3, min_history: int = 3, window: int = 3):
        super().__init__(window)
        self.threshold, self.alpha, self.min_history = threshold, alpha, min_history
        self.state = {f: [0, 0.0, 0.0] for f in INPUTS}  # n, mean, variance

    def _step(self, x):
        strengths, sources = {}, {}
        for f, p, dirs in FEATURE_SPECS:
            v = x[f]
            if v is None:
                continue
            st = self.state[f]
            fired = False
            if st[0] >= self.min_history:
                z = (v - st[1]) / max(math.sqrt(st[2]), SD_FLOOR[f])
                fired = _directional(p, dirs, z, -z, self.threshold, self.name, strengths, sources)
            if not fired:
                if st[0] == 0:
                    st[1], st[2] = v, 0.0
                else:
                    d = v - st[1]
                    st[1] += self.alpha * d
                    st[2] = (1 - self.alpha) * (st[2] + self.alpha * d * d)
                st[0] += 1
        return strengths, sources


class FixedReference:
    """Personal reference for control charts: mean and SD of the first `size` non-signalled observations, then frozen."""

    def __init__(self, floor: float, size: int = 6):
        self.floor, self.size, self.values = floor, size, []

    def add(self, v: float) -> None:
        if len(self.values) < self.size:
            self.values.append(v)

    def ready(self, min_history: int) -> bool:
        return len(self.values) >= min_history

    def standardize(self, v: float) -> float:
        a = np.asarray(self.values)
        sd = float(a.std(ddof=1)) if len(a) > 1 else 0.0
        return (v - float(a.mean())) / max(sd, self.floor)


class CusumDetector(Detector):
    """One-sided CUSUM on the standardized series: S+ = max(0, S+ + s - k), S- for cycle length; signal when S > h."""
    name = "cusum"

    def __init__(self, h: float = 5.0, k: float = 0.5, min_history: int = 3, baseline_window: int = 6, window: int = 3):
        super().__init__(window)
        self.h, self.k, self.min_history = h, k, min_history
        self.ref = {f: FixedReference(SD_FLOOR[f], baseline_window) for f in INPUTS}
        self.s_hi = dict.fromkeys(INPUTS, 0.0)
        self.s_lo = dict.fromkeys(INPUTS, 0.0)

    def _step(self, x):
        strengths, sources = {}, {}
        for f, p, dirs in FEATURE_SPECS:
            v = x[f]
            if v is None:
                continue
            fired = False
            if self.ref[f].ready(self.min_history):
                s = self.ref[f].standardize(v)
                self.s_hi[f] = max(0.0, self.s_hi[f] + s - self.k)
                self.s_lo[f] = max(0.0, self.s_lo[f] - s - self.k)
                fired = _directional(p, dirs, self.s_hi[f], self.s_lo[f], self.h, self.name, strengths, sources)
            if not fired:
                self.ref[f].add(v)
        return strengths, sources


class EwmaChartDetector(Detector):
    """EWMA control chart: e = lam * s + (1 - lam) * e, signal when |e| > L * sqrt(lam / (2 - lam))."""
    name = "ewma"

    def __init__(self, L: float = 3.0, lam: float = 0.3, min_history: int = 3, baseline_window: int = 6, window: int = 3):
        super().__init__(window)
        self.limit = L * math.sqrt(lam / (2 - lam))
        self.lam, self.min_history = lam, min_history
        self.ref = {f: FixedReference(SD_FLOOR[f], baseline_window) for f in INPUTS}
        self.e = dict.fromkeys(INPUTS, 0.0)

    def _step(self, x):
        strengths, sources = {}, {}
        for f, p, dirs in FEATURE_SPECS:
            v = x[f]
            if v is None:
                continue
            fired = False
            if self.ref[f].ready(self.min_history):
                s = self.ref[f].standardize(v)
                self.e[f] = self.lam * s + (1 - self.lam) * self.e[f]
                fired = _directional(p, dirs, self.e[f], -self.e[f], self.limit, self.name, strengths, sources)
            if not fired:
                self.ref[f].add(v)
        return strengths, sources


class IsolationForestDetector(Detector):
    """Per-user Isolation Forest refit each cycle on all of that user's past cycles (needs min_history).

    When the anomaly score (0..1, about 0.5 is ordinary) exceeds `threshold`, the features whose
    standardized deviation from the user's past mean is at least `attribution_z` become the signals.
    Score and attribution do not depend on the threshold, so evaluation computes them once (`raw`).
    """
    name = "isolation_forest"

    def __init__(self, threshold: float = 0.6, min_history: int = 5, n_estimators: int = 50,
                 attribution_z: float = 2.0, seed: int = 0, window: int = 3):
        super().__init__(window)
        self.threshold, self.min_history, self.n_estimators = threshold, min_history, n_estimators
        self.attribution_z, self.seed = attribution_z, seed
        self.history: list[dict[str, float | None]] = []

    def raw(self, x: dict[str, float | None]) -> tuple[float, dict[str, float]]:
        """(anomaly score, standardized deviation per signal name) for x given the history, then append x."""
        from sklearn.ensemble import IsolationForest

        score, dev = 0.0, {}
        if len(self.history) >= self.min_history:
            hist = np.array([[np.nan if h[f] is None else h[f] for f in INPUTS] for h in self.history])
            med = np.nan_to_num(np.nanmedian(hist, axis=0), nan=0.0) if not np.isnan(hist).all() else np.zeros(len(INPUTS))
            hist = np.where(np.isnan(hist), med, hist)
            cur = np.array([med[i] if x[f] is None else x[f] for i, f in enumerate(INPUTS)])
            model = IsolationForest(n_estimators=self.n_estimators, random_state=self.seed).fit(hist)
            score = float(-model.score_samples(cur.reshape(1, -1))[0])
            mean, sd = hist.mean(axis=0), hist.std(axis=0, ddof=1)
            for i, (f, p, dirs) in enumerate(FEATURE_SPECS):
                if x[f] is None:
                    continue
                s = (cur[i] - mean[i]) / max(float(sd[i]), SD_FLOOR[f])
                if "high" in dirs:
                    dev[f"{p}_high"] = s
                if "low" in dirs:
                    dev[f"{p}_low"] = -s
        self.history.append(x)
        return score, dev

    def signals_from_raw(self, score: float, dev: dict[str, float]) -> dict[str, str]:
        if score <= self.threshold:
            return {}
        return {k: self.name for k, v in dev.items() if v >= self.attribution_z}

    def _step(self, x):
        score, dev = self.raw(x)
        strengths = {"anomaly": score / self.threshold} if dev else {}
        return strengths, self.signals_from_raw(score, dev)


class HybridDetector(Detector):
    """Tier 1 hybrid: signals from the adaptive z-score OR from CUSUM, then the shared rule layer."""
    name = "hybrid"

    def __init__(self, z_threshold: float = 3.0, h: float = 5.0, alpha: float = 0.3, k: float = 0.5,
                 min_history: int = 3, baseline_window: int = 6, window: int = 3):
        super().__init__(window)
        self.z = ZScoreDetector(z_threshold, alpha, min_history)
        self.c = CusumDetector(h, k, min_history, baseline_window)

    def _step(self, x):
        zs, zsrc = self.z._step(x)
        cs, csrc = self.c._step(x)
        strengths = {k: max(zs.get(k, 0.0), cs.get(k, 0.0)) for k in set(zs) | set(cs)}
        return strengths, {**csrc, **zsrc}  # z-score wins attribution when both fire

    def _label(self, contributing, sources):
        return "cusum" if any(sources.get(s) == "cusum" for s in contributing) else "zscore"


REGISTRY = {
    "fixed_threshold": FixedThresholdDetector,
    "zscore": ZScoreDetector,
    "ewma": EwmaChartDetector,
    "cusum": CusumDetector,
    "isolation_forest": IsolationForestDetector,
    "hybrid": HybridDetector,
}


def make_detector(name: str, **params) -> Detector:
    return REGISTRY[name](**params)
