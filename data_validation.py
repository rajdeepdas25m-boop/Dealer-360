"""Validation and conservative field mapping for Dealer 360 input data.

The module does not calculate attention scores. It normalizes only explicitly
recognized columns and reports unsupported or ambiguous mappings before the app
uses an upload.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd


DEALER_ALIASES = {
    "dealer_id": ["dealer_id", "dealer_code", "outlet_id"],
    "dealer_name": ["dealer_name", "dealer", "outlet_name"],
    "month": ["month", "reporting_month", "period", "date", "registration_month"],
    "state": ["state", "state_name", "geography", "location_state"],
    "region": ["region", "sales_region"],
    "sales_target_units": ["sales_target_units", "target_units", "monthly_target"],
    "retail_sales_units": ["retail_sales_units", "actual_retail_sales_units", "sales_actual_units", "retail_units"],
    "target_achievement_pct": ["target_achievement_pct", "sales_target_achievement_pct", "sales_vs_target_pct", "sales_versus_target_pct", "sales_vs_target", "sales_versus_target"],
    "sales_growth_yoy_pct": ["sales_growth_yoy_pct", "yoy_sales_growth_pct", "yoy_growth_pct", "sales_growth_yoy", "sales_growth"],
    "inventory_days": ["inventory_days", "stock_days", "inventory_cover_days"],
    "units_over_90_days": ["units_over_90_days", "stock_over_90_days"],
    "units_over_90_days_pct": ["units_over_90_days_pct", "inventory_age_90plus_pct", "inventory_aged_90plus_pct", "inventory_ageing_pct", "inventory_ageing_90plus_pct", "inventory_ageing_90_days"],
    "units_over_180_days": ["units_over_180_days", "stock_over_180_days"],
    "receivables_inr_lakh": ["receivables_inr_lakh", "total_receivables_inr_lakh", "receivables"],
    "overdue_receivables_inr_lakh": ["overdue_receivables_inr_lakh", "overdue_receivables"],
    "overdue_pct_receivables": ["overdue_pct_receivables", "overdue_pct"],
    "average_payment_days": ["average_payment_days", "payment_days", "payment_delay_days", "payment_delays_days"],
    "service_sla_compliance_pct": ["service_sla_compliance_pct", "service_sla_pct", "sla_compliance_pct", "service_performance_pct", "service_performance", "service_performance_sla"],
    "first_response_time_hours": ["first_response_time_hours", "first_response_hours", "frt_hours", "frt"],
    "average_resolution_time_hours": ["average_resolution_time_hours", "average_resolution_hours", "resolution_time_hours", "art_hours", "art"],
    "customer_satisfaction_score_5": ["customer_satisfaction_score_5", "customer_satisfaction_score_0_5", "customer_satisfaction_score", "customer_satisfaction", "csat_score_5", "customer_rating_5"],
    "customer_complaints": ["customer_complaints", "complaints"],
    "complaints_per_100_retail_sales": ["complaints_per_100_retail_sales", "complaints_rate", "customer_complaints_per_100_sales", "customer_complaints_per_100_retail_sales"],
    "estimated_state_market_units_monthly": ["estimated_state_market_units_monthly", "monthly_market_potential_units", "local_market_potential_units", "local_market_potential_units_month", "local_market_potential_units_per_month", "local_market_potential"],
    "manufacturer": ["manufacturer", "maker", "oem"],
    "vehicle_segment": ["vehicle_segment", "segment", "body_style", "vehicle_class", "class"],
}

BENCHMARK_ALIASES = {
    "month": ["month", "registration_month", "period", "month_year", "year_month", "date", "period_start"],
    "year": ["year", "registration_year"],
    "month_name": ["month_name", "month"],
    "state": ["state", "state_name", "geography", "geography_name", "state_ut"],
    "geography_level": ["geography_level"],
    "rto": ["rto", "rto_name", "regional_transport_office"],
    "manufacturer": ["manufacturer", "maker", "oem"],
    "vehicle_segment": ["vehicle_segment", "segment", "vehicle_class", "class", "category"],
    "fuel_type": ["fuel_type", "fuel", "fuel_category"],
    "registrations": ["registrations", "registration_count", "vehicle_count", "value", "count", "total_registrations", "registrations_total"],
    "unit": ["unit", "units", "measure"],
    "last_updated": ["last_updated", "updated_at", "extract_date", "download_date", "extracted_on"],
    "source": ["source", "source_name", "publisher"],
    "source_url": ["source_url", "url"],
    "vehicle_scope": ["vehicle_scope"],
    "record_status": ["record_status"],
}

DEALER_METRIC_COLUMNS = {
    "sales_target_units", "retail_sales_units", "target_achievement_pct", "sales_growth_yoy_pct", "inventory_days",
    "units_over_90_days", "units_over_90_days_pct", "units_over_180_days", "receivables_inr_lakh",
    "overdue_receivables_inr_lakh", "overdue_pct_receivables", "average_payment_days",
    "service_sla_compliance_pct", "customer_complaints", "complaints_per_100_retail_sales", "estimated_state_market_units_monthly",
    "first_response_time_hours", "average_resolution_time_hours", "customer_satisfaction_score_5",
}
PERCENT_COLUMNS = {"overdue_pct_receivables", "service_sla_compliance_pct", "units_over_90_days_pct"}
NONNEGATIVE_COLUMNS = DEALER_METRIC_COLUMNS - {"sales_growth_yoy_pct"}

USE_CASE_ALIASES = {
    "dealer_id": DEALER_ALIASES["dealer_id"],
    "dealer_name": DEALER_ALIASES["dealer_name"],
    "month": DEALER_ALIASES["month"],
    "state": DEALER_ALIASES["state"],
    "region": DEALER_ALIASES["region"],
    "sales_target_units": DEALER_ALIASES["sales_target_units"],
    "retail_sales_units": DEALER_ALIASES["retail_sales_units"],
    "target_achievement_pct": ["sales_vs_target_pct", "sales_versus_target_pct", "sales_vs_target", "sales_versus_target"],
    "sales_growth_yoy_pct": ["sales_growth_yoy_pct", "sales_growth_yoy", "sales_growth"],
    "inventory_days": ["inventory_days", "inventory_ageing_days", "inventory_age_days", "stock_days", "inventory_cover_days"],
    "units_over_90_days_pct": ["units_over_90_days_pct", "inventory_age_90plus_pct", "inventory_aged_90plus_pct", "inventory_ageing_pct", "inventory_ageing_90plus_pct", "inventory_ageing_90_days"],
    "average_payment_days": ["average_payment_days", "payment_delay_days", "payment_delays_days"],
    "service_sla_compliance_pct": ["service_sla_compliance_pct", "service_performance_pct", "service_performance", "service_performance_sla"],
    "first_response_time_hours": ["first_response_time_hours", "first_response_hours", "frt_hours", "frt"],
    "average_resolution_time_hours": ["average_resolution_time_hours", "average_resolution_hours", "resolution_time_hours", "art_hours", "art"],
    "customer_satisfaction_score_5": ["customer_satisfaction_score_5", "customer_satisfaction_score_0_5", "customer_satisfaction_score", "customer_satisfaction", "csat_score_5", "customer_rating_5"],
    "customer_complaints": DEALER_ALIASES["customer_complaints"],
    "complaints_per_100_retail_sales": ["complaints_per_100_retail_sales", "customer_complaints_per_100_sales", "customer_complaints_per_100_retail_sales"],
    "estimated_state_market_units_monthly": ["estimated_state_market_units_monthly", "monthly_market_potential_units", "local_market_potential_units", "local_market_potential_units_month", "local_market_potential_units_per_month", "local_market_potential"],
}


def _key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _map_columns(df: pd.DataFrame, aliases: dict[str, list[str]]) -> tuple[pd.DataFrame, dict[str, str], list[str]]:
    normalized = df.copy()
    mapping: dict[str, str] = {}
    conflicts: list[str] = []
    by_key: dict[str, list[Any]] = {}
    for original in df.columns:
        by_key.setdefault(_key(original), []).append(original)
    for canonical, candidates in aliases.items():
        matches = [original for original in df.columns if _key(original) in {_key(x) for x in candidates}]
        if len(matches) > 1:
            conflicts.append(f"Ambiguous mapping for {canonical}: {', '.join(map(str, matches))}")
        elif matches:
            mapping[canonical] = matches[0]
    return normalized, mapping, conflicts


def _parse_period(series: pd.Series) -> tuple[pd.Series, int]:
    raw = series.astype("string").str.strip()
    # VAHAN/Dataful style can provide separate year and month columns; handled
    # by the caller. Month names are accepted when paired with a year.
    parsed = pd.to_datetime(raw, errors="coerce")
    return parsed.dt.to_period("M").astype("string"), int(parsed.isna().sum())


def _combine_year_month(years: pd.Series, months: pd.Series) -> pd.Series:
    month_text = months.astype("string").str.strip()
    month_number = pd.to_numeric(month_text, errors="coerce")
    names = pd.to_datetime(month_text, format="%B", errors="coerce").dt.month
    short_names = pd.to_datetime(month_text, format="%b", errors="coerce").dt.month
    month_number = month_number.fillna(names).fillna(short_names)
    formatted = month_number.where(month_number.between(1, 12)).astype("Int64").astype("string").str.zfill(2)
    return years.astype("string").str.strip() + "-" + formatted


@dataclass
class ValidationResult:
    accepted: bool
    frame: pd.DataFrame
    mapping: dict[str, str]
    errors: list[str]
    warnings: list[str]
    provenance: dict[str, Any]


def validate_dealer_data(frame: pd.DataFrame, source_name: str, source_kind: str = "uploaded operational data",
                         known_dealer_ids: set[str] | None = None) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    _, mapping, conflicts = _map_columns(frame, DEALER_ALIASES)
    errors.extend(conflicts)
    required = [name for name in ("dealer_id", "month") if name not in mapping]
    if required:
        errors.append("Required dealer fields missing: " + ", ".join(required) + ". Use dealer_id/dealer_code and month/reporting_month.")
    if not (DEALER_METRIC_COLUMNS & set(mapping)):
        errors.append("No recognized operating metrics were found; this file cannot support dealer scoring.")
    ambiguous_currency = [str(c) for c in frame.columns if _key(c) in {"receivables", "total_receivables", "overdue_receivables"}]
    if ambiguous_currency:
        errors.append("Receivables columns do not declare currency/scale: " + ", ".join(ambiguous_currency) + ". Rename them with explicit units such as *_inr_lakh before loading.")

    out = frame.copy()
    for canonical, original in mapping.items():
        if canonical != original:
            out[canonical] = out[original]
    if "dealer_id" in mapping:
        out["dealer_id"] = out["dealer_id"].astype("string").str.strip()
        bad_id = out["dealer_id"].isna() | out["dealer_id"].isin(["", "nan", "None"])
        if bad_id.any(): errors.append(f"{int(bad_id.sum())} row(s) have a missing dealer ID.")
        if known_dealer_ids:
            unknown = sorted(set(out.loc[~bad_id, "dealer_id"].astype(str)) - known_dealer_ids)
            if unknown:
                errors.append(f"{len(unknown)} dealer ID(s) have no match in the supplied Dealer_Master: {', '.join(unknown[:8])}{' …' if len(unknown)>8 else ''}.")
    if "month" in mapping:
        month_values = out["month"].astype("string").str.strip()
        if "year" in mapping and month_values.str.fullmatch(r"[A-Za-z]+|\d{1,2}", case=False, na=False).all():
            out["month"] = _combine_year_month(out[mapping["year"]], month_values)
        periods, bad_dates = _parse_period(out["month"])
        if bad_dates:
            errors.append(f"{bad_dates} row(s) have an unparseable reporting month/date.")
        out["month"] = periods
    if {"dealer_id", "month"}.issubset(out.columns):
        duplicates = out.duplicated(["dealer_id", "month"], keep=False)
        if duplicates.any():
            errors.append(f"Duplicate dealer-month key(s): {int(duplicates.sum())} affected row(s). Resolve duplicates before scoring.")
    for metric in DEALER_METRIC_COLUMNS & set(mapping):
        values = pd.to_numeric(out[metric], errors="coerce")
        raw_present = out[metric].notna()
        invalid = raw_present & values.isna()
        if invalid.any(): errors.append(f"{int(invalid.sum())} non-numeric value(s) in {metric}.")
        if metric in NONNEGATIVE_COLUMNS and (values.dropna() < 0).any(): errors.append(f"{metric} contains negative values; expected non-negative values in the named units.")
        if metric in PERCENT_COLUMNS and ((values.dropna() < 0) | (values.dropna() > 100)).any():
            errors.append(f"{metric} must use percentage points from 0 to 100; fractional or out-of-range values need explicit conversion.")
        out[metric] = values
    recognized_originals={_key(alias) for aliases in DEALER_ALIASES.values() for alias in aliases}
    unsupported=[str(c) for c in frame.columns if _key(c) not in recognized_originals]
    if unsupported:
        warnings.append("Unmapped columns retained but not used in scoring: " + ", ".join(unsupported[:12]) + (" …" if len(unsupported)>12 else ""))
    missing_metrics=sorted(DEALER_METRIC_COLUMNS-set(mapping))
    if missing_metrics:
        warnings.append("Operating metrics not supplied (their score components will be omitted/reweighted by the unchanged engine): " + ", ".join(missing_metrics))
    if "state" not in mapping:
        warnings.append("State is unavailable; external regional benchmark matching will not be possible.")
    if "manufacturer" not in mapping:
        warnings.append("Manufacturer is unavailable in the current Dealer 360 dealer/model schema; manufacturer-level benchmark matching is disabled.")
    provenance = {"source": source_name, "source_kind": source_kind, "reporting_period": ", ".join(sorted(set(out["month"].dropna().astype(str)))) if "month" in out else "Unavailable", "geography": "State-level field supplied" if "state" in mapping else "Unavailable", "metric_status": "Observed operational input, subject to source validation"}
    return ValidationResult(not errors, out, mapping, errors, warnings, provenance)


def validate_use_case_dealer_data(frame: pd.DataFrame, source_name: str, source_kind: str) -> ValidationResult:
    """Validate the raw dealer-month input fields used by the active score model."""
    errors: list[str] = []
    warnings: list[str] = []
    normalized_headers=[_key(c) for c in frame.columns]
    if len(normalized_headers)!=len(set(normalized_headers)):
        errors.append("Duplicate column names after standardizing spaces and punctuation.")
    _, mapping, conflicts = _map_columns(frame, USE_CASE_ALIASES)
    errors.extend(conflicts)
    required=[
        "dealer_id", "dealer_name", "month", "state", "region",
        "sales_target_units", "retail_sales_units", "sales_growth_yoy_pct",
        "inventory_days", "average_payment_days", "first_response_time_hours",
        "average_resolution_time_hours", "customer_satisfaction_score_5",
        "customer_complaints", "estimated_state_market_units_monthly",
    ]
    missing=[field for field in required if field not in mapping]
    if missing:
        errors.append("Required columns missing: "+", ".join(missing)+". Download the Dealer 360 upload template for exact headers.")
    service_fields={"first_response_time_hours", "average_resolution_time_hours", "customer_satisfaction_score_5"}
    allowed_keys={_key(alias) for aliases in USE_CASE_ALIASES.values() for alias in aliases}
    extra=[str(c) for c in frame.columns if _key(c) not in allowed_keys]
    if extra:
        errors.append("Unsupported extra columns: "+", ".join(extra)+". Use the Dealer 360 upload template headers.")

    out=frame.copy()
    for canonical, original in mapping.items():
        if canonical!=original: out[canonical]=out[original]
    if {"retail_sales_units", "sales_target_units"}.issubset(out.columns):
        retail=pd.to_numeric(out["retail_sales_units"],errors="coerce")
        targets=pd.to_numeric(out["sales_target_units"],errors="coerce")
        targets=targets.where(targets>0)
        out["target_achievement_pct"]=retail.div(targets)*100.0
    if {"customer_complaints", "retail_sales_units"}.issubset(out.columns):
        complaints=pd.to_numeric(out["customer_complaints"],errors="coerce")
        retail=pd.to_numeric(out["retail_sales_units"],errors="coerce")
        retail=retail.where(retail>0)
        out["complaints_per_100_retail_sales"]=complaints.div(retail)*100.0
    for field in ("dealer_id","dealer_name","state","region"):
        if field in out:
            out[field]=out[field].astype("string").str.strip()
            bad=out[field].isna()|out[field].isin(["","nan","None"])
            if bad.any(): errors.append(f"{int(bad.sum())} row(s) have missing {field} values.")
    if "month" in mapping:
        periods,bad_dates=_parse_period(out["month"])
        if bad_dates: errors.append(f"{bad_dates} reporting month/date value(s) could not be parsed.")
        out["month"]=periods
    if {"dealer_id","month"}.issubset(out.columns):
        duplicate=out.duplicated(["dealer_id","month"],keep=False)
        if duplicate.any(): errors.append(f"Duplicate dealer-month rows: {int(duplicate.sum())} affected row(s). Keep one record per dealer per month.")
    for field in ("dealer_name","state","region"):
        if {"dealer_id",field}.issubset(out.columns):
            changing=out.groupby("dealer_id",dropna=False)[field].nunique(dropna=True)
            ids=changing[changing>1].index.astype(str).tolist()
            if ids: warnings.append(f"{len(ids)} dealer ID(s) have changing {field} values across periods: {', '.join(ids[:6])}{' …' if len(ids)>6 else ''}.")

    ranges={
        "sales_target_units":(1,100000,"units per month"),
        "retail_sales_units":(0,100000,"units per month"),
        "target_achievement_pct":(0,300,"percentage points"),
        "sales_growth_yoy_pct":(-100,300,"percentage points"),
        "inventory_days":(0,1000,"days"),
        "units_over_90_days_pct":(0,100,"percentage points"),
        "average_payment_days":(0,365,"days"),
        "service_sla_compliance_pct":(0,100,"percentage points"),
        "first_response_time_hours":(0,8760,"hours"),
        "average_resolution_time_hours":(0,8760,"hours"),
        "customer_satisfaction_score_5":(0,5,"points on a 0–5 scale"),
        "customer_complaints":(0,100000,"complaints per month"),
        "complaints_per_100_retail_sales":(0,1000,"complaints per 100 retail sales"),
        "estimated_state_market_units_monthly":(0,1000000,"units per month"),
    }
    required_metric_values=set(required) - {"dealer_id", "dealer_name", "month", "state", "region"}
    for field,(low,high,unit) in ranges.items():
        if field not in out: continue
        raw=out[field]
        values=pd.to_numeric(raw,errors="coerce")
        bad=raw.notna()&values.isna()
        if bad.any(): errors.append(f"{int(bad.sum())} non-numeric value(s) in {field}.")
        outside=values.notna()&((values<low)|(values>high))
        if outside.any(): errors.append(f"{int(outside.sum())} value(s) in {field} fall outside the accepted {low} to {high} {unit} range.")
        if values.notna().sum()==0 and field in required_metric_values:
            errors.append(f"{field} has no usable values.")
        elif field in {"sales_target_units", "retail_sales_units", "customer_complaints", "first_response_time_hours", "average_resolution_time_hours", "customer_satisfaction_score_5"} and values.isna().any():
            errors.append(f"{int(values.isna().sum())} row(s) have missing required values in {field}.")
        elif values.isna().any():
            warnings.append(f"{int(values.isna().sum())} row(s) have missing {field}; scores will omit that factor where no component is available.")
        elif values.notna().sum()==0 and field in mapping:
            warnings.append(f"{field} is present but has no usable values; its scoring component will be unavailable.")
        out[field]=values
    for field in ("sales_target_units", "retail_sales_units", "customer_complaints"):
        if field in out:
            values=pd.to_numeric(out[field],errors="coerce")
            fractional=values.notna()&((values-values.round()).abs()>1e-9)
            if fractional.any(): errors.append(f"{int(fractional.sum())} value(s) in {field} are not whole numbers.")
    if {"customer_complaints", "retail_sales_units"}.issubset(out.columns):
        zero_sales=pd.to_numeric(out["retail_sales_units"],errors="coerce").eq(0)
        if zero_sales.any(): warnings.append(f"{int(zero_sales.sum())} row(s) have zero retail sales; complaint rate is unavailable for those rows.")
    if not service_fields.issubset(mapping):
        warnings.append("One or more service submetrics (FRT, ART, satisfaction) are unavailable; service scoring uses only supplied metrics.")
    if "estimated_state_market_units_monthly" in out and out["estimated_state_market_units_monthly"].isna().all():
        warnings.append("Local market potential is unavailable in every row. Attention scoring remains unaffected; no market comparison will be shown.")
    provenance={"source":source_name,"source_kind":source_kind,
                "reporting_period":", ".join(sorted(set(out["month"].dropna().astype(str)))) if "month" in out else "Unavailable",
                "geography":"State and region supplied","metric_status":"Synthetic sample" if "synthetic" in source_kind.lower() else "Uploaded source values; not independently audited"}
    return ValidationResult(not errors,out,mapping,errors,warnings,provenance)


def validate_market_benchmark(frame: pd.DataFrame, source_name: str) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    _, mapping, conflicts = _map_columns(frame, BENCHMARK_ALIASES)
    errors.extend(conflicts)
    # Resolve year + month-name files (common in public VAHAN extracts).
    month_col = mapping.get("month")
    separate_year = mapping.get("year")
    if month_col is None and separate_year and "month_name" not in mapping:
        errors.append("Required registration period missing; provide month/date or year plus month name.")
    elif month_col is None:
        errors.append("Required registration period missing; provide month/date or year plus month name.")
    for required in ("state", "registrations"):
        if required not in mapping: errors.append(f"Required benchmark field missing: {required}.")
    if "manufacturer" not in mapping:
        warnings.append("Manufacturer is absent; only geography/time/category benchmark comparisons are available.")
    if "vehicle_segment" not in mapping:
        warnings.append("Vehicle category/segment is absent; benchmark is aggregate across the supplied file’s vehicle scope.")
    out = frame.copy()
    for canonical, original in mapping.items():
        if canonical != original:
            out[canonical] = out[original]
    if "geography_level" in out:
        level = out["geography_level"].astype("string").str.strip().str.casefold()
        state_rows = level.str.contains(r"state|union territory|\but\b", regex=True, na=False)
        if not state_rows.any():
            errors.append("The supplied geography level has no state/UT observations; state-level dealer matching is unavailable.")
        elif (~state_rows).any():
            warnings.append(f"{int((~state_rows).sum())} non-state/UT benchmark row(s) were excluded from state-level matching.")
            out = out.loc[state_rows].copy()
    if "record_status" in out:
        status = out["record_status"].astype("string").str.strip().str.casefold()
        if status.isna().any() or not status.eq("observed").all():
            errors.append("The benchmark contains rows not explicitly labeled Observed. Provide an observed-only extract; modeled or estimated values are not accepted as observed registrations.")
    if "vehicle_scope" in out:
        scopes = out["vehicle_scope"].dropna().astype("string").str.strip().unique()
        if len(scopes) > 1:
            errors.append("The benchmark mixes vehicle scopes. Separate scopes before aggregation so registrations are not double-counted.")
        elif len(scopes) == 0:
            warnings.append("Vehicle scope is not supplied; confirm whether counts cover the dealer's vehicle segment before comparing levels.")
        elif any(token in str(scopes[0]).casefold() for token in ("all makers", "all vehicle", "all categories", "all fuels")):
            warnings.append("This is an all-maker/all-vehicle-scope total. Use it as broad state demand context only; it is not a matching dealer segment, catchment estimate, or market-share denominator.")
    if "month" in mapping and separate_year:
        month_values = out[mapping["month"]].astype("string").str.strip()
        if month_values.str.fullmatch(r"[A-Za-z]+|\d{1,2}", case=False, na=False).all():
            out["month"] = _combine_year_month(out[mapping["year"]], month_values)
    elif "month" not in mapping and separate_year and mapping.get("month_name"):
        out["month"] = _combine_year_month(out[mapping["year"]], out[mapping["month_name"]])
    if "month" in out.columns:
        periods, bad_dates = _parse_period(out["month"])
        if bad_dates: errors.append(f"{bad_dates} benchmark row(s) have an unparseable period.")
        out["month"] = periods
    if "state" in out:
        out["state"] = out["state"].astype("string").str.strip()
        if out["state"].isna().any() or out["state"].eq("").any(): errors.append("Benchmark contains missing state/geography values.")
    if "registrations" in out:
        raw = out["registrations"]
        count = pd.to_numeric(raw.astype("string").str.replace(",", "", regex=False), errors="coerce")
        invalid = raw.notna() & count.isna()
        if invalid.any(): errors.append(f"{int(invalid.sum())} registration count(s) are non-numeric.")
        if (count.dropna() < 0).any(): errors.append("Registration counts cannot be negative.")
        out["registrations"] = count
    if {"month", "state", "registrations"}.issubset(out.columns):
        keys = ["month", "state"] + (["rto"] if "rto" in out else []) + (["vehicle_segment"] if "vehicle_segment" in out else []) + (["fuel_type"] if "fuel_type" in out else []) + (["manufacturer"] if "manufacturer" in out else []) + (["vehicle_scope"] if "vehicle_scope" in out else [])
        duplicates = out.duplicated(keys, keep=False)
        if duplicates.any(): errors.append(f"Duplicate benchmark grouping keys ({', '.join(keys)}): {int(duplicates.sum())} affected row(s). Aggregate duplicate source rows only when their definitions are confirmed disjoint.")
    if "unit" in out and out["unit"].notna().any():
        unit_values = sorted(out["unit"].dropna().astype(str).str.strip().unique())
        if any("percent" in u.lower() or "share" in u.lower() for u in unit_values): errors.append("Benchmark unit is a share/percentage; registration counts are required for this comparison.")
        elif any(not any(token in u.lower() for token in ("count", "absolute", "number", "vehicle")) for u in unit_values):
            warnings.append("Benchmark unit is not a recognized absolute registration count; verify its definition before interpreting levels.")
    warnings.append("Market registrations are a regional demand context, not dealer sales, inventory, market share, or dealer-causality evidence.")
    if "manufacturer" in mapping:
        warnings.append("Manufacturer value is retained for filtering, but Dealer 360 has no verified dealer-OEM mapping; do not infer a dealer-manufacturer join.")
    if "vehicle_segment" in mapping:
        warnings.append("Source vehicle categories are kept as supplied; no unverified crosswalk to the workbook’s synthetic model IDs is applied.")
    recognized_benchmark_columns={_key(alias) for aliases in BENCHMARK_ALIASES.values() for alias in aliases}
    unsupported=[str(c) for c in frame.columns if _key(c) not in recognized_benchmark_columns]
    if unsupported:
        warnings.append("Additional benchmark columns retained but not used for matching: " + ", ".join(unsupported[:12]) + (" …" if len(unsupported)>12 else ""))
    updated = mapping.get("last_updated")
    source_col = mapping.get("source")
    source_url_col = mapping.get("source_url")
    scope_values = out["vehicle_scope"].dropna().astype(str).unique().tolist() if "vehicle_scope" in out else []
    level_values = out["geography_level"].dropna().astype(str).unique().tolist() if "geography_level" in out else []
    status_values = out["record_status"].dropna().astype(str).unique().tolist() if "record_status" in out else []
    updated_text = str(out[updated].dropna().iloc[0]) if updated and out[updated].notna().any() else "Not supplied"
    if updated_text != "Not supplied":
        parsed_updated = pd.to_datetime(updated_text, errors="coerce")
        if pd.notna(parsed_updated): updated_text = parsed_updated.strftime("%Y-%m-%d")
    provenance = {"source": str(out[source_col].dropna().iloc[0]) if source_col and out[source_col].notna().any() else source_name,
                  "source_kind": "External public market benchmark; source must be verified by uploader",
                  "reporting_period": ", ".join(sorted(set(out["month"].dropna().astype(str)))) if "month" in out else "Unavailable",
                  "geography": ", ".join(level_values) if level_values else ("State/geography column supplied" if "state" in mapping else "Unavailable"),
                  "last_updated": updated_text,
                  "source_url": str(out[source_url_col].dropna().iloc[0]) if source_url_col and out[source_url_col].notna().any() else "Not supplied",
                  "vehicle_scope": "; ".join(scope_values) if scope_values else "Not supplied",
                  "record_status": ", ".join(status_values) if status_values else "Not supplied",
                  "unit": ", ".join(sorted(out["unit"].dropna().astype(str).unique().tolist())) if "unit" in out and out["unit"].notna().any() else "Vehicle registrations",
                  "metric_status": "Observed registrations as labeled in source; not Dealer 360 operating data" if status_values and all(x.strip().casefold() == "observed" for x in status_values) else "Registration extract; observation status not supplied"}
    return ValidationResult(not errors, out, mapping, errors, warnings, provenance)
