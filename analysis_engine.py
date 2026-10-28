"""Scoring profile requested for the regional-manager Dealer 360 workflow.

The original six-factor model remains in app.py. This module implements the
separately versioned specification model and keeps performance scores distinct
from attention-risk contributions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


SPECIFICATION_WEIGHTS = {
    # Sales are outcome signals; give them the smallest individual weights.
    "Sales versus target": 0.05,
    "Less sales growth": 0.05,
    "Payment delays": 0.24,
    "Inventory ageing": 0.24,
    "Service performance": 0.30,
    "Customer complaints": 0.12,
}

GOOD_TARGET_SCORE = 70.0
GOOD_GROWTH_SCORE = 70.0
MIN_LOCAL_REFERENCE_COUNT = 3


def classify_risk_band(scores: pd.Series) -> pd.Series:
    """Apply half-open manager-facing bands: 0–<20, 20–<40, 40–<60, 60+."""
    values = pd.to_numeric(scores, errors="coerce")
    return pd.cut(values, bins=[0, 20, 40, 60, np.inf], right=False,
                  labels=["No attention", "Low-risk", "Mid-risk", "High-risk"])


def _numeric(frame: pd.DataFrame, field: str) -> pd.Series:
    if field not in frame:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[field], errors="coerce")


def _first_numeric(frame: pd.DataFrame, fields: tuple[str, ...]) -> pd.Series:
    result = pd.Series(np.nan, index=frame.index, dtype=float)
    for field in fields:
        values = _numeric(frame, field)
        result = result.where(result.notna(), values)
    return result


def _state_period_market(benchmark: pd.DataFrame | None) -> pd.DataFrame:
    """Build a state/month market trend only when the match key is unambiguous.

    The bundled VAHAN file has one state total per month. If an uploaded file
    has multiple scope rows for the same state/month, it is left unmatched here
    rather than summing potentially overlapping categories without a crosswalk.
    """
    required = {"month", "state", "registrations"}
    if benchmark is None or benchmark.empty or not required.issubset(benchmark.columns):
        return pd.DataFrame(columns=["state_key", "period_key", "registrations", "market_yoy_pct", "market_12m_avg"])

    data = benchmark.copy()
    data["state_key"] = data["state"].astype("string").str.strip().str.casefold()
    data["period_key"] = pd.to_datetime(data["month"], errors="coerce").dt.to_period("M")
    data["registrations"] = pd.to_numeric(data["registrations"], errors="coerce")
    data = data.dropna(subset=["state_key", "period_key", "registrations"])
    if data.empty:
        return pd.DataFrame(columns=["state_key", "period_key", "registrations", "market_yoy_pct", "market_12m_avg"])

    counts = data.groupby(["state_key", "period_key"], observed=True).size()
    unambiguous = counts[counts == 1].index
    data = data.set_index(["state_key", "period_key"]).loc[lambda x: x.index.isin(unambiguous)].reset_index()
    rows: list[pd.DataFrame] = []
    for state_key, group in data.groupby("state_key", sort=False):
        series = group.set_index("period_key")["registrations"].sort_index()
        records = []
        for period, value in series.items():
            recent_periods = pd.period_range(end=period, periods=12, freq="M")
            prior_periods = pd.period_range(end=period - 12, periods=12, freq="M")
            recent = series.reindex(recent_periods)
            prior = series.reindex(prior_periods)
            recent_total = float(recent.sum()) if recent.notna().all() else np.nan
            prior_total = float(prior.sum()) if prior.notna().all() else np.nan
            growth = ((recent_total / prior_total) - 1.0) * 100.0 if pd.notna(recent_total) and pd.notna(prior_total) and prior_total > 0 else np.nan
            records.append({
                "state_key": state_key,
                "period_key": period,
                "registrations": float(value),
                "market_yoy_pct": growth,
                "market_12m_avg": recent_total / 12.0 if pd.notna(recent_total) else np.nan,
            })
        rows.append(pd.DataFrame(records))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _cohort_reference(
    values: pd.Series,
    eligible: pd.Series,
    regions: pd.Series,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Find peer medians, using same-region eligible peers when n>=3.

    If fewer than three same-region peers qualify, use all qualifying dealers
    in the current reporting-period cohort. Returns median, n and method.
    """
    values = pd.to_numeric(values, errors="coerce")
    eligible = eligible.fillna(False) & values.notna()
    regions = regions.astype("string").fillna("").str.strip()
    eligible_values = values.where(eligible)
    overall_median = eligible_values.median()
    overall_n = int(eligible_values.notna().sum())
    medians, counts, methods = [], [], []
    for idx in values.index:
        same_region = eligible & regions.eq(regions.loc[idx]) & regions.ne("")
        local_values = values.loc[same_region]
        if len(local_values) >= MIN_LOCAL_REFERENCE_COUNT:
            medians.append(float(local_values.median()))
            counts.append(int(len(local_values)))
            methods.append("same-region qualifying peers")
        elif overall_n:
            medians.append(float(overall_median))
            counts.append(overall_n)
            methods.append("all qualifying dealers in period")
        else:
            medians.append(np.nan)
            counts.append(0)
            methods.append("reference cohort unavailable")
    return (
        pd.Series(medians, index=values.index, dtype=float),
        pd.Series(counts, index=values.index, dtype="int64"),
        pd.Series(methods, index=values.index, dtype="string"),
    )


def _risk_vs_reference(values: pd.Series, reference: pd.Series, zero_floor: float) -> pd.Series:
    """Risk score: peer median maps to 50; double the baseline maps to 100."""
    values = pd.to_numeric(values, errors="coerce")
    reference = pd.to_numeric(reference, errors="coerce")
    denominator = pd.concat([reference.abs(), pd.Series(zero_floor, index=reference.index)], axis=1).max(axis=1)
    score = 50.0 + 50.0 * (values - reference) / denominator
    return score.clip(0.0, 100.0).where(values.notna() & reference.notna())


def _peer_percentile_score(values: pd.Series, higher_is_better: bool) -> pd.Series:
    values = pd.to_numeric(values, errors="coerce")
    valid = values.notna()
    out = pd.Series(np.nan, index=values.index, dtype=float)
    if valid.any():
        percentile = values.loc[valid].rank(method="average", pct=True) * 100.0
        out.loc[valid] = percentile if higher_is_better else 100.0 - percentile
    return out


def _median_anchored_risk(values: pd.Series, reference_values: pd.Series | None = None) -> pd.Series:
    """Scale a factor's risk values so dataset min/median/max map to 0/50/100.

    Uses a separate linear segment on each side of the median. When a reference set
    has no spread, every usable entry is neutral at 50. Repeated values remain
    tied instead of receiving arbitrary dealer-specific ranks.
    """
    values = pd.to_numeric(values, errors="coerce")
    result = pd.Series(np.nan, index=values.index, dtype=float)
    valid = values.dropna()
    reference = pd.to_numeric(reference_values, errors="coerce").dropna() if reference_values is not None else valid
    if valid.empty or reference.empty:
        return result

    low = float(reference.min())
    median = float(reference.median())
    high = float(reference.max())
    if high == low:
        result.loc[valid.index] = 50.0
        return result

    bounded = valid.clip(low, high)
    lower = bounded.le(median)
    if median > low:
        result.loc[valid.index[lower]] = 50.0 * (bounded.loc[lower] - low) / (median - low)
    else:
        # If the median is tied with the minimum, identical minimum values
        # cannot be assigned both 0 and 50; preserve the explicit minimum rule.
        result.loc[valid.index[lower]] = 0.0

    upper = bounded.gt(median)
    if high > median:
        result.loc[valid.index[upper]] = 50.0 + 50.0 * (bounded.loc[upper] - median) / (high - median)
    return result.clip(0.0, 100.0)


def score_specification(
    frame: pd.DataFrame,
    benchmark: pd.DataFrame | None = None,
    market_scope_compatible: bool = False,
    risk_scale_reference: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate specification scores for one reporting-period dealer cohort.

    Scores for target, growth, inventory and service are performance scores
    (higher is healthier); payment and complaints are risk scores (higher is
    worse). Those directions are converted to a consistent risk direction for
    the weighted attention score.
    """
    out = frame.copy()
    state_col = "state" if "state" in out else None
    period_col = "month" if "month" in out else None
    region_col = "region" if "region" in out else state_col

    # Target achievement is a performance score and is capped at 100.
    target = _first_numeric(out, ("target_achievement_pct", "sales_target_achievement_pct"))
    if target.notna().sum() == 0 and {"retail_sales_units", "sales_target_units"}.issubset(out.columns):
        target = _numeric(out, "retail_sales_units") / _numeric(out, "sales_target_units").replace(0, np.nan) * 100.0
    target_score = target.clip(0.0, 100.0)

    # Keep the state-market comparison separate from scoring unless the manager
    # confirms the benchmark vehicle/catchment scope is comparable.
    dealer_growth = _first_numeric(out, ("sales_growth_yoy_pct", "yoy_sales_growth_pct"))
    market_table = _state_period_market(benchmark)
    out["market_state_monthly_registrations"] = np.nan
    out["market_trailing_12m_monthly_average"] = np.nan
    out["market_trailing_12m_yoy_growth_pct"] = np.nan
    out["market_growth_match_status"] = "No exact state/month benchmark match"
    if state_col and period_col and not market_table.empty:
        market_lookup = market_table.set_index(["state_key", "period_key"])
        periods = pd.to_datetime(out[period_col], errors="coerce").dt.to_period("M")
        state_keys = out[state_col].astype("string").str.strip().str.casefold()
        for idx in out.index:
            key = (state_keys.loc[idx], periods.loc[idx])
            if pd.isna(key[1]) or key not in market_lookup.index:
                continue
            market_row = market_lookup.loc[key]
            out.loc[idx, "market_state_monthly_registrations"] = float(market_row["registrations"])
            out.loc[idx, "market_trailing_12m_monthly_average"] = float(market_row["market_12m_avg"]) if pd.notna(market_row["market_12m_avg"]) else np.nan
            out.loc[idx, "market_trailing_12m_yoy_growth_pct"] = float(market_row["market_yoy_pct"]) if pd.notna(market_row["market_yoy_pct"]) else np.nan
            out.loc[idx, "market_growth_match_status"] = "Exact state/month; broad state-level scope"

    market_growth = pd.to_numeric(out["market_trailing_12m_yoy_growth_pct"], errors="coerce")
    growth_market_gap = dealer_growth - market_growth
    score_growth = dealer_growth.copy()
    if market_scope_compatible:
        score_growth = (dealer_growth - market_growth.where(market_growth.notna(), 0.0)).where(market_growth.notna(), dealer_growth)
    growth_score = (50.0 + 2.0 * score_growth).clip(0.0, 100.0)
    growth_score = growth_score.where(dealer_growth.notna())
    growth_method = pd.Series("Reported dealer YoY growth; matched market trend is context only", index=out.index, dtype="string")
    growth_method.loc[market_growth.notna() & dealer_growth.notna()] = "Reported dealer YoY growth scored directly; state-market trend shown separately due scope mismatch"
    if market_scope_compatible:
        growth_method = pd.Series("Reported dealer YoY growth; no aligned market trend", index=out.index, dtype="string")
        growth_method.loc[market_growth.notna() & dealer_growth.notna()] = "Dealer YoY growth less manager-confirmed comparable state registration YoY growth"
    out["dealer_reported_growth_pct"] = dealer_growth
    out["growth_market_comparison_gap_pp"] = growth_market_gap
    out["market_adjusted_growth_pp"] = (dealer_growth - market_growth).where(market_growth.notna()) if market_scope_compatible else np.nan
    out["growth_score_method"] = growth_method

    # Inventory score uses the exact requested 120-day midpoint. Linear bounds
    # are explicit: 0 days => 100, 120 => 50, 240+ => 0.
    inventory_days = _first_numeric(out, ("inventory_days", "stock_days"))
    inventory_score = (50.0 + (120.0 - inventory_days) * (100.0 / 240.0)).clip(0.0, 100.0)
    inventory_score = inventory_score.where(inventory_days.notna())
    out["inventory_ageing_days_used"] = inventory_days

    # Healthy peers require at least 70/100 on both target and active growth
    # performance. Reference medians are month-aligned; same-region
    # references are used when at least three peers qualify.
    good_sales = target_score.ge(GOOD_TARGET_SCORE) & growth_score.ge(GOOD_GROWTH_SCORE)
    growth_good = growth_score.ge(GOOD_GROWTH_SCORE)
    regions = out[region_col] if region_col else pd.Series("", index=out.index)

    payment_days = _first_numeric(out, ("average_payment_days", "payment_delay_days", "payment_days"))
    payment_ref, payment_ref_n, payment_ref_method = _cohort_reference(payment_days, good_sales, regions)
    payment_risk = _risk_vs_reference(payment_days, payment_ref, zero_floor=30.0)

    complaint_rate = _first_numeric(out, ("complaints_per_100_retail_sales", "complaints_rate"))
    if complaint_rate.notna().sum() == 0 and "customer_complaints" in out and "retail_sales_units" in out:
        raw_complaints = _numeric(out, "customer_complaints")
        retail = _numeric(out, "retail_sales_units").replace(0, np.nan)
        complaint_rate = raw_complaints / retail * 100.0
    complaint_ref, complaint_ref_n, complaint_ref_method = _cohort_reference(complaint_rate, growth_good, regions)
    complaint_risk = _risk_vs_reference(complaint_rate, complaint_ref, zero_floor=1.0)

    # FRT and ART are relative lower-is-better percentiles; satisfaction is a
    # higher-is-better percentile. Components are averaged equally. If none of
    # the three is available, the supplied service SLA score is the fallback.
    frt = _numeric(out, "first_response_time_hours")
    art = _numeric(out, "average_resolution_time_hours")
    csat = _numeric(out, "customer_satisfaction_score_5")
    frt_score = _peer_percentile_score(frt, higher_is_better=False)
    art_score = _peer_percentile_score(art, higher_is_better=False)
    csat_score = _peer_percentile_score(csat, higher_is_better=True)
    submetric_scores = pd.concat([frt_score, art_score, csat_score], axis=1)
    service_submetric_count = submetric_scores.notna().sum(axis=1)
    service_score = submetric_scores.mean(axis=1, skipna=True)
    sla = _first_numeric(out, ("service_sla_compliance_pct", "service_sla_pct")).clip(0.0, 100.0)
    service_score = service_score.where(service_submetric_count.gt(0), sla)
    service_method = pd.Series("Service SLA fallback; FRT/ART/CSAT unavailable", index=out.index, dtype="string")
    service_method.loc[service_submetric_count.gt(0)] = service_submetric_count.loc[service_submetric_count.gt(0)].astype(str) + " of 3 service submetrics; equal-weight peer percentiles"

    # Build risk-direction inputs, then consistently anchor every factor to
    # this dataset column: minimum risk 0, median risk 50, maximum risk 100.
    risks = pd.DataFrame(index=out.index)
    risks["Sales versus target"] = 100.0 - target_score
    risks["Less sales growth"] = 100.0 - growth_score
    risks["Payment delays"] = payment_risk
    risks["Inventory ageing"] = 100.0 - inventory_score
    risks["Service performance"] = 100.0 - service_score
    risks["Customer complaints"] = complaint_risk
    raw_risks = risks.copy()
    for factor in risks:
        reference_values = risk_scale_reference[factor] if risk_scale_reference is not None and factor in risk_scale_reference else None
        risks[factor] = _median_anchored_risk(risks[factor], reference_values)

    # Preserve the requested higher-is-healthier performance interpretation
    # for four display factors; payment and complaint scores are already risks.
    factor_scores = pd.DataFrame(index=out.index)
    factor_scores["Sales versus target score"] = 100.0 - risks["Sales versus target"]
    factor_scores["Sales growth score"] = 100.0 - risks["Less sales growth"]
    factor_scores["Inventory ageing score"] = 100.0 - risks["Inventory ageing"]
    factor_scores["Payment delays score"] = risks["Payment delays"]
    factor_scores["Service performance score"] = 100.0 - risks["Service performance"]
    factor_scores["Customer complaints score"] = risks["Customer complaints"]

    weights = pd.Series(SPECIFICATION_WEIGHTS)
    component_coverage = risks.notna().astype(float)
    service_coverage = (service_submetric_count / 3.0).astype(float)
    service_coverage = service_coverage.where(service_submetric_count.gt(0), sla.notna().astype(float) / 3.0)
    component_coverage["Service performance"] = service_coverage
    effective_weights = component_coverage.mul(weights, axis="columns")
    numerator = risks.fillna(0.0).mul(effective_weights).sum(axis=1)
    denominator = effective_weights.sum(axis=1)
    out["attention_score"] = (numerator / denominator.replace(0.0, np.nan)).round(1)
    out["score_coverage_pct"] = (denominator * 100.0).round(0)
    out["priority_band"] = classify_risk_band(out["attention_score"])
    out["payment_reference_median_days"] = payment_ref
    out["payment_reference_n"] = payment_ref_n
    out["payment_reference_method"] = payment_ref_method
    out["complaints_reference_median_per_100"] = complaint_ref
    out["complaints_reference_n"] = complaint_ref_n
    out["complaints_reference_method"] = complaint_ref_method
    out["service_submetrics_used"] = service_submetric_count
    out["service_input_coverage_pct"] = (service_coverage * 100.0).round(0)
    out["service_score_method"] = service_method
    out["factor_score_method"] = "Risk direction; loaded-dataset column minimum=0, median=50, maximum=100"
    for field in raw_risks:
        out[field + " raw risk"] = raw_risks[field]
    out["_specification_factor_scores"] = list(factor_scores.to_dict("records"))
    out["_risk_components"] = list(risks.to_dict("records"))
    for field in factor_scores:
        out[field] = factor_scores[field].round(1)
    for field in risks:
        out[field + " risk"] = risks[field].round(1)
        out[field + " effective weight pct"] = (effective_weights[field] * 100.0).round(1)
    return out, risks
