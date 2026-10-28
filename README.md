# Dealer 360

Streamlit workspace for dealer attention scoring, diagnosis, evidence review, manager reassessment, and action planning.

## Run locally

The default dealer input is `outputs/dealer360_use_case/Dealer360_50_Dealers_3_Years_Specification_v2.xlsx`, a clearly labeled synthetic dataset with 50 fictional dealers and 36 monthly periods. The original synthetic seven-measure sample remains available from the sidebar. The app also loads the bundled observed VAHAN state/UT registration snapshot in `data/Dealer360_State_Market_Demand.xlsx`; a manager can upload another benchmark to replace it for the current session.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

On Windows, activate the environment with `.venv\Scripts\activate`.

## Workbook support

- The specification-model upload contract uses 15 fields: dealer ID, dealer name, month, state, region, retail sales units, sales target units, sales growth YoY %, inventory age in days, payment delay days, FRT hours, ART hours, customer satisfaction (0–5), customer complaints count, and estimated local market potential (units/month). The app calculates target achievement from sales ÷ target and complaints per 100 retail sales from complaint count ÷ retail sales. One unique dealer-month row is required.
- Download the active `Dealer360_Upload_Template_v3.xlsx` for exact headers, units, and ranges. Unsupported columns and duplicate dealer-month rows are blocked; invalid dates, missing identifiers, non-numeric values, out-of-range values, and malformed metrics are reported before analysis.
- The legacy `Monthly_Dealer_KPIs` sheet remains supported when the legacy detailed test workbook is selected.
- `Model_Month_Performance` adds model-level supply, retail, availability, and ageing evidence.
- `Dealer_Master` adds dealer metadata when present.
- `Shipment_Events`, `Receivables_Invoices`, `Service_Cases`, `Customer_Complaints`, and `Regional_Market_Model` appear in supporting-evidence drill-downs when present.
- Dealer operating data can be uploaded as CSV, `.xlsx`, or `.xls`. The seven-category manager upload is validated before scoring. The legacy detailed format and earlier synthetic workbook remain available for testing the preserved original model.
- The bundled VAHAN file contains 864 observed state/UT-month counts, covering Oct 2024–Sep 2026, extracted 28 Oct 2026. The app imports the `VAHAN_Monthly_Raw` tab and maps `period_start`, `geography_name`, `registrations_total`, `geography_level`, `vehicle_scope`, `record_status`, `source_name`, `source_url`, and `extracted_on` through the same validation layer as uploaded benchmarks.
- For an exact state and month match, the app displays observed registrations, the trailing-12-month monthly average, and change versus the prior 12 months. The specification model uses matched state registration growth as a broad directional comparison for the dealer growth score. The bundled extract covers all makers, vehicle categories, vehicle types, and fuels; it cannot establish a dealer catchment, same-segment demand, dealer sales, or dealer market share.
- A separate CSV/Excel upload can replace the bundled benchmark for the current session. Supported fields include period, state/geography, and absolute registration count; optional RTO, vehicle-category/class, fuel, manufacturer, source URL, scope, and observation-status fields are validated and retained. Non-state rows are excluded from state matching, and inputs with non-observed status or mixed vehicle scopes are rejected.
- Source name, URL, extract date, reporting period, geography, vehicle scope, and validation notes are shown in the app. The bundled file is a dated snapshot, not a live connection. The official [VAHAN Public Dashboard](https://www.analytics.parivahan.gov.in/analytics/publicdashboard/vahan?lang=en) provides filters for period, State, RTO, maker, category, fuel and vehicle class; upload a scope-filtered extract when those fields are needed for a like-for-like local-market estimate. SIAM datasets are subject to licensing and redistribution restrictions; upload only data your organization may use.
- A public VAHAN-derived state/month/class/fuel CSV is available from [Dataful](https://dataful.in/datasets/18276/). The app maps `year` + `month`, `state`, `rto`, `vehicle_class`, `fuel`, `value`, and `unit` to the benchmark schema. Dataful notes monthly refreshes and possible differences from current VAHAN dashboard values; it does not supply manufacturer, dealer ID, or dealer catchment identifiers.
- Both new sample and template files are stored under `outputs/dealer360_use_case/`. The dealer sample is synthetic. Its local potential values are modeled estimates and are not dealer sales or observed registrations. The only real observed data bundled is the state-level VAHAN registration snapshot; no real dealer operating records or live registration feed is included.

## Scoring and attention queue

The active manager profile is **specification v3**. Factor risk direction follows the requested rules: lower target achievement and growth, older inventory, longer payment delays, poorer service, and more complaints mean higher risk. After each factor's risk direction is calculated, it is rescaled using all usable dealer-period entries in that factor column across the loaded dataset, so the column minimum maps to 0, the median to 50, and the maximum to 100. Historical back-testing recalibrates at each month using only data available by that month. The overall attention score weights those factor risks: target 5%, growth 5%, payments 24%, inventory 24%, service 30%, complaints 12%. Sales measures are outcome indicators with the smallest individual weights. Diagnosis and action plans prioritize operational risk drivers; sales-recovery actions are generated only when no operational risk or actionable operating signal is present.

Existing metric formulas and references establish factor ordering before the common scale is applied: inventory retains the 120-day direction midpoint; sales growth defaults to reported dealer YoY and can use comparable state-market growth only after explicit scope confirmation; payment and complaints retain the specified good-sales peer cohorts and median references; service FRT and ART use lower-is-better peer percentiles while satisfaction uses a higher-is-better percentile. Tied observations remain tied; if all dealers have the same factor value, all receive 50. Partial service inputs reduce effective service weight and overall score coverage; SLA-only fallback uses one-third service coverage. The bundled VAHAN extract covers all vehicle types/categories and cannot be enabled as like-for-like demand.

Missing factor weights are excluded and the attention score is re-normalized over usable inputs; score coverage is shown. Risk bands are no attention (0–<20), low risk (20–<40), mid-risk (40–<60), and high risk (60+). The separate attention-list cutoff remains strictly **attention score > 50**, and the full dealer roster remains available. Comparison cohorts use the no-attention and low-risk bands above. The market-potential level itself is contextual and is not a separate weighted factor. Back-testing uses the active profile; manual standalone scoring retains the original manual workflow.

## Manager reassessment and audit trail

Saving a workbook reassessment records the original model score and factor scores separately from the manager’s revised factor scores, revised score, manager name, evidence, dealer, and reporting period. Standalone manual assessments are also recorded and explicitly have no original model score. Audit records are held in Streamlit session state, so download the JSON audit log for durable retention. The Audit Trail page can import and append a previously downloaded JSON log. Session state is not a shared or permanent database.

## Streamlit Community Cloud

1. Put this project in a GitHub repository, including `app.py`, `analysis_engine.py`, `data_validation.py`, `requirements.txt`, the `data/Dealer360_State_Market_Demand.xlsx` benchmark, the original legacy workbook, and the complete `outputs/dealer360_use_case/` folder.
2. In Streamlit Community Cloud, create an app from that repository and set the main file path to `app.py`. Select Python 3.11 in the deployment settings to match the local environment.
3. Deploy. The app loads the 50-dealer synthetic workbook and the bundled VAHAN state-demand snapshot by default; managers can download the template, upload an approved dealer workbook, or replace the benchmark extract in the sidebar.

The workbook contains synthetic/sample operational data. Replace it with an approved dataset before using the hosted app for operational decisions. The app does not require secrets or external services.
