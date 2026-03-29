"""Configuration for the Automatic Insights System.

Centralizes metric polarity, category weights, detection thresholds,
and correlated metric pairs. All values are tunable without code changes
to the detection logic.
"""

# --- Metric Polarity ---
# "higher_is_better" or "lower_is_better"
# Used by anomaly, trend, and opportunity detectors to classify direction.

METRIC_POLARITY: dict[str, str] = {
    "Perfect Orders": "higher_is_better",
    "Gross Profit UE": "higher_is_better",
    "Lead Penetration": "higher_is_better",
    "Pro Adoption": "higher_is_better",
    "Turbo Adoption": "higher_is_better",
    "Restaurants SST > SS CVR": "higher_is_better",
    "Restaurants SS > ATC CVR": "higher_is_better",
    "Restaurants ATC > Trx CVR": "higher_is_better",
    "% PRO Users Who Breakeven": "higher_is_better",
    "% Order Loss": "lower_is_better",
    "Restaurants Markdowns / GMV": "lower_is_better",
}

# Default polarity for metrics not in the table above.
DEFAULT_POLARITY = "higher_is_better"

# --- Metric Display Type ---
# "dollar" = absolute value with $ (e.g., Gross Profit UE)
# "ratio"  = 0-1 value shown as percentage (e.g., Perfect Orders = 88.7%)
# "number" = raw number (e.g., Lead Penetration = 14.6%)
# Controls how values are formatted in insight titles/descriptions.

METRIC_DISPLAY_TYPE: dict[str, str] = {
    "Gross Profit UE": "dollar",
    "Lead Penetration": "ratio",
    "Perfect Orders": "ratio",
    "Pro Adoption": "ratio",
    "Pro Adoption (Last Week Status)": "ratio",
    "Turbo Adoption": "ratio",
    "% PRO Users Who Breakeven": "ratio",
    "% Order Loss": "ratio",
    "% Restaurants Sessions With Optimal Assortment": "ratio",
    "Restaurants SST > SS CVR": "ratio",
    "Restaurants SS > ATC CVR": "ratio",
    "Restaurants ATC > Trx CVR": "ratio",
    "Retail SST > SS CVR": "ratio",
    "Non-Pro PTC > OP": "ratio",
    "MLTV Top Verticals Adoption": "ratio",
    "Restaurants Markdowns / GMV": "ratio",
}

# --- Category Weights (for severity scoring) ---
# Higher weight = more urgent in executive summary ranking.

CATEGORY_WEIGHTS: dict[str, float] = {
    "anomalias": 1.0,
    "tendencias": 0.9,
    "benchmarking": 0.7,
    "correlaciones": 0.6,
    "oportunidades": 0.5,
}

# --- Result Limits ---
# Maximum findings per detector (top-N by severity).
MAX_FINDINGS_PER_DETECTOR = 10
# Maximum findings per CATEGORY in the final report.
MAX_FINDINGS_PER_CATEGORY = 3
# Maximum findings per METRIC within a category (forces diversity).
MAX_FINDINGS_PER_METRIC_PER_CATEGORY = 2
# Maximum total findings in the report.
MAX_TOTAL_FINDINGS = 15

# --- Severity Cap ---
# Cap magnitude at this value to prevent outliers from dominating.
# A 134,000% change from a 0.001 baseline is noise, not insight.
SEVERITY_MAGNITUDE_CAP = 5.0  # max 500% change treated as meaningful

# --- Detection Thresholds ---

# Anomalies: minimum relative WoW change to flag.
# 10% was too low — captured 22% of all zone/metric combos as "anomalies".
# 25% focuses on truly significant changes.
ANOMALY_THRESHOLD = 0.25  # 25%

# Trends: minimum number of consecutive declining weeks.
TREND_MIN_WEEKS = 3

# Trends: minimum total cumulative change over the period to avoid noise.
# 5% was too low — flagged micro-fluctuations. 15% focuses on real deterioration.
TREND_MIN_MAGNITUDE = 0.15  # 15% total decline

# Benchmarking: minimum divergence from peer median to flag.
# 20% captured 43% of all data. 40% focuses on meaningful outliers.
BENCHMARK_DIVERGENCE_THRESHOLD = 0.40  # 40%

# Benchmarking: minimum zones in a peer group.
BENCHMARK_MIN_PEER_GROUP = 3

# Opportunities: minimum improvement magnitude (same as trend threshold).
OPPORTUNITY_MIN_MAGNITUDE = 0.05

# Opportunities: max weak metrics for "targeted weakness" detector.
OPPORTUNITY_MAX_WEAK_METRICS = 2

# Opportunities: threshold for "significantly below" peer median.
OPPORTUNITY_BELOW_THRESHOLD = 0.15  # 15%

# --- Correlated Metric Pairs ---
# Each tuple is (metric_a, metric_b, inverse).
# inverse=False: both below median triggers finding.
# inverse=True: metric_a below median AND metric_b above median triggers finding.

CORRELATED_PAIRS: list[tuple[str, str, bool]] = [
    ("Lead Penetration", "Restaurants SST > SS CVR", False),
    ("Restaurants SS > ATC CVR", "Restaurants ATC > Trx CVR", False),
    ("Perfect Orders", "% Order Loss", True),  # inverse: low PO + high loss
    ("Pro Adoption", "Gross Profit UE", False),
]

# --- Key Metrics (subset for profiling and summaries) ---

KEY_METRICS = [
    "Perfect Orders",
    "Gross Profit UE",
    "Lead Penetration",
    "Pro Adoption",
    "Turbo Adoption",
]

# --- Week Columns ---
# Ordered oldest to newest for raw_input_metrics and raw_orders.

METRIC_WEEK_COLS = [
    "L8W_ROLL", "L7W_ROLL", "L6W_ROLL", "L5W_ROLL",
    "L4W_ROLL", "L3W_ROLL", "L2W_ROLL", "L1W_ROLL", "L0W_ROLL",
]

ORDER_WEEK_COLS = [
    "L8W", "L7W", "L6W", "L5W", "L4W", "L3W", "L2W", "L1W", "L0W",
]
