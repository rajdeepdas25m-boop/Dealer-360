import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from pathlib import Path
import json
import importlib
from datetime import datetime, timezone
from html import escape as html_escape
import data_validation as dealer_data_validation
dealer_data_validation = importlib.reload(dealer_data_validation)
validate_dealer_data = dealer_data_validation.validate_dealer_data
validate_market_benchmark = dealer_data_validation.validate_market_benchmark
validate_use_case_dealer_data = dealer_data_validation.validate_use_case_dealer_data
import analysis_engine as dealer_analysis_engine
dealer_analysis_engine = importlib.reload(dealer_analysis_engine)
SPECIFICATION_WEIGHTS = dealer_analysis_engine.SPECIFICATION_WEIGHTS
score_specification = dealer_analysis_engine.score_specification
classify_risk_band = dealer_analysis_engine.classify_risk_band

st.set_page_config(page_title='Dealer 360 | Management Attention', page_icon='🚘', layout='wide')
WEIGHTS = SPECIFICATION_WEIGHTS.copy()
LEGACY_WEIGHTS = WEIGHTS.copy()
SCORE_METHOD_VERSION = 'specification-weighted-v3'
SALES_RISK_FACTORS = {'Sales versus target','Less sales growth'}
OPERATIONAL_RISK_FACTORS = set(WEIGHTS) - SALES_RISK_FACTORS
MATERIAL_OPERATIONAL_RISK = 50.0
FACTOR_SCALE_METHOD = 'dataset-column-min-median-max-risk-v1'
MARKET_SCOPE_COMPATIBLE = False
RECS = {
'Sales versus target':'Treat target achievement as an outcome signal. First check inventory availability, payment constraints, service and complaint patterns; review lead conversion only if operational factors do not explain the result.',
'Less sales growth':'Treat year-on-year growth as an outcome signal. Compare periods and market context, then investigate operational constraints before recommending sales interventions.',
'Inventory ageing':'Review inventory age against the 120-day scoring midpoint and investigate model/variant ageing before changing replenishment.',
'Payment delays':'Create an invoice-wise collection plan, prioritise overdue balances and review credit limits.',
'Service performance':'Audit SLA misses, technician capacity, spare-parts availability and repeat repairs.',
'Customer complaints':'Identify top complaint causes, contact unresolved customers and track complaint rates.'}
ATTENTION_LIST_CUTOFF = 50.0
PROJECT_OUTPUTS = Path(__file__).parent/'outputs'/'dealer360_input_upgrade'
PREVIOUS_PROJECT_OUTPUTS = Path(__file__).parent/'outputs'/'dealer360_use_case'
DEFAULT_WORKBOOK = PROJECT_OUTPUTS/'Dealer360_50_Dealers_3_Years_v3.xlsx'
ORIGINAL_SAMPLE_WORKBOOK = PREVIOUS_PROJECT_OUTPUTS/'Dealer360_50_Dealers_3_Years.xlsx'
DEFAULT_TEMPLATE = PROJECT_OUTPUTS/'Dealer360_Upload_Template_v3.xlsx'
ORIGINAL_TEMPLATE = PREVIOUS_PROJECT_OUTPUTS/'Dealer360_Upload_Template.xlsx'
LEGACY_WORKBOOK = Path(__file__).with_name('Dealer360_Realistic_Backend_Dataset.xlsx')
MARKET_DEMAND_WORKBOOK = Path(__file__).parent/'data'/'Dealer360_State_Market_Demand.xlsx'

def audit_log():
    return st.session_state.setdefault('assessment_audit_log', [])

def record_assessment(event):
    record = {'event_id': f"AUD-{len(audit_log()) + 1:05d}",
              'recorded_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'score_method_version':SCORE_METHOD_VERSION,'model_weights':WEIGHTS.copy(),
              'factor_scale_method':FACTOR_SCALE_METHOD,
              'attention_list_cutoff':'>50', **event}
    audit_log().append(record)
    return record

def json_safe(value):
    if isinstance(value, dict): return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [json_safe(v) for v in value]
    if isinstance(value, (datetime, pd.Timestamp)): return value.isoformat()
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating,)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.bool_,)): return bool(value)
    if pd.isna(value): return None
    return value

st.markdown('''<style>
:root{--ink:#17253a;--muted:#63738a;--line:#e1e7ef;--paper:#f6f8fb;--panel:#ffffff;--blue:#1f4e8c;--blue-soft:#eaf1fa;--teal:#147c78}
.stApp{background:var(--paper);color:var(--ink)}
.block-container{padding-top:1.35rem;padding-bottom:2.5rem;max-width:1320px}
[data-testid="stSidebar"]{background:#fbfcfe;border-right:1px solid #e2e8f0}
[data-testid="stSidebar"]>div:first-child{padding-top:1.2rem}
[data-testid="stSidebar"] [data-testid="stRadio"] label{padding:10px 12px;border-radius:10px;margin:3px 0;font-size:.94rem}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked){background:#e9efff;color:#2447b5;font-weight:700}
.manager-hero{background:linear-gradient(112deg,#172b50 0%,#234581 72%,#176d70 100%);border-radius:16px;padding:22px 26px;margin:0 0 16px;color:#fff;box-shadow:0 8px 22px rgba(28,55,98,.10)}
.manager-hero .eyebrow{color:#c4d5ee!important;text-transform:uppercase;letter-spacing:.12em;font-weight:700;font-size:.72rem}
.manager-hero h1{color:#fff!important;margin:6px 0 4px;font-size:1.8rem;letter-spacing:-.4px;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.manager-hero p{color:#e2eafa!important;margin:0;font-size:.96rem}
.section-heading{font-size:1.08rem;font-weight:750;color:#20314b;margin:0 0 4px}.section-note{font-size:.86rem;color:#6d7c91;margin:0 0 12px}
h1,h2,h3{letter-spacing:-.25px;color:#20314b}h1{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
[data-testid="stMetric"]{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px;box-shadow:0 3px 12px rgba(24,45,75,.035);min-height:102px}
[data-testid="stMetricLabel"]{color:#68788e;font-size:.86rem}[data-testid="stMetricValue"]{color:#1b2b43;font-weight:700}
[data-testid="stVerticalBlockBorderWrapper"]{background:rgba(255,255,255,.82);border:1px solid var(--line);border-radius:16px;padding:14px}
[data-testid="stForm"]{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px}
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,[data-testid="stSelectbox"]>div>div,[data-testid="stTextArea"] textarea{border-radius:10px}
.stButton>button,.stDownloadButton>button{border-radius:12px;font-weight:700;min-height:3.15rem;padding:.65rem 1.15rem;font-size:1rem;color:#20263a!important;background:#fff!important;border:1px solid #c8d1e1!important;box-shadow:0 2px 5px rgba(32,38,58,.06)}
.stButton>button[kind=primary],.stFormSubmitButton>button[kind=primary]{background:#3049bf!important;border-color:#3049bf!important;color:#fff!important;min-height:3.35rem;font-size:1.05rem;box-shadow:0 4px 12px rgba(48,73,191,.2)}
[data-testid='stSidebar'] .stButton>button,[data-testid='stSidebar'] .stDownloadButton>button{background:#fff!important;color:#20263a!important;border:1px solid #c8d1e1!important}
[data-testid="stDataFrame"],[data-testid="stTable"]{border:1px solid var(--line);border-radius:12px;overflow:hidden}
[data-testid="stRadio"]>div[role="radiogroup"]{gap:.4rem;padding:5px;background:#edf1f7;border:1px solid #e1e7ef;border-radius:14px;width:max-content;max-width:100%;flex-wrap:wrap}
[data-testid="stRadio"]>div[role="radiogroup"] label{border-radius:10px;padding:8px 13px;margin:0;color:#53627a!important;font-weight:650;transition:all .15s ease}
[data-testid="stRadio"]>div[role="radiogroup"] label:has(input:checked){background:#fff;color:#1f4e8c!important;box-shadow:0 1px 5px rgba(23,37,58,.12)}
hr{border-color:#dfe4ed}
/* Force readable labels/help text on the light workspace, including selectbox labels */
.stApp, .stApp p, .stApp label, .stApp [data-testid="stWidgetLabel"],
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stCaptionContainer"]{color:#20263a}
.stApp [data-testid="stCaptionContainer"]{color:#586276!important}
.stApp [data-testid="stSelectbox"] label, .stApp [data-testid="stTextInput"] label,
.stApp [data-testid="stNumberInput"] label, .stApp [data-testid="stTextArea"] label,
.stApp [data-testid="stSlider"] label, .stApp [data-testid="stRadio"] label{color:#30384b!important}
.stApp input, .stApp textarea{color:#20263a!important;background:#fff!important}
.stApp [data-baseweb="select"] div{color:#20263a}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] p{color:#20263a!important}
.insight-card{background:#fff;border:1px solid #dce4ee;border-radius:14px;padding:15px 17px;margin:8px 0;box-shadow:0 3px 12px rgba(33,45,75,.04);color:#20263a}
.insight-card .eyebrow{font-size:.78rem;text-transform:uppercase;letter-spacing:.06em;font-weight:700;color:#596782}
.insight-card .headline{font-size:1.15rem;font-weight:750;color:#20263a;margin:5px 0}
.insight-card .body{font-size:.93rem;line-height:1.5;color:#465168}
.action-card{background:linear-gradient(120deg,#fff 0%,#f8f9ff 100%);border:1px solid #d7deed;border-left:5px solid #3049bf;border-radius:15px;padding:17px 19px;margin:10px 0;color:#20263a}
.action-card h4{margin:4px 0 8px;color:#20263a;font-size:1.08rem}
.action-card p{color:#465168;line-height:1.5;margin:5px 0}
.factor-score-label{font-size:.78rem;text-transform:uppercase;letter-spacing:.07em;color:#718096;font-weight:700;margin-top:10px}
.factor-score-value{font-size:1.72rem;line-height:1.1;font-weight:760;letter-spacing:-.035em;color:#1c2d47;white-space:nowrap;margin:2px 0 12px}
.factor-score-value span{font-size:.95rem;font-weight:600;color:#7b8798;letter-spacing:0}
.semantic-positive{color:#15803d!important;font-weight:700}
.semantic-negative{color:#c03935!important;font-weight:700}
.semantic-neutral{color:#475569!important;font-weight:700}
.factor-compare{font-size:.91rem;line-height:1.45;color:#63738a;margin:5px 0 2px}
.factor-compare strong{color:#36465d}
.risk-meter{height:9px;background:#e8edf3;border-radius:8px;overflow:hidden;margin:5px 0 9px}
.risk-meter span{display:block;height:100%;border-radius:8px}
.comparison-card{height:100%;border:1px solid var(--line);border-radius:15px;background:#fff;padding:16px 18px;box-shadow:0 3px 12px rgba(24,45,75,.035)}
.comparison-card .label{font-size:.78rem;text-transform:uppercase;letter-spacing:.07em;color:#718096;font-weight:700}
.comparison-card .value{font-size:1.5rem;font-weight:750;letter-spacing:-.02em;margin:5px 0;color:#1c2d47}
.comparison-card .detail{font-size:.9rem;color:#65748a;line-height:1.4}
@media(max-width:900px){.manager-hero h1{font-size:1.55rem}.block-container{padding-left:1rem;padding-right:1rem}}
@media(max-width:800px){[data-testid="stHorizontalBlock"]{flex-wrap:wrap!important;gap:.75rem!important}[data-testid="stHorizontalBlock"]>[data-testid="column"]{flex:1 1 100%!important;width:100%!important;min-width:100%!important}}
</style>''',unsafe_allow_html=True)
st.sidebar.markdown('### Dealer 360')
st.sidebar.caption('Regional manager workspace')
# Keep every generated plan as a separate workspace so later plans never overwrite earlier ones.
action_plans = st.session_state.setdefault('action_plans', [])
def register_action_plan(source, dealer_id, dealer_label, manual_data, answers):
    base_id = str(dealer_id or '').strip()
    if not base_id or base_id.lower() in {'nan', 'none', 'not provided'}:
        base_id = str(dealer_label or 'UNKNOWN').strip()
    base_label = f'Action Plan ({base_id})'
    same = sum(1 for item in st.session_state.setdefault('action_plans', []) if item.get('base_label') == base_label)
    label = base_label if same == 0 else f'{base_label} · {same + 1}'
    record = {'key': f'plan_{len(st.session_state["action_plans"]) + 1}', 'label': label,
              'base_label': base_label, 'source': source, 'dealer_id': base_id,
              'dealer': str(dealer_label or base_id), 'manual_data': manual_data,
              'answers': dict(answers or {})}
    st.session_state['action_plans'].append(record)
    # Streamlit preserves a keyed selectbox value across reruns, even when its
    # options change. Explicitly point it at the appended plan so creating a
    # manual assessment cannot leave the previous plan selected or appear to
    # replace it.
    st.session_state['active_action_plan_key'] = record['key']
    st.session_state['action_plan_selector'] = label
    return label

nav_pages=['File upload','Manager Overview','Dealer Ranking & Diagnosis','Action Plan','Manual Dealer Score','Methodology']
nav_labels={'File upload':'1 · File upload','Manager Overview':'2 · Overview',
            'Dealer Ranking & Diagnosis':'3 · Selected dealer','Action Plan':'4 · Action plan',
            'Manual Dealer Score':'5 · Manual dealer analysis','Methodology':'6 · Methodology'}
if not st.session_state.get('dealer360_five_tab_workflow'):
    st.session_state['main_navigation']='File upload'
    st.session_state['dealer360_five_tab_workflow']=True
pending=st.session_state.pop('pending_navigation',None)
if pending:
    st.session_state['main_navigation']=pending if pending in nav_pages else 'Action Plan'
if st.session_state.pop('clear_uploaded_file_on_next_run',False):
    st.session_state.pop('uploaded_dealer_file_payload',None)
    st.session_state.pop('dealer_workbook_upload_v2',None)
if st.session_state.get('main_navigation') not in nav_pages:
    st.session_state['main_navigation']='File upload'
page=st.sidebar.radio('WORKSPACE',nav_pages,key='main_navigation',format_func=lambda item:nav_labels[item])

# First workflow step: upload a dealer file or download the blank workbook.
upload=None
if page=='File upload':
    st.markdown('''<div class="manager-hero"><div class="eyebrow">Dealer 360 · regional manager workspace</div><h1>Start with your dealer data</h1><p>Upload your file or use the ready-to-fill Excel template.</p></div>''',unsafe_allow_html=True)
    upload_col,template_col=st.columns([1.4,1],gap='large')
    with upload_col:
        upload_widget=st.file_uploader('Upload dealer data',type=['csv','xlsx','xls'],key='dealer_workbook_upload_v2',help='CSV or Excel. Your file is validated before it is scored.')
    with template_col:
        if DEFAULT_TEMPLATE.exists():
            st.download_button('Download blank Excel template',DEFAULT_TEMPLATE.read_bytes(),
                'Dealer360_Specification_Model_Template.xlsx',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key='download_blank_dealer_template',use_container_width=True)
        if DEFAULT_WORKBOOK.exists():
            st.download_button('Download 50-dealer sample',DEFAULT_WORKBOOK.read_bytes(),
                'Dealer360_50_Dealers_3_Years_Specification_v2.xlsx',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key='download_sample_workflow',use_container_width=True)
    if upload_widget is not None:
        st.session_state['uploaded_dealer_file_payload']={'data':upload_widget.getvalue(),'name':upload_widget.name}
    upload=st.session_state.get('uploaded_dealer_file_payload')
    with st.expander('What the app checks'):
        st.caption('Required columns, duplicates, dates, numeric values, units, ranges and missing data are checked before scoring. The default sample is synthetic. Public registration data is shown only as broad market context, not dealer sales or local catchment demand.')
    if upload is not None:
        st.success(f"Ready to validate: {upload['name']}")
        if st.button('Use the default sample instead',key='clear_uploaded_dealer_file'):
            st.session_state['clear_uploaded_file_on_next_run']=True
            st.rerun()
    sample_choice='50 dealers · 36 months · specification sample'
    with st.expander('Source details (optional)'):
        dealer_source_input=st.text_input('Dealer data source / system',
            st.session_state.get('dealer_source_input_saved','Uploaded file; source not independently verified'),key='workflow_dealer_source')
        dealer_updated_input=st.text_input('Extract date (if known)',
            st.session_state.get('dealer_updated_input_saved',''),key='workflow_dealer_updated')
    st.session_state['dealer_source_input_saved']=dealer_source_input
    st.session_state['dealer_updated_input_saved']=dealer_updated_input
    if st.button('Continue to overview',type='primary',key='continue_to_overview'):
        st.session_state['pending_navigation']='Manager Overview'
        st.rerun()
else:
    upload=st.session_state.get('uploaded_dealer_file_payload')
    sample_choice='50 dealers · 36 months · specification sample'
    dealer_source_input=st.session_state.get('dealer_source_input_saved','Uploaded file; source not independently verified')
    dealer_updated_input=st.session_state.get('dealer_updated_input_saved','')
    if page=='Action Plan' and action_plans:
        plan_options=[item['label'] for item in action_plans]
        active_plan=next((item for item in action_plans if item['key']==st.session_state.get('active_action_plan_key')),action_plans[-1])
        active_index=plan_options.index(active_plan['label'])
        chosen_label=st.selectbox('Action plan',plan_options,index=active_index,key='action_plan_selector')
        plan=next(item for item in action_plans if item['label']==chosen_label)
        st.session_state['active_action_plan_key']=plan['key']
        st.session_state['action_plan_source']=plan['source']
        st.session_state['action_plan_dealer']=plan['dealer']
        st.session_state['action_plan_dealer_id']=plan['dealer_id']
        st.session_state['action_plan_manual_data']=plan.get('manual_data') or {}
        st.session_state['action_plan_answers']=plan.get('answers') or {}

# Downloadable input template
with st.sidebar.expander('Advanced data settings',expanded=False):
    WEIGHTS=SPECIFICATION_WEIGHTS.copy()
    SCORE_METHOD_VERSION='specification-weighted-v3'
    st.session_state['active_score_method_version']=SCORE_METHOD_VERSION
    st.caption('A VAHAN state/UT registrations snapshot is bundled by default (Oct 2024–Sep 2026; extracted 28 Oct 2026). It is observed broad-market context, not a live feed or dealer-catchment estimate. Upload another extract to replace it for this session.')
    benchmark_upload=st.file_uploader('External registrations benchmark (CSV or Excel)',type=['csv','xlsx','xls'],key='market_benchmark_upload')
    benchmark_source_input=st.text_input('Source / publisher override (optional)','',key='benchmark_source_input')
    benchmark_updated_input=st.text_input('Extract date / last updated (if known)','',key='benchmark_updated_input')
    market_scope_confirmed=st.checkbox('Use benchmark growth in the score after confirming scope matches dealer sales',value=False,key='market_scope_confirmed_v2',help='Enable only when the benchmark covers the same vehicle scope and geography as dealer sales. The bundled file is all vehicle types/categories and will remain context-only.')
if upload is not None:
    data_source = upload['data']
    data_source_format = Path(upload['name']).suffix.lower()
    data_source_label = f'Uploaded dealer file: {upload["name"]}'
    use_case_input = True
elif sample_choice=='50 dealers · 36 months · specification sample' and DEFAULT_WORKBOOK.exists():
    data_source = DEFAULT_WORKBOOK
    data_source_format = '.xlsx'
    data_source_label = f'Default workbook: {DEFAULT_WORKBOOK.name}'
    use_case_input = True
elif sample_choice=='50 dealers · 36 months · original sample' and ORIGINAL_SAMPLE_WORKBOOK.exists():
    data_source = ORIGINAL_SAMPLE_WORKBOOK
    data_source_format = '.xlsx'
    data_source_label = f'Original synthetic workbook: {ORIGINAL_SAMPLE_WORKBOOK.name}'
    use_case_input = True
elif LEGACY_WORKBOOK.exists():
    data_source = LEGACY_WORKBOOK
    data_source_format = '.xlsx'
    data_source_label = f'Legacy detailed test workbook: {LEGACY_WORKBOOK.name}'
    use_case_input = False
else:
    data_source = None
    data_source_format = None
    data_source_label = 'No workbook loaded'
    use_case_input = False
synthetic_data = data_source in (DEFAULT_WORKBOOK, ORIGINAL_SAMPLE_WORKBOOK, LEGACY_WORKBOOK)

def col(df,names):
    lookup={str(c).strip().lower().replace(' ','_'):c for c in df.columns}
    return next((lookup[n.lower().replace(' ','_')] for n in names if n.lower().replace(' ','_') in lookup),None)
def numeric(df,names):
    c=col(df,names)
    return pd.to_numeric(df[c],errors='coerce') if c else pd.Series(np.nan,index=df.index,dtype=float)
def market_potential_monthly(df):
    """Return monthly regional same-category market potential.

    Prefer annual market potential and divide by 12. If the workbook already
    supplies a monthly estimate, use that value directly (equivalent to
    annualising it and dividing by 12, without double-dividing it).
    """
    annual = numeric(df, [
        'estimated_annual_market_potential_units', 'annual_market_potential_units',
        'estimated_annual_regional_retail_sales_units', 'annual_regional_category_retail_units',
        'yearly_market_potential_units', 'regional_annual_vehicle_category_sales_units',
        'estimated_state_market_units_yearly', 'estimated_state_market_units_annual'
    ])
    monthly = numeric(df, [
        'estimated_state_market_units_monthly', 'regional_category_retail_units',
        'estimated_regional_retail_sales_units', 'monthly_market_potential_units',
        'estimated_monthly_market_potential_units', 'local_market_potential_units',
        'local_market_potential_units_month', 'local_market_potential_units_per_month', 'local_market_potential'
    ])
    return annual.div(12).where(annual.notna(), monthly)

def scale_risk(s):
    s=pd.to_numeric(s,errors='coerce'); lo,hi=s.quantile(.1),s.quantile(.9)
    if s.notna().sum()==0:return pd.Series(np.nan,index=s.index)
    if pd.isna(lo) or pd.isna(hi) or hi<=lo: lo,hi=s.min(),s.max()
    if pd.isna(lo) or pd.isna(hi) or hi<=lo:return pd.Series(50.,index=s.index)
    return ((s.clip(lo,hi)-lo)/(hi-lo)*100).clip(0,100)

def score_data_legacy(df):
    target=numeric(df,['sales_target_units','target_units']); sales=numeric(df,['retail_sales_units','actual_retail_sales_units','sales_actual_units'])
    ach=sales/target.replace(0,np.nan)*100
    if ach.notna().sum()==0: ach=numeric(df,['target_achievement_pct','sales_target_achievement_pct'])
    growth=numeric(df,['sales_growth_yoy_pct','yoy_sales_growth_pct'])
    aged=numeric(df,['units_over_90_days','stock_over_90_days']); agepct=numeric(df,['units_over_90_days_pct','inventory_age_90plus_pct','inventory_ageing_90_days']); invdays=numeric(df,['inventory_days','stock_days'])
    overdue=numeric(df,['overdue_pct_receivables']); receiv=numeric(df,['receivables_inr_lakh','total_receivables_inr_lakh','receivables']); overdue_amt=numeric(df,['overdue_receivables_inr_lakh','overdue_receivables'])
    overdue=overdue.where(overdue.notna(),overdue_amt/receiv.replace(0,np.nan)*100)
    paydays=numeric(df,['average_payment_days','payment_days']); service=numeric(df,['service_sla_compliance_pct','service_sla_pct'])
    complaints=numeric(df,['complaints_per_100_retail_sales','complaints_rate','customer_complaints'])
    # Regional market potential is a comparison variable only; it never contributes negatively to attention score.
    # 0=healthy, 100=high risk. Relative factors use peer-distribution scaling.
    growthrisk=(-growth).clip(lower=0); growthrisk=(growthrisk/max(float(growthrisk.quantile(.9)) if growthrisk.notna().any() else 1,1)*100).clip(0,100)
    agedrisk=scale_risk(aged); invrisk=scale_risk(invdays)
    comps=pd.DataFrame(index=df.index)
    comps['Sales versus target']=(100-ach.clip(0,150)).clip(0,100)
    comps['Less sales growth']=growthrisk
    comps['Inventory ageing']=pd.concat([agedrisk,scale_risk(agepct),invrisk],axis=1).mean(axis=1,skipna=True)
    comps['Payment delays']=pd.concat([scale_risk(overdue),scale_risk(paydays)],axis=1).mean(axis=1,skipna=True)
    comps['Service performance']=(100-service.clip(0,100)).clip(0,100)
    comps['Customer complaints']=scale_risk(complaints)
    # Local market potential is intentionally excluded from risk scoring.
    active_weights=LEGACY_WEIGHTS
    weights=pd.Series(active_weights)
    nume=comps.mul(weights).sum(axis=1,skipna=True); deno=comps.notna().mul(weights).sum(axis=1)
    out=df.copy(); out['attention_score']=(nume/deno.replace(0,np.nan)).round(1)
    out['priority_band']=classify_risk_band(out.attention_score)
    for c in comps: out[c+' risk']=comps[c].round(1)
    out['_risk_components']=list(comps.to_dict('records'))
    return out,comps

def priority_risk_drivers(risk_values, threshold=50.0):
    """Prioritize operational risks; show sales risks only if operations do not explain the signal."""
    material=[]
    for factor,value in risk_values.items():
        try:
            score=float(value)
        except (TypeError,ValueError):
            continue
        if np.isfinite(score) and score>threshold:
            material.append((factor,score))
    operational=[item for item in material if item[0] in OPERATIONAL_RISK_FACTORS]
    return sorted(operational or material,key=lambda item:item[1],reverse=True)

@st.cache_data(max_entries=12, show_spinner=False)
def active_score_data(df, benchmark=None, factor_scale_reference=None):
    """Apply the selected, versioned profile without altering the legacy engine."""
    if SCORE_METHOD_VERSION=='specification-weighted-v3':
        return score_specification(df, benchmark, market_scope_compatible=MARKET_SCOPE_COMPATIBLE,
                                   risk_scale_reference=factor_scale_reference)
    return score_data_legacy(df)

@st.cache_data(max_entries=8, show_spinner=False)
def build_factor_scale_reference(history, benchmark=None):
    """Collect raw factor risks from every dealer-month for column calibration."""
    if SCORE_METHOD_VERSION!='specification-weighted-v3':
        return None
    month_field=col(history,['month','reporting_month'])
    cohorts=history.groupby(month_field,sort=False) if month_field else [(None,history)]
    scored_cohorts=[]
    for _,cohort in cohorts:
        raw_scored,_=score_specification(cohort.copy(),benchmark,market_scope_compatible=MARKET_SCOPE_COMPATIBLE)
        scored_cohorts.append(raw_scored)
    if not scored_cohorts:
        return None
    return pd.DataFrame({factor:pd.concat([part[factor+' raw risk'] for part in scored_cohorts],ignore_index=True)
                         for factor in SPECIFICATION_WEIGHTS})

def project_dealer_metrics(history, dealer_id_value, id_field, month_field, selected_period):
    """Directional three-month continuation from the latest six observed months."""
    if not id_field or not month_field or history.empty: return pd.DataFrame()
    subset=history[history[id_field].astype(str)==str(dealer_id_value)].copy()
    subset['_period']=pd.to_datetime(subset[month_field],errors='coerce')
    cutoff=pd.to_datetime(str(selected_period),errors='coerce')
    subset=subset[subset['_period'].notna() & (subset['_period']<=cutoff)].sort_values('_period')
    if subset.empty: return pd.DataFrame()
    specs=[
        ('Sales versus target (%)','target_achievement_pct',['sales_target_units','retail_sales_units'],0,300,'higher is stronger'),
        ('Sales growth YoY (%)','sales_growth_yoy_pct',[], -100,300,'negative growth is a concern'),
        ('Inventory age (days)','inventory_days',[],0,1000,'rising inventory age is a concern'),
        ('Payment delays (days)','average_payment_days',[],0,365,'rising delay is a concern'),
        ('Service performance SLA (%)','service_sla_compliance_pct',[],0,100,'falling SLA is a concern'),
        ('Customer complaints per 100 sales','complaints_per_100_retail_sales',[],0,1000,'rising complaint rate is a concern'),
        ('Local market potential (units/month)','estimated_state_market_units_monthly',[],0,1000000,'context only; not dealer sales'),
    ]
    projected=[]
    for label,field,derived_fields,lower,upper,direction in specs:
        values=pd.to_numeric(subset[field],errors='coerce') if field in subset else pd.Series(np.nan,index=subset.index)
        if values.notna().sum()==0 and len(derived_fields)==2:
            numerator=numeric(subset,[derived_fields[0]])
            denominator=numeric(subset,[derived_fields[1]])
            if label.startswith('Sales'): values=numerator/denominator.replace(0,np.nan)*100
            else: values=numerator/denominator.replace(0,np.nan)*100
        if values.notna().sum()==0 and field=='estimated_state_market_units_monthly':
            values=market_potential_monthly(subset)
        valid=pd.DataFrame({'period':subset['_period'],'value':values}).dropna().sort_values('period').tail(6)
        if len(valid)<6: continue
        month_index=valid['period'].dt.year.to_numpy()*12+valid['period'].dt.month.to_numpy()
        x=month_index-month_index[0]
        if len(set(x.tolist()))<6: continue
        y=valid['value'].to_numpy(dtype=float); slope=float(np.polyfit(x,y,1)[0])
        estimate=float(np.clip(y[-1]+3*slope,lower,upper))
        projected.append({'Measure':label,'Latest observed':round(float(y[-1]),1),'3-month directional projection':round(estimate,1),'Change from latest':round(estimate-float(y[-1]),1),'Months used':len(y),'Reading':direction})
    return pd.DataFrame(projected)

def read_uploaded_table(payload, suffix, preferred_sheet=None):
    """Read one uploaded CSV/XLSX table without modifying the supplied file."""
    stream = BytesIO(payload)
    if suffix == '.csv':
        return pd.read_csv(stream)
    book = pd.ExcelFile(stream)
    sheet = next((name for name in book.sheet_names if name.lower() == str(preferred_sheet or '').lower()), book.sheet_names[0])
    return pd.read_excel(book, sheet_name=sheet)

def read_market_benchmark_table(payload, suffix):
    """Read the bundled VAHAN raw tab or a conventional single-table upload."""
    stream=BytesIO(payload)
    if suffix=='.csv': return pd.read_csv(stream)
    book=pd.ExcelFile(stream)
    raw_sheet=next((name for name in book.sheet_names if name.strip().casefold()=='vahan_monthly_raw'),None)
    if raw_sheet: return pd.read_excel(book,sheet_name=raw_sheet,header=3)
    return pd.read_excel(book,sheet_name=book.sheet_names[0])

def state_market_demand_context(frame, state_value, period_value):
    """Return observed state registrations and a trailing 12-month demand run-rate."""
    if frame.empty or not {'month','state','registrations'}.issubset(frame.columns) or not state_value:
        return None
    data=frame.copy()
    data['_period']=pd.to_datetime(data['month'],errors='coerce').dt.to_period('M')
    state_key=str(state_value).strip().casefold()
    data=data[data['state'].astype(str).str.strip().str.casefold()==state_key].dropna(subset=['_period'])
    selected_period=pd.to_datetime(str(period_value),errors='coerce')
    if pd.isna(selected_period): return None
    selected_period=selected_period.to_period('M')
    data['registrations']=pd.to_numeric(data['registrations'],errors='coerce')
    exact=data[data['_period']==selected_period]
    if len(exact)!=1: return None
    monthly_values=data.groupby('_period')['registrations'].sum(min_count=1).sort_index()
    recent_periods=pd.period_range(end=selected_period,periods=12,freq='M')
    prior_periods=pd.period_range(end=selected_period-12,periods=12,freq='M')
    recent=monthly_values.reindex(recent_periods)
    prior=monthly_values.reindex(prior_periods)
    recent_total=float(recent.sum()) if recent.notna().all() else np.nan
    prior_total=float(prior.sum()) if prior.notna().all() else np.nan
    yoy=((recent_total/prior_total)-1)*100 if pd.notna(recent_total) and pd.notna(prior_total) and prior_total>0 else np.nan
    trend=data[(data['_period']<=selected_period)&(data['_period']>=selected_period-23)].copy()
    trend=trend.groupby('_period',as_index=False)['registrations'].sum(min_count=1).sort_values('_period')
    trend['Month']=trend['_period'].astype(str)
    return {'state':str(state_value),'period':selected_period,'registrations':float(exact['registrations'].iloc[0]),
            'trailing_12_total':recent_total,'trailing_12_monthly_average':recent_total/12 if pd.notna(recent_total) else np.nan,
            'trailing_12_yoy_growth_pct':yoy,'trend':trend[['Month','registrations']]}

benchmark_validation = None
benchmark_frame = pd.DataFrame()
benchmark_upload_error = None
benchmark_file_name = None
benchmark_is_bundled = False
if benchmark_upload is not None:
    benchmark_payload=benchmark_upload.getvalue()
    benchmark_suffix=Path(benchmark_upload.name).suffix.lower()
    benchmark_file_name=benchmark_upload.name
elif MARKET_DEMAND_WORKBOOK.exists():
    benchmark_payload=MARKET_DEMAND_WORKBOOK.read_bytes()
    benchmark_suffix=MARKET_DEMAND_WORKBOOK.suffix.lower()
    benchmark_file_name=MARKET_DEMAND_WORKBOOK.name
    benchmark_is_bundled=True
else:
    benchmark_payload=None
    benchmark_suffix=None
if benchmark_payload is not None:
    try:
        benchmark_raw = read_market_benchmark_table(benchmark_payload, benchmark_suffix)
        benchmark_validation = validate_market_benchmark(benchmark_raw, benchmark_file_name or 'Market benchmark')
        benchmark_validation.provenance['source_kind']='Bundled observed VAHAN snapshot' if benchmark_is_bundled else 'Uploaded external market benchmark; uploader-supplied source'
        benchmark_validation.provenance['source_file']=benchmark_file_name
        if benchmark_upload is not None and benchmark_source_input.strip(): benchmark_validation.provenance['source']=benchmark_source_input.strip()+' · '+benchmark_file_name
        if benchmark_upload is not None and benchmark_updated_input.strip(): benchmark_validation.provenance['last_updated']=benchmark_updated_input.strip()
        if benchmark_validation.accepted:
            benchmark_frame = benchmark_validation.frame
            status_label='Bundled VAHAN snapshot' if benchmark_is_bundled else 'Uploaded benchmark'
            st.sidebar.success(f'{status_label} validated · {len(benchmark_frame):,} state/month records')
        else:
            st.sidebar.error(f'Benchmark rejected · {len(benchmark_validation.errors)} validation issue(s)')
    except Exception as exc:
        benchmark_upload_error = f'Could not read benchmark file: {exc}'
        st.sidebar.error('Market-demand workbook could not be read')

benchmark_scope_text=benchmark_validation.provenance.get('vehicle_scope','') if benchmark_validation is not None and benchmark_validation.accepted else ''
benchmark_scope_key=str(benchmark_scope_text).strip().casefold()
broad_market_scope=any(token in benchmark_scope_key for token in ('all makers','all vehicle','all categories','all fuels'))
scope_is_explicit=benchmark_scope_key not in {'','not supplied','unavailable','none'}
MARKET_SCOPE_COMPATIBLE=bool(market_scope_confirmed and benchmark_validation is not None and benchmark_validation.accepted and scope_is_explicit and not broad_market_scope)
if market_scope_confirmed and broad_market_scope:
    st.sidebar.warning('Growth-score adjustment is disabled: the selected benchmark is explicitly broad/all-vehicle scope. It remains available as market context.')
elif market_scope_confirmed and not MARKET_SCOPE_COMPATIBLE:
    st.sidebar.warning('Growth-score adjustment is disabled until an accepted benchmark provides an explicit vehicle-scope label.')

if page=='File upload':
    st.info('Dealer files are validated before they affect scores. Select **Overview** after choosing a file or sample to start the analysis.')
elif page=='Manual Dealer Score':
    st.header('Manual Dealer Attention Score')
    st.caption('Enter real operating figures. This standalone form retains the original six-factor manual scoring workflow; dataset scoring uses the selected model profile.')
    with st.form('manual_score_form'):
        name=st.text_input('Dealer name','Manual assessment')
        manual_dealer_id=st.text_input('Dealer ID (used to label the action-plan tab)','DXXX')
        c1,c2=st.columns(2)
        with c1:
            target=st.number_input('Monthly sales target (units)',min_value=0,value=100,step=10)
            retail=st.number_input('Actual retail sales this month (units)',min_value=0,value=75,step=5)
            prior=st.number_input('Retail sales same month last year (units)',min_value=0,value=80,step=5)
            stock=st.number_input('Current inventory (units)',min_value=0,value=120,step=10)
            over90=st.number_input('Inventory aged over 90 days (units)',min_value=0,value=25,step=5)
            over180=st.number_input('Inventory aged over 180 days (units)',min_value=0,value=8,step=2)
        with c2:
            receiv=st.number_input('Total receivables (₹ lakh)',min_value=0.0,value=20.0,step=1.0)
            overdue=st.number_input('Overdue receivables (₹ lakh)',min_value=0.0,value=8.0,step=1.0)
            paydays=st.number_input('Average payment delay (days)',min_value=0,value=45,step=5)
            sla=st.slider('Service SLA compliance (%)',0,100,80,5)
            complaints=st.number_input('Customer complaints this month',min_value=0,value=8,step=1)
            annual_market=st.number_input('Estimated yearly retail market potential for the same vehicle category in the region (units)',min_value=0,value=9600,step=600)
            retail_market=annual_market/12
            st.caption(f'Calculated monthly market potential: {retail_market:,.0f} units (yearly estimate ÷ 12).')
        submitted=st.form_submit_button('Calculate attention score',type='primary')
    if submitted:
        st.session_state['manual_calculated'] = True
    if submitted or st.session_state.get('manual_calculated', False):
        achievement=(retail/target*100) if target else np.nan
        growth=((retail-prior)/prior*100) if prior else np.nan
        aged_pct=(over90/stock*100) if stock else np.nan
        overdue_pct=(overdue/receiv*100) if receiv else np.nan
        share=(retail/retail_market*100) if retail_market else np.nan
        # Rule-based risk transformations; transparent and editable through calibration weights.
        vals={
          'Sales versus target':float(np.clip(100-achievement,0,100)) if pd.notna(achievement) else np.nan,
          'Less sales growth':float(np.clip(max(0,-growth)*2,0,100)) if pd.notna(growth) else np.nan,
          'Inventory ageing':float(np.clip((aged_pct or 0)*1.5 + (over180/max(stock,1))*100*.5,0,100)) if pd.notna(aged_pct) else np.nan,
          'Payment delays':float(np.clip((overdue_pct or 0)*.7+paydays*.6,0,100)),
          'Service performance':float(100-sla),
          'Customer complaints':float(np.clip(complaints/max(retail,1)*100*5,0,100))}
        active=LEGACY_WEIGHTS; denom=sum(active[k] for k,v in vals.items() if pd.notna(v)); score=sum(vals[k]*active[k] for k in vals if pd.notna(vals[k]))/denom if denom else np.nan
        band='No attention' if score<20 else ('Low-risk' if score<40 else ('Mid-risk' if score<60 else 'High-risk'))
        if submitted:
            record_assessment({
                'assessment_type':'standalone_manual_score','dealer_id':str(manual_dealer_id).strip(),
                'score_method_version':'manual-weighted-six-factor-v2','model_weights':LEGACY_WEIGHTS.copy(),
                'dealer_name':str(name or 'Manual assessment'),'reporting_period':'Manager-entered period',
                'original_model_score':None,'original_model_band':None,
                'manager_inputs':{'target':target,'retail':retail,'prior_year_retail':prior,'stock':stock,
                    'stock_over_90_days':over90,'stock_over_180_days':over180,'receivables_lakh':receiv,
                    'overdue_lakh':overdue,'average_payment_days':paydays,'service_sla_pct':sla,
                    'complaints':complaints,'annual_market_potential':annual_market},
                'manager_factor_scores':vals,'manager_revised_score':score,'manager_revised_band':band,
                'reassessment_reason':'Standalone manual assessment; no original model score was supplied.'
            })
        a,b,c=st.columns(3); a.metric('Dealer',name or 'Manual assessment')
        score_tone='semantic-negative' if score>=40 else 'semantic-positive'
        band_tone='semantic-negative' if score>=40 else 'semantic-positive'
        b.markdown(f'<div class="comparison-card"><div class="label">Attention score</div><div class="value {score_tone}">{score:.1f}<span style="font-size:.9rem"> / 100</span></div></div>',unsafe_allow_html=True)
        c.markdown(f'<div class="comparison-card"><div class="label">Risk category</div><div class="value {band_tone}">{band}</div></div>',unsafe_allow_html=True)
        if submitted:
            st.success('Assessment recorded in the current session audit trail. Download it from Audit Trail to retain it across sessions.')
        st.subheader('Relevant KPI signals')
        signals=[]
        if pd.notna(achievement) and achievement<90: signals.append(('Sales below target',f'{achievement:.1f}% of target','Target achievement is below 90%; validate lead conversion, model mix and target realism.'))
        if pd.notna(growth) and growth<0: signals.append(('Negative year-on-year sales growth',f'{growth:.1f}%','Compare model-level sales, lead volume and conversion with the same period last year.'))
        if pd.notna(growth) and growth>=0: signals.append(('Sales growth',f'+{growth:.1f}%' if growth>0 else '0.0%','Growth is not a negative attention factor; retained as context only.'))
        if stock>0 and over90/stock>=.25: signals.append(('High ageing inventory',f'{over90/stock*100:.1f}% of stock is 90+ days','Check slow-moving models, cancellations, replenishment and local preference mismatch.'))
        if pd.notna(aged_pct) and aged_pct<25: signals.append(('Ageing stock within watch range',f'{aged_pct:.1f}% aged 90+ days','Continue monitoring stock ageing and model-level movement.'))
        if pd.notna(overdue_pct) and overdue_pct>=30: signals.append(('High overdue receivables',f'{overdue_pct:.1f}% of receivables','Review invoice ageing, disputed invoices and collection ownership.'))
        if paydays>=45: signals.append(('Payment delays',f'{paydays} average days','Review oldest unpaid invoices and payment commitments.'))
        if sla<85: signals.append(('Service SLA below benchmark',f'{sla}% compliance','Check parts availability, technician capacity and job backlog.'))
        if retail>0 and complaints/retail*100>=5: signals.append(('Elevated complaints relative to sales',f'{complaints/retail*100:.1f} per 100 sales','Group complaints by issue, model and resolution time.'))
        if retail_market>0:
            market_share=share
            if pd.notna(market_share) and market_share<10: signals.append(('Dealer sales vs estimated monthly regional market',f'{retail} dealer units vs {retail_market:,.0f} estimated monthly category units ({market_share:.1f}% simple ratio)','Comparison only: annual market potential is divided by 12. This ratio is directional and is not dealer market share unless the estimate represents the dealer’s catchment and the sales denominator is market-wide retail sales.'))
        if not signals: signals=[('No major rule-based KPI alert','Current inputs do not cross the displayed watch rules','Use the follow-up questions below to check for risks not captured in the numeric inputs.')]
        cols=st.columns(2)
        for i,(title,value,detail) in enumerate(signals):
            with cols[i%2]:
                tone='semantic-positive' if title.startswith(('No major','Ageing stock within','Sales growth')) else 'semantic-negative'
                st.markdown(f'''<div class="comparison-card"><div style="font-weight:700">{title}</div><div class="value {tone}">{value}</div><div class="detail">{detail}</div></div>''',unsafe_allow_html=True)
        st.subheader('Factor risk breakdown')
        detail=pd.DataFrame({'Factor':list(vals),'Weight':[f'{active[k]*100:.1f}%' for k in vals],'Calculated risk':[round(vals[k],1) if pd.notna(vals[k]) else np.nan for k in vals],'Weighted contribution':[round(vals[k]*active[k],1) if pd.notna(vals[k]) else np.nan for k in vals]})
        detail_style=detail.style.map(lambda value:'color:#c03935;font-weight:700' if pd.notna(value) and value>50 else ('color:#15803d;font-weight:700' if pd.notna(value) else ''),subset=['Calculated risk'])
        st.dataframe(detail_style,width='stretch',hide_index=True)
        st.subheader('Investigate before deciding on actions')
        st.caption('Answer these operational questions to refine the diagnosis. Insights below update from the answers; they are not treated as confirmed causes.')
        q1=st.selectbox('What best explains the sales situation?', ['Not yet known','Low enquiry/footfall','Low conversion despite enquiries','Popular models unavailable','Competitor discounting / new launch','Target may be unrealistic'],key='manual_q_sales')
        q2=st.selectbox('What is the main inventory issue?', ['Not yet known','Specific models/variants are ageing','Stock arrived recently but demand is weak','Stock mix does not match local preference','No material inventory issue'],key='manual_q_stock')
        q3=st.selectbox('Why are payments delayed?', ['Not yet known','Customer/dealer cash-flow issue','Invoice or credit-note dispute','Collection follow-up is weak','Receivables are not actually overdue'],key='manual_q_pay')
        q4=st.selectbox('What is driving service issues or complaints?', ['Not yet known','Spare-parts availability','Technician capacity / skill','Repeat repair / unresolved fault','Delivery or product-expectation issue','No clear service issue'],key='manual_q_service')
        context=st.text_area('Additional evidence (model mix, competitor activity, lead funnel, pending invoices, complaint themes)',key='manual_context',placeholder='Add any facts gathered from the dealer or regional manager...')
        insights=[]
        if q1=='Low enquiry/footfall': insights.append('Prioritise catchment-level lead generation and walk-in trends before assuming a conversion problem.')
        elif q1=='Low conversion despite enquiries': insights.append('Inspect enquiry response time, test rides, quotation follow-up and lost-lead reasons; low conversion is more plausible than low demand alone.')
        elif q1=='Popular models unavailable': insights.append('Check model/variant stockouts and replenishment lead times before reducing the dealer target or marketing activity.')
        elif q1=='Competitor discounting / new launch': insights.append('Compare competitor offer, model positioning and lost-deal feedback; avoid matching discounts without margin analysis.')
        elif q1=='Target may be unrealistic': insights.append('Compare target with prior run-rate, seasonality, catchment demand and dealer capacity before interpreting achievement as execution failure.')
        if q2=='Specific models/variants are ageing' or q2=='Stock mix does not match local preference': insights.append('The inventory signal may be a model-mix problem rather than excess total stock; analyse age by model/variant and local enquiry mix.')
        elif q2=='Stock arrived recently but demand is weak': insights.append('Separate recent stock from aged stock and check whether retail demand, not just dispatch volume, supports replenishment.')
        if q3=='Invoice or credit-note dispute': insights.append('Resolve disputed invoices/credit notes separately from collection escalation; disputed balances may distort the apparent payment-risk signal.')
        elif q3=='Collection follow-up is weak': insights.append('Assign invoice-level owners and dated commitments; compare promised payment dates with actual receipt behaviour.')
        elif q3=='Receivables are not actually overdue': insights.append('Reconcile invoice due dates and credit terms; avoid treating total outstanding receivables as overdue debt.')
        if q4=='Spare-parts availability': insights.append('Compare service backlog and SLA misses with parts fill rate and back-order duration.')
        elif q4=='Technician capacity / skill': insights.append('Compare job arrivals with technician capacity, skill coverage and repeat repair rates by job type.')
        elif q4=='Repeat repair / unresolved fault': insights.append('Audit repeat jobs by model and fault code; repeated repairs may be a stronger quality signal than complaint count alone.')
        elif q4=='Delivery or product-expectation issue': insights.append('Separate delivery-delay complaints from product/service complaints and track resolution time.')
        if context.strip(): insights.append('Additional evidence supplied: '+context.strip())
        if insights:
            st.subheader('Refined diagnostic insights')
            for insight in insights: st.markdown('- '+insight)
        triggered=sorted([(k,v) for k,v in vals.items() if pd.notna(v) and v>=50],key=lambda x:x[1],reverse=True)
        if triggered: st.caption('Numeric risk signals to investigate: '+', '.join(f'{k} ({v:.0f}/100)' for k,v in triggered)+'.')
        else: st.success('No factor crosses the 50/100 numeric action trigger. Use the operational answers to identify emerging issues.')
        st.caption('Regional market estimate is for comparison only and does not increase the attention score. Validate any guesstimate before investment decisions.')
        st.divider()
        st.subheader('Ready to devise an action plan?')
        st.write('Your operating figures, market comparison and answers above will be used to build a dealer-specific plan in a separate workspace.')
        if st.button('Devise action plan',type='primary',key='manual_devise_plan'):
            manual_plan_data={
                'name':str(name or 'Manual assessment'),'target':float(target),'retail':float(retail),'prior':float(prior),
                'stock':float(stock),'over90':float(over90),'over180':float(over180),'receiv':float(receiv),
                'overdue':float(overdue),'paydays':float(paydays),'sla':float(sla),'complaints':float(complaints),
                'annual_market':float(annual_market),'monthly_market':float(retail_market),'score':float(score),'band':band,
                'achievement':float(achievement) if pd.notna(achievement) else None,'growth':float(growth) if pd.notna(growth) else None,
                'overdue_pct':float(overdue_pct) if pd.notna(overdue_pct) else None,'aged_pct':float(aged_pct) if pd.notna(aged_pct) else None,
                'market_ratio':float(share) if pd.notna(share) else None,'risk_values':{k:(float(v) if pd.notna(v) else None) for k,v in vals.items()}}
            manual_answers={'sales':q1,'inventory':q2,'payments':q3,'service':q4,'context':context}
            plan_label=register_action_plan('manual', manual_dealer_id, str(name or 'Manual assessment'), manual_plan_data, manual_answers)
            st.session_state['active_action_plan_key']=st.session_state['action_plans'][-1]['key']
            st.session_state['pending_navigation']='Action Plan'
            st.rerun()

    with st.expander('Assessment audit trail and export'):
        st.caption('Model scores, manager inputs and revised assessments remain separate. Session records can be exported or restored as JSON.')
        audit_upload=st.file_uploader('Restore a previous Dealer 360 audit JSON',type=['json'],key='audit_restore_upload_workflow')
        if audit_upload is not None:
            try:
                payload=json.load(audit_upload)
                imported=payload.get('records',[]) if isinstance(payload,dict) else payload
                if not isinstance(imported,list): raise ValueError('Expected a list of audit records.')
                existing={r.get('event_id') for r in audit_log()}
                additions=[r for r in imported if isinstance(r,dict) and r.get('event_id') not in existing]
                audit_log().extend(additions)
                st.success(f'Imported {len(additions)} new record(s).')
            except Exception as exc:
                st.error(f'Could not import audit records: {exc}')
        records=audit_log()
        if records:
            st.dataframe(pd.DataFrame(records),width='stretch',hide_index=True)
            audit_json=json.dumps(json_safe({'format_version':1,'records':records}),ensure_ascii=False,indent=2).encode('utf-8')
            st.download_button('Download audit log (JSON)',audit_json,'Dealer360_Assessment_Audit.json','application/json')
            st.download_button('Download audit log (CSV)',pd.DataFrame(records).to_csv(index=False).encode('utf-8'),'Dealer360_Assessment_Audit.csv','text/csv')
        else:
            st.info('No assessments have been recorded in this session yet.')

elif page=='Methodology':
    st.markdown('''<div class="manager-hero"><div class="eyebrow">Model transparency</div><h1>Methodology</h1><p>Scoring, analysis rules, recommendation logic, and source validation in one place.</p></div>''',unsafe_allow_html=True)
    st.info('Market data is validated from the bundled or manager-uploaded extract. The bundled VAHAN workbook is a dated snapshot, not a live API/feed. Dealer workbook validation runs on the selected file before that data can be scored.')
    st.subheader('Current scoring profile')
    st.write('Current model weights: '+', '.join(f'{k} ({v*100:.0f}%)' for k,v in WEIGHTS.items())+'.')
    st.caption('Sales versus target and sales growth are outcome signals (5% each). Inventory, payment, service and complaint risks together carry 90% of the attention score.')
    if SCORE_METHOD_VERSION=='specification-weighted-v3':
        st.markdown('**Manager-specified scoring rules**')
        st.markdown('''
- **Risk direction:** lower target achievement, weaker YoY growth, older inventory, longer payment delays, poorer service, and more complaints increase risk. Existing factor-specific rules and eligible peer references establish that direction.
- **Common factor scale:** each factor's risk is rescaled using every usable dealer-period entry in that factor's column across the loaded dataset: the column minimum maps to **0**, the median to **50**, and the maximum to **100**, with separate linear scaling below and above the median. Tied values stay tied. If all usable values are identical, all receive 50. The selected month uses these same dataset-wide column anchors.
- **Factor inputs:** payment delays use the median from good-sales peers (target and growth scores ≥70); complaints use the median among dealers with growth score ≥70. Same-region peers are used when at least 3 qualify, otherwise the full qualifying period cohort. Service uses available FRT and ART (lower is better) and satisfaction (higher is better), averaged equally, or the SLA fallback when those details are absent. Inventory retains the 120-day risk direction before cohort rescaling. Growth uses reported dealer YoY by default; compatible market growth adjusts it only after explicit scope confirmation.
- **Overall attention score:** weighted mean of the rescaled factor risks at **5% target, 5% growth, 24% payments, 24% inventory, 30% service, and 12% complaints**. Sales measures are outcome indicators and receive the smallest individual weights; operational factors drive diagnosis and action prioritization. The action plan prioritizes operational risks above 50/100 and uses raw operating thresholds and investigation responses to identify other actionable issues. Sales recovery is addressed only when no operational risk or actionable operating issue is present. This is a prioritization rule, not proof that a factor caused the sales outcome. Historical back-testing recalibrates at each month using entries available up to that month to avoid using future data. Missing factor weights are omitted and the remaining weights re-normalized; input coverage is shown with the score. Local market potential is context and is not a separate weighted factor.
''')
        with st.expander('Backend factor calculations',expanded=False):
            st.markdown('''
**Risk direction:** every factor is ultimately expressed as 0–100 where higher means more attention risk.

| Factor | Calculation before common scaling | Direction |
|---|---|---|
| Sales versus target | Achievement = retail units ÷ target units × 100 (unless achievement is supplied); performance is capped at 0–100; risk = 100 − performance. | Lower achievement raises risk; 5% weight. |
| Sales growth | Performance = 50 + 2 × YoY growth percentage points, clipped to 0–100; if scope is explicitly confirmed as comparable, the matched market growth is subtracted first. Risk = 100 − performance. | Stronger growth lowers risk; 5% weight. |
| Inventory age | Performance = 50 + (120 − inventory days) × 100 ÷ 240, clipped to 0–100; risk = 100 − performance. | 120 days is the midpoint; older stock raises risk. |
| Payment delays | Compare payment days with the median among good-sales peers. Raw risk = 50 + 50 × (dealer days − reference median) ÷ max(abs(reference median), 30), clipped to 0–100. | Longer delay raises risk. |
| Service | Calculate peer percentiles for FRT (lower is better), ART (lower is better), and satisfaction (higher is better); average available scores. Use SLA as fallback if all three submetrics are absent. | Lower service performance raises risk after reversing the performance score. |
| Complaints | Convert to complaints per 100 retail sales when needed; compare with the median among peers with good growth. Raw risk = 50 + 50 × (dealer rate − reference median) ÷ max(abs(reference median), 1), clipped to 0–100. | More complaints raise risk. |

Payment reference cohort: target performance ≥70 and growth performance ≥70. Complaint reference cohort: growth performance ≥70. Use same-region eligible peers when at least 3 qualify; otherwise use all qualifying dealers in that reporting period. The common factor scale then maps each usable factor column’s minimum/median/maximum to 0/50/100, linearly on each side of the median. If the column has no spread, usable entries receive 50. Missing values are omitted and weights are re-normalized; service input coverage is adjusted for the available submetrics.
''')
        with st.expander('Overall score, bands, and historical validation',expanded=False):
            st.markdown('''
**Overall attention score** = weighted mean of available factor risk scores using the weights above. The profile version is `specification-weighted-v3`. Risk bands are no attention (0–<20), low risk (20–<40), mid-risk (40–<60), and high risk (60+). The Overview attention list uses a separate strict cutoff of **score >50**.

Historical scoring/back-test recomputes factor scaling using information available through each historical month to avoid future-data leakage. Its deterioration chart checks whether an earlier risk flag preceded a later deterioration; it is a descriptive back-test, not proof of prediction or causation. Directional projections use a straight-line slope from the latest six available months and extend three months, with metric-specific bounds; they are planning signals, not seasonal forecasts.
''')
        with st.expander('Diagnosis and action-plan rules',expanded=False):
            st.markdown('''
1. Rank material factor risks above 50. Operational factors (inventory, payments, service, complaints) take precedence; sales risks are shown as drivers only when no operational factor is above 50.
2. Check operating thresholds and manager investigation answers as well as factor scores. Main operational triggers include inventory above 120 days, 90+ day stock share ≥25%, overdue receivables ≥25%, payment delay >45 days, service SLA <85%, and complaints >5 per 100 sales. A factor risk >50 or an indicated operating issue can also trigger an action.
3. Compare with the dealer’s recent history when at least three prior periods are available (target achievement −10 percentage points, growth −5 points, inventory age +20 days, payment delay +10 days, service SLA −5 points, or complaints +1 per 100 are review thresholds). Deterioration is a signal to investigate, not an attribution.
4. Compare factor risks separately with low-risk (20–<40) and no-attention (0–<20) cohorts; use same-region cohorts when at least 3 peers are available. **Sales versus target is excluded** from this peer comparison. A possible wider-pattern action is raised only when both comparison cohort medians exceed 50 for a factor. The generic “Target dealer-specific gaps” action has been removed; peer comparison remains evidence, not an automatic corrective action.
5. Sales recovery actions are generated only when no operational risk, raw operating threshold, or manager response indicates an operating issue. If shown, sales is still investigated as an outcome: the plan asks managers to validate target realism, lead funnel, model availability and market context before choosing an intervention.
6. Every recommendation is conditional. Owners, review windows, evidence, and caveats accompany actions; scoring and comparisons do not establish causation.

Market-potential comparisons are contextual and never imply dealer sales or market share without aligned catchment/category evidence. The regional market-potential action is a validation prompt; it does not alter attention score.
''')
        with st.expander('Standalone manual assessment calculations',expanded=False):
            st.markdown('''
The standalone Manual Dealer Analysis form uses the same 5/5/24/24/30/12 weights but retains a simpler legacy transform: target risk = clipped (100 − achievement); growth risk = clipped (2 × magnitude of negative YoY growth); inventory risk = clipped (1.5 × 90+ day stock share + 0.5 × 180+ day stock share); payment risk = clipped (0.7 × overdue share + 0.6 × average payment days); service risk = 100 − SLA; complaint risk = clipped (complaints ÷ retail sales × 100 × 5). Available components are weighted and re-normalized. This manual calculation is separate from the dataset-calibrated v3 scoring profile.
''')
        st.warning('The bundled VAHAN benchmark is an observed statewide total across all makers, vehicle types, categories, and fuels. Its broad scope cannot be enabled for growth-score adjustment; it remains context only. It does not establish a dealer market share or causal effect.')
    else:
        st.write('The alternate legacy formula remains available for comparison. It uses the same sales-light factor weights, but retains its original factor transformations and does not use the specification profile or market-adjusted growth transformation.')
        st.write('Weights in the legacy comparison: target 5%, growth 5%, inventory 24%, payments 24%, service 30%, and complaints 12%. Missing components are excluded and remaining weights are re-normalised.')
    with st.expander('Validation protocol and accepted data rules',expanded=False):
        st.markdown('''
**Dealer workbook:** recognized headers are mapped to canonical fields. The use-case file requires dealer ID/name, reporting month, state, region, target and retail units, YoY growth, inventory days, payment days, FRT, ART, satisfaction, complaint count, and monthly market potential. Periods must parse to year-month; duplicate dealer-month rows, missing required values, non-numeric measures, unsupported extra columns, and out-of-range values are rejected. Target, retail and complaint counts must be whole numbers. Main accepted ranges: target 1–100,000 units/month; retail 0–100,000; target achievement 0–300%; growth −100–300%; inventory age 0–1,000 days; payment days 0–365; FRT/ART 0–8,760 hours; satisfaction 0–5; complaints 0–100,000/month; and monthly market potential 0–1,000,000 units. Percent fields use 0–100 percentage points. Missing optional measures are not fabricated and can lower score coverage.

**External benchmark:** require period, state/geography and absolute non-negative registration count. Validate period formats, numeric counts, units, observed status, geography level, vehicle scope, and duplicate grouping keys. Non-observed rows and ambiguous duplicates are rejected. Source, URL, period, scope and extraction date are retained when supplied. Matching is exact state/month; registrations are never converted into dealer sales. The bundled VAHAN snapshot is broad all-maker/all-vehicle scope and remains context only. Uploaded extracts are validated when provided, but this prototype does not perform a live network refresh.
''')
    st.markdown('**Dealer workbook format:** one row per dealer-month with 15 required fields. Enter retail sales units and target units so the app calculates target achievement, and enter complaint count so it calculates complaints per 100 retail sales. Service performance uses FRT, ART, and customer satisfaction (0–5).')
    st.write('The specification sample contains 50 fictional dealers across 36 months, with retail sales and target units, complaint counts, inventory age and service inputs. All sample operating values are synthetic demonstrations. Uploaded operating values are source-reported after structural validation; they are not independently audited.')
    st.write('Missing FRT is never inferred from service case open dates. The current legacy workbook has resolution and satisfaction fields but no first-response timestamp; it therefore cannot produce the full FRT/ART/satisfaction service composite unless the upload supplies those fields.')
    st.markdown('### Evidence types and supported public benchmark')
    st.write('Dealer operating records are used only after required dealer ID, period, geography, seven-measure, duplicate, date, unit and range checks pass. The default 50-dealer workbook is explicitly synthetic, covers 36 complete months, and is illustrative only. Local market potential remains a supplied/modeled estimate and is never treated as observed registrations or dealer sales.')
    st.write('A user-supplied VAHAN snapshot is bundled as a state/UT benchmark: 24 observed monthly totals from Oct 2024 through Sep 2026, extracted 28 Oct 2026. The specification profile uses exact state/month matches to calculate trailing-12-month registrations average and year-over-year change. This is a state-wide run-rate proxy, not a dealer catchment estimate; the extract covers all makers, vehicle categories, vehicle types, and fuels, so do not interpret it as same-segment demand or dealer market share.')
    st.write('The specification model scores reported dealer YoY growth directly by default and displays the VAHAN trend separately. The sidebar allows market adjustment only after a manager confirms comparable vehicle scope and an accepted benchmark supplies an explicit scope label; broad all-vehicle data cannot be enabled. Absolute registrations remain separate from dealer sales. The original six-factor profile does not use the market benchmark in its attention score.')
    st.markdown('[VAHAN public dashboard](https://analytics.parivahan.gov.in/analytics/publicdashboard/vahan) · [VAHAN public report](https://analytics.parivahan.gov.in/analytics/vahanpublicreport) · [SIAM statistical services](https://www.siam.in/statistical-services/statistical-profile)')
    st.markdown('[VAHAN-derived state/month/class/fuel CSV dataset (Dataful)](https://dataful.in/datasets/18276/)')
    st.caption('Supported Dataful column map: year + month → period; state → geography; rto → RTO scope; vehicle_class → raw source category; fuel → raw fuel; value → registrations; unit → count unit. It contains no manufacturer identifier, and its category labels do not map to the project’s synthetic model IDs.')
    st.caption('SIAM model-wise/monthly datasets are paid and redistribution is restricted by SIAM. Upload only a dataset your organization is licensed to use. VAHAN extracts must retain the query/extract date and selected filters.')
    if benchmark_validation is not None:
        st.markdown('**External benchmark validation**')
        if benchmark_validation.accepted:
            st.success(f"Benchmark accepted · {len(benchmark_validation.frame):,} rows · {benchmark_validation.provenance.get('reporting_period','period unavailable')} · Updated/extracted: {benchmark_validation.provenance.get('last_updated','not supplied')}")
        else:
            st.error('Benchmark rejected by validation; it is not used in analysis.')
        st.json({"source": benchmark_validation.provenance, "mapped_columns": benchmark_validation.mapping, "errors": benchmark_validation.errors, "warnings": benchmark_validation.warnings})
    elif benchmark_upload_error:
        st.error(benchmark_upload_error)
    else:
        st.info('No external registration extract is currently supplied. No real-world benchmark values are being used.')
    st.markdown('### Current dealer workbook validation')
    if data_source is None:
        st.info('No dealer workbook is selected. Upload a file or load the sample from the File upload page to see its row-level validation summary here.')
    else:
        try:
            dealer_bytes=bytes(data_source) if isinstance(data_source,(bytes,bytearray)) else Path(data_source).read_bytes()
            if data_source_format=='.csv':
                method_history=pd.read_csv(BytesIO(dealer_bytes))
            else:
                method_book=pd.ExcelFile(BytesIO(dealer_bytes))
                method_names={name.casefold():name for name in method_book.sheet_names}
                method_sheet=next((method_names[name] for name in ['dealer_data','monthly_dealer_kpis','dealer_input'] if name in method_names),method_book.sheet_names[0])
                method_history=pd.read_excel(method_book,sheet_name=method_sheet)
            method_history.columns=[str(c).strip() for c in method_history.columns]
            method_validation=(validate_use_case_dealer_data(method_history,data_source_label,'synthetic sample workbook' if synthetic_data else 'uploaded seven-measure dealer file')
                               if use_case_input else validate_dealer_data(method_history,data_source_label,'legacy workbook'))
            if upload is not None:
                method_validation.provenance['source']=(st.session_state.get('dealer_source_input_saved','').strip() or 'Source not supplied')+' · '+data_source_label
                method_validation.provenance['last_updated']=st.session_state.get('dealer_updated_input_saved','').strip() or 'Not supplied'
            if method_validation.accepted:
                st.success(f"Dealer data accepted · {len(method_validation.frame):,} rows · {method_validation.provenance.get('reporting_period','period unavailable')} · {method_validation.provenance.get('metric_status','status unavailable')}")
            else:
                st.error('Dealer data is blocked from scoring until these validation errors are corrected.')
            st.json({'source':method_validation.provenance,'mapped_columns':method_validation.mapping,'errors':method_validation.errors,'warnings':method_validation.warnings})
        except Exception as exc:
            st.error(f'Could not produce the selected dealer workbook validation summary: {exc}')

elif page=='Audit Trail':
    st.header('Assessment Audit Trail')
    st.caption('Original model values, manager-provided inputs, and revised assessments are stored as separate fields. The log is held in this browser session; download it to retain or transfer it across sessions.')
    audit_upload=st.file_uploader('Restore or append a previous Dealer 360 audit JSON',type=['json'],key='audit_restore_upload')
    if audit_upload is not None and st.button('Import audit records',key='import_audit_records'):
        try:
            payload=json.load(audit_upload)
            imported=payload.get('records',[]) if isinstance(payload,dict) else payload
            if not isinstance(imported,list): raise ValueError('Expected a list of audit records.')
            existing={r.get('event_id') for r in audit_log()}
            additions=[r for r in imported if isinstance(r,dict) and r.get('event_id') not in existing]
            audit_log().extend(additions)
            st.success(f'Imported {len(additions)} new record(s).')
        except Exception as exc:
            st.error(f'Could not import audit records: {exc}')
    records=audit_log()
    if records:
        st.metric('Recorded assessments',len(records))
        st.dataframe(pd.DataFrame(records),width='stretch',hide_index=True)
        audit_json=json.dumps(json_safe({'format_version':1,'records':records}),ensure_ascii=False,indent=2).encode('utf-8')
        st.download_button('Download audit log (JSON)',audit_json,'Dealer360_Assessment_Audit.json','application/json')
        st.download_button('Download audit log (CSV)',pd.DataFrame(records).to_csv(index=False).encode('utf-8'),'Dealer360_Assessment_Audit.csv','text/csv')
    else:
        st.info('No assessments have been recorded in this session yet. Manual score submissions and saved dealer reassessments will appear here.')

elif page in ['Manager Overview','Overview'] and data_source is None:
    st.header('Dealer 360')
    st.write('Choose a data file or sample from the File upload tab to see dealer priorities.')
    st.info('Manual dealer analysis is available independently of an uploaded workbook.')

if page=='Action Plan' and st.session_state.get('action_plan_source')=='manual':
    md=st.session_state.get('action_plan_manual_data',{})
    ans=st.session_state.get('action_plan_answers',{})
    dealer_name=st.session_state.get('action_plan_dealer','Manual assessment')
    dealer_id=st.session_state.get('action_plan_dealer_id', dealer_name)
    st.markdown('''<div class="manager-hero"><div class="eyebrow">Manual assessment</div><p>Evidence-led plan · inputs, diagnosis, actions, and validation checklist</p></div>''',unsafe_allow_html=True)
    st.markdown(f'## Action Plan ({dealer_id})')
    st.caption(f"Attention score · {float(md.get('score',0)):.1f}/100   •   Risk band · {md.get('band','Unclassified')}")
    st.subheader('Management takeaway')
    st.write('This plan combines the entered operating metrics with the investigation responses. Validate hypotheses against dealer records before making credit, inventory or allocation decisions.')
    action_items=[]
    achievement=md.get('achievement'); growth=md.get('growth'); aged_pct=md.get('aged_pct'); overdue_pct=md.get('overdue_pct')
    retail=md.get('retail',0); target=md.get('target',0); stock=md.get('stock',0); over90=md.get('over90',0); over180=md.get('over180',0)
    paydays=md.get('paydays',0); sla=md.get('sla',100); complaints=md.get('complaints',0); market=md.get('monthly_market',0)
    manual_risks=md.get('risk_values',{})
    manual_operational_risk=(
        any(pd.notna(manual_risks.get(k)) and float(manual_risks[k])>MATERIAL_OPERATIONAL_RISK for k in OPERATIONAL_RISK_FACTORS)
        or (aged_pct is not None and aged_pct>=25) or over180>0
        or (overdue_pct is not None and overdue_pct>=25) or paydays>=45
        or sla<85 or (retail>0 and complaints/retail*100>=5)
        or ans.get('inventory') not in (None,'Not yet known','No major inventory issue')
        or ans.get('payments') not in (None,'Not yet known')
        or ans.get('service') not in (None,'Not yet known','No clear service issue')
    )
    if achievement is not None and achievement<90 and not manual_operational_risk:
        sales_answer=ans.get('sales','Not yet known')
        if sales_answer=='Low enquiry/footfall':
            diagnosis='Sales are below target and the reported issue is low enquiry/footfall. This points first to a potential catchment reach or lead-volume gap, not necessarily a closing-skill problem.'
            action='For the next 4 weeks, track enquiries, walk-ins, test rides, quotations and retail conversions weekly by source. Compare with the dealer’s own prior 3-month run-rate and same-region peers. Run targeted local outreach only if enquiry volume is below that baseline; review conversion separately so lead generation is not used to mask a conversion issue.'
        elif sales_answer=='Low conversion despite enquiries':
            diagnosis='The dealer reports adequate enquiries but weak conversion, consistent with a follow-up, offer, product-fit or sales-process bottleneck.'
            action='Audit the last 30 lost leads: response time, test ride completed, quotation issued, follow-up count and loss reason. Set a 24-hour first-response standard and dated follow-up cadence; compare conversion by salesperson and model weekly. Do not increase dispatches until retail conversion and model availability are checked.'
        elif sales_answer=='Popular models unavailable':
            diagnosis='Reported unavailability may be suppressing retail sales even if total inventory appears adequate.'
            action='Create a model/variant availability list with stockout days, lost orders, replenishment lead time and retail run-rate. Prioritise replenishment only for variants with documented lost orders and recurring demand; offset with transfers from dealers holding slow-moving stock where feasible.'
        else:
            gap=max(target-retail,0)
            diagnosis=f'Retail achievement is {achievement:.1f}% of target. The numeric gap is {gap:.0f} units; operational context is “{sales_answer}”.'
            action=f'Set a four-week recovery plan to close up to {gap:.0f} units (about {gap/4:.1f} additional units per week). Split the gap by model, lead source and salesperson. Validate target realism against recent run-rate, local category demand and stock availability before attributing the shortfall to execution.'
        action_items.append(('P1 · Recover retail sales',diagnosis,action,f'Retail {retail:.0f} vs target {target:.0f}; achievement {achievement:.1f}%.','Dealer sales lead + regional manager · Weekly review for 4 weeks'))
    if (aged_pct is not None and aged_pct>=25) or over180>0 or (pd.notna(manual_risks.get('Inventory ageing')) and manual_risks['Inventory ageing']>50) or ans.get('inventory') in ['Specific models/variants are ageing','Stock arrived recently but demand is weak','Stock mix does not match local preference']:
        diagnosis='Ageing inventory may be tying up working capital; the selected context helps distinguish slow demand from a model-mix mismatch.'
        action='Build a model/variant ageing ladder (0–30, 31–60, 61–90, 91–180 and 180+ days) and compare each variant’s on-hand stock with its last 3-month retail run-rate. Transfer variants with high age and weak local movement; protect variants with recurring stockouts. Avoid blanket replenishment cuts or discounting before checking margin and demand.'
        if ans.get('inventory')=='Stock mix does not match local preference':
            action='Prepare a model/variant matrix of current stock, 90+/180+ day units, last 3-month retail sales and local category demand proxy. Identify variants with both high ageing and weak movement for transfer or targeted offers; preserve supply for variants with proven lost orders. Review weekly for 30 days.'
        aged_evidence=f'Inventory {stock:.0f} units; 90+ day {over90:.0f}; 180+ day {over180:.0f}.'
        if aged_pct is not None: aged_evidence+=f' 90+ share {aged_pct:.1f}%.'
        action_items.append(('P1 · Correct inventory mix',diagnosis,action,aged_evidence,'Dealer stock manager + regional supply planner · Weekly review for 30 days'))
    if (overdue_pct is not None and overdue_pct>=25) or paydays>=45 or (pd.notna(manual_risks.get('Payment delays')) and manual_risks['Payment delays']>50) or ans.get('payments') not in ['Not yet known',None]:
        diagnosis='Payment delays need invoice-level separation of genuinely overdue collectible debt, disputes and due-date/credit-term mismatches.'
        pay_answer=ans.get('payments')
        if pay_answer=='Invoice or credit-note dispute': action='Within five working days, reconcile disputed invoices and credit notes against delivery proof and the ledger. Split disputed from undisputed exposure, assign an owner and closure date to each case, then calculate collectible overdue exposure before any credit decision.'
        elif pay_answer=='Collection follow-up is weak': action='Create an invoice-wise collection tracker with amount, days overdue, named owner, promised date and actual receipt. Contact the largest/oldest undisputed balances first, review missed promises twice weekly and escalate only under company credit policy.'
        elif pay_answer=='Customer/dealer cash-flow issue': action='Prepare a cash commitment calendar backed by invoice ageing and actual payment history. Review exposure and revised terms with the authorised credit team; do not rely on verbal promises or relax limits without approval.'
        else: action='Reconcile due dates and contractual credit terms, then prioritise the oldest and largest undisputed invoices. Record dated commitments and review missed promises twice weekly; separate documentation disputes from cash collection issues.'
        pay_evidence=f'Average payment delay {paydays:.0f} days; overdue {md.get("overdue",0):.1f} lakh / receivables {md.get("receiv",0):.1f} lakh.'
        if overdue_pct is not None: pay_evidence+=f' Overdue share {overdue_pct:.1f}%.'
        action_items.append(('P1 · Reduce overdue exposure',diagnosis,action,pay_evidence,'Finance controller + dealer accounts lead · Review in 7 days'))
    if sla<85 or (retail>0 and complaints/retail*100>=5) or any(pd.notna(manual_risks.get(k)) and manual_risks[k]>50 for k in ['Service performance','Customer complaints']) or ans.get('service') not in ['Not yet known',None,'No clear service issue']:
        diagnosis='Service compliance and complaint levels may indicate a backlog, parts constraint, repair-quality issue or expectation mismatch.'
        svc=ans.get('service')
        if svc=='Spare-parts availability': action='Rank open jobs by part number, days waiting and customer impact. Escalate repeat back-orders, communicate committed repair dates, and track backlog ageing and SLA recovery weekly.'
        elif svc=='Technician capacity / skill': action='Compare jobs received versus closed, productive technician hours, skill coverage and backlog by repair type for two weeks. Reassign qualified capacity or provide targeted training to categories driving the backlog.'
        elif svc=='Repeat repair / unresolved fault': action='Audit repeat jobs by model/fault code, inspect a sample of reopened repairs and require technical sign-off on recurring faults. Track repeat-repair rate alongside SLA so faster closure does not compromise quality.'
        else: action='Classify complaints by delivery, product expectation, service quality and resolution delay. Contact high-severity unresolved customers first and review complaint rate per 100 retail units and closure time weekly.'
        action_items.append(('P2 · Restore service reliability',diagnosis,action,f'Service SLA {sla:.0f}%; complaints {complaints:.0f}; complaints per 100 sales {(complaints/max(retail,1)*100):.1f}.','Service manager · Review in 14 days'))
    if market>0:
        ratio=retail/market*100
        market_action=f'Compare the dealer’s {retail:.0f} retail units with estimated monthly same-category market potential of {market:,.0f} units (simple ratio {ratio:.2f}%). Validate catchment and vehicle category against registration/retail data. If below comparable peers while model availability is healthy, test local lead generation and conversion; if stockouts are high, solve availability before spending more on demand generation.'
        action_items.append(('P2 · Validate local market opportunity','The annual regional estimate has been divided by 12 to provide a monthly comparison. A state/region total is not necessarily the dealer catchment, so this ratio is directional rather than confirmed dealer market share.',market_action,f'Annual estimate {md.get("annual_market",0):,.0f} ÷ 12 = {market:,.0f} units/month; simple ratio {ratio:.2f}%.','Regional manager + dealer sales lead · Review in 30 days'))
    if ans.get('context','').strip():
        action_items.append(('Validate field evidence','The additional dealer/manager note is a hypothesis until matched to operational records.','Match the note to lead logs, stockout/model availability, invoice ledger, service cases or complaint records. Quantify the affected units/value and update the plan only after validation: '+ans['context'].strip(),'Source: manual field note','Regional manager · Next review meeting'))
    if not action_items:
        action_items.append(('P1 · Establish a measured baseline','The entered figures do not cross the main action triggers, or some indicators are missing.','Track retail versus target, model-level stock and ageing, overdue invoices, service SLA and complaints weekly for the next month. Use this baseline to identify the first measurable gap before committing to an intervention.','No major action trigger in entered values.','Dealer manager · Review in 14 days'))
    for title,diagnosis,action,evidence,owner in action_items:
        with st.container(border=True):
            action_tone='semantic-negative' if title.startswith('P1') else ('semantic-neutral' if title.startswith('P2') else 'semantic-positive')
            st.markdown(f'<div class="{action_tone}">{html_escape(title)}</div>',unsafe_allow_html=True)
            st.markdown('**Next step**')
            st.write(action)
            st.caption('Owner / review · '+owner)
            with st.expander('Evidence, rationale and limits'):
                st.write('Why this matters: '+diagnosis)
                st.write('Supporting data: '+evidence)
                st.caption('This is a directional recommendation, not proof of cause. Check seasonality, target changes, model mix, supply timing and data completeness.')
    st.subheader('Validation checklist')
    for item in ['Confirm model-level retail, stockout and ageing data for the same month.','Reconcile receivables against invoice due dates and disputed balances.','Validate the local market estimate and catchment before treating it as share.','Record the baseline, owner, due date and measurable outcome before the next review.']:
        st.checkbox(item,key='manual_plan_check_'+str(abs(hash(item))))
    st.download_button('Download this action plan',pd.DataFrame(action_items,columns=['Priority','Diagnosis','Action','Evidence','Owner / review']).to_csv(index=False).encode('utf-8'),f'{str(dealer_name).replace(" ","_")}_Action_Plan.csv','text/csv')
elif data_source is not None and page not in ['File upload','Manual Dealer Score','Methodology','Audit Trail']:
    try:
        if data_source_format == '.csv':
            history=read_uploaded_table(data_source,data_source_format)
            model_history=pd.DataFrame(); evidence_sheets={}; master=pd.DataFrame()
        else:
            workbook_source=BytesIO(data_source) if isinstance(data_source,(bytes,bytearray)) else data_source
            xls=pd.ExcelFile(workbook_source); names={s.lower():s for s in xls.sheet_names}
            model_history=pd.read_excel(xls,sheet_name=names['model_month_performance']) if 'model_month_performance' in names else pd.DataFrame()
            evidence_sheets={}
            for evidence_sheet in ['Shipment_Events','Receivables_Invoices','Service_Cases','Customer_Complaints','Regional_Market_Model']:
                if evidence_sheet.lower() in names:
                    evidence_sheets[evidence_sheet]=pd.read_excel(xls,sheet_name=names[evidence_sheet.lower()])
            if 'dealer_data' in names:
                history=pd.read_excel(xls,sheet_name=names['dealer_data']); master=pd.DataFrame()
            elif 'monthly_dealer_kpis' in names:
                history=pd.read_excel(xls,sheet_name=names['monthly_dealer_kpis'])
                master=pd.read_excel(xls,sheet_name=names['dealer_master']) if 'dealer_master' in names else pd.DataFrame()
            elif 'dealer_input' in names: history=pd.read_excel(xls,sheet_name=names['dealer_input']); master=pd.DataFrame()
            else: history=pd.read_excel(xls,sheet_name=xls.sheet_names[0]); master=pd.DataFrame()
        history.columns=[str(c).strip() for c in history.columns]
        known_ids=set(master[col(master,['dealer_id','dealer_code'])].dropna().astype(str).str.strip()) if not master.empty and col(master,['dealer_id','dealer_code']) else None
        if use_case_input:
            validation=validate_use_case_dealer_data(history,data_source_label,'synthetic sample workbook' if synthetic_data else 'uploaded seven-measure dealer file')
            if upload is not None:
                validation.provenance['source']=(dealer_source_input.strip() or 'Source not supplied')+' · '+data_source_label
                validation.provenance['last_updated']=dealer_updated_input.strip() or 'Not supplied'
            else:
                validation.provenance['source']=data_source_label
                validation.provenance['last_updated']='Not applicable · synthetic sample'
        else:
            validation=validate_dealer_data(history,data_source_label,'legacy synthetic workbook',known_dealer_ids=known_ids)
        if not validation.accepted:
            st.error('Dealer data is blocked from analysis until validation errors are resolved.')
            for issue in validation.errors: st.write('• '+issue)
            st.stop()
        history=validation.frame
        factor_scale_reference=build_factor_scale_reference(history,benchmark_frame)
        if validation.warnings:
            with st.expander('Dealer data mapping and validation notes'):
                st.write('Mapped fields:',validation.mapping)
                st.write('Data provenance:',validation.provenance)
                for note in validation.warnings: st.write('• '+note)
        monthcol=col(history,['month','reporting_month'])
        if monthcol:
            history[monthcol]=history[monthcol].astype(str); months=sorted(history[monthcol].dropna().unique())
            selected=st.sidebar.selectbox('Reporting month',months,index=len(months)-1)
            current=history[history[monthcol]==selected].copy()
        else: selected='Uploaded snapshot'; current=history.copy()
        scored,components=active_score_data(current,benchmark_frame,factor_scale_reference)
        idcol=col(scored,['dealer_id','dealer_code']) or col(scored,['dealer_name','dealer','outlet_name'])
        namecol=col(scored,['dealer_name','dealer','outlet_name']) or idcol
        if not namecol: scored['Dealer']='Dealer'; namecol='Dealer'
        if not idcol: idcol=namecol
        scored['Dealer display']=scored[namecol].astype(str)
        if page=='Manager Overview' and not st.session_state.get('show_advanced_analytics',False):
            score_series=pd.to_numeric(scored['attention_score'],errors='coerce')
            ranked=scored.assign(_score=score_series).sort_values('_score',ascending=False)
            high=ranked[ranked['_score']>=60].copy()
            mid=ranked[(ranked['_score']>=40)&(ranked['_score']<60)].copy()
            factor_cols=[f+' risk' for f in WEIGHTS if f+' risk' in scored.columns]
            if factor_cols:
                high['Leading driver']=high.apply(lambda r: (priority_risk_drivers({f:r.get(f+' risk',np.nan) for f in WEIGHTS}) or [('No material driver',0)])[0][0],axis=1)
                mid['Leading driver']=mid.apply(lambda r: (priority_risk_drivers({f:r.get(f+' risk',np.nan) for f in WEIGHTS}) or [('No material driver',0)])[0][0],axis=1)
            st.markdown('''<div class="manager-hero"><div class="eyebrow">Regional manager overview</div><h1>Dealers needing attention</h1><p>High-risk dealers are shown first. Mid-risk dealers remain visible in a quieter list.</p></div>''',unsafe_allow_html=True)
            metric_status='Synthetic sample' if synthetic_data else 'Uploaded data'
            st.caption(f'{selected} · {len(scored)} dealers · {metric_status} · Bands: no attention 0–<20, low risk 20–<40, mid-risk 40–<60, high risk 60+')
            st.subheader(f'High risk · {len(high)} dealers')
            if high.empty:
                st.success('No high-risk dealers this period.')
            else:
                card_cols=st.columns(2)
                for ix,(_,dealer_row) in enumerate(high.iterrows()):
                    driver=dealer_row.get('Leading driver','Risk driver unavailable')
                    with card_cols[ix%2]:
                        with st.container(border=True):
                            st.markdown(f"**{dealer_row['Dealer display']}**  ·  <span class='semantic-negative'><b>{dealer_row['_score']:.1f}/100</b></span>",unsafe_allow_html=True)
                            st.caption(f"Primary risk: {driver}")
                            if st.button('Review dealer',key=f"overview_high_{dealer_row.get(idcol,ix)}"):
                                st.session_state['diagnosis_dealer']=dealer_row['Dealer display']
                                st.session_state['pending_navigation']='Dealer Ranking & Diagnosis'
                                st.rerun()
            st.subheader(f'Mid risk · {len(mid)} dealers')
            if mid.empty:
                st.caption('No dealers in the mid-risk band (score 40 to <60).')
            else:
                mid_cols=[c for c in ['Dealer display',idcol,'_score','Leading driver'] if c in mid.columns]
                mid_display=mid[mid_cols].rename(columns={'_score':'Attention score'})
                mid_style=mid_display.style.map(lambda _: 'color:#c03935;font-weight:700',subset=['Attention score'])
                st.dataframe(mid_style,width='stretch',hide_index=True,
                    column_config={'Attention score':st.column_config.NumberColumn(format='%.1f')})
            choices=ranked['Dealer display'].astype(str).tolist()
            if st.session_state.get('diagnosis_dealer') not in choices:
                st.session_state.pop('diagnosis_dealer',None)
            with st.container(border=True):
                diagnosis_choice=st.selectbox('Select a dealer for detailed analysis',choices,key='overview_dealer_choice')
                if st.button('Open selected dealer →',type='primary',key='overview_open_diagnosis'):
                    st.session_state['diagnosis_dealer']=diagnosis_choice
                    st.session_state['pending_navigation']='Dealer Ranking & Diagnosis'
                    st.rerun()
            if st.button('Open advanced analytics & back-test',key='open_advanced_analytics'):
                st.session_state['show_advanced_analytics']=True
                st.rerun()
        elif page=='Overview' or (page=='Manager Overview' and st.session_state.get('show_advanced_analytics',False)):
            st.markdown('''<div class="manager-hero"><div class="eyebrow">Analytical evidence</div><h1>Model analytics & back-test</h1><p>Explore score distributions, factor patterns, and historical deterioration validation.</p></div>''',unsafe_allow_html=True)
            if st.button('← Back to overview',key='close_advanced_analytics'):
                st.session_state['show_advanced_analytics']=False
                st.rerun()
            st.caption(f'Reporting period · {selected}   •   Data source · {data_source_label}')
            threshold_default=50
            # Create a next-month outcome from the operational measures the loaded file actually supplies.
            hm=col(history,['month','reporting_month']); hd=col(history,['dealer_id','dealer_code','dealer_name'])
            hist_eval=None; best_threshold=threshold_default; best_f1=0
            if hm and hd:
                hc=history.copy(); hc['_month']=pd.to_datetime(hc[hm],errors='coerce').dt.to_period('M').dt.to_timestamp()
                hc['_dealer_key']=hc[hd].astype(str); hc=hc.dropna(subset=['_month']).sort_values(['_dealer_key','_month'])
                achc=numeric(hc,['target_achievement_pct','sales_target_achievement_pct'])
                if achc.isna().all():
                    tarc=numeric(hc,['sales_target_units','target_units']); salc=numeric(hc,['retail_sales_units','actual_retail_sales_units']); achc=salc/tarc.replace(0,np.nan)*100
                def first_populated_metric(candidates):
                    for candidate in candidates:
                        values=numeric(hc,[candidate])
                        if values.notna().any(): return values
                    return pd.Series(np.nan,index=hc.index,dtype=float)
                growthc=first_populated_metric(['sales_growth_yoy_pct','yoy_sales_growth_pct','sales_growth'])
                invc=first_populated_metric(['inventory_days','stock_days','units_over_90_days_pct','inventory_age_90plus_pct','units_over_90_days','stock_over_90_days'])
                payc=first_populated_metric(['overdue_pct_receivables','average_payment_days','payment_days'])
                slac=first_populated_metric(['service_sla_compliance_pct','service_sla_pct'])
                complaintc=first_populated_metric(['complaints_per_100_retail_sales','complaints_rate','customer_complaints_per_100_sales'])
                metrics={'Sales versus target':achc,'Sales growth':growthc,'Inventory ageing':invc,
                         'Payment delays':payc,'Service performance':slac,'Customer complaints':complaintc}
                conditions=pd.DataFrame(index=hc.index)
                for label,values in metrics.items():
                    following=values.groupby(hc['_dealer_key']).shift(-1)
                    comparable=values.notna() & following.notna()
                    event=pd.Series(np.nan,index=hc.index,dtype=float)
                    if label in ['Sales versus target','Service performance']:
                        event.loc[comparable]=(following.loc[comparable] <= values.loc[comparable]*0.80).astype(float)
                    elif label=='Sales growth':
                        # Growth can cross zero, so use a percentage-point drop rather than a relative ratio.
                        event.loc[comparable]=(following.loc[comparable] <= values.loc[comparable]-20).astype(float)
                    elif label in ['Inventory ageing','Payment delays','Customer complaints']:
                        base=values.loc[comparable]
                        later=following.loc[comparable]
                        event.loc[comparable]=np.where(base>0,later>=base*1.20,later>base).astype(float)
                    conditions[label+' deterioration']=event
                measured=conditions.notna().any(axis=1)
                hc['_deterioration']=conditions.fillna(False).astype(bool).any(axis=1).where(measured,np.nan)
                hc['_has_next']=hc.groupby('_dealer_key')['_month'].shift(-1).eq(hc['_month']+pd.offsets.MonthBegin(1))
                # Use only observations available up to each month when validating
                # historical scores, avoiding future-data leakage in calibration.
                score_rows=[]
                for m,g in history.groupby(hm,sort=True):
                    as_of_history=history[pd.to_datetime(history[hm],errors='coerce')<=pd.to_datetime(m)]
                    as_of_scale=build_factor_scale_reference(as_of_history,benchmark_frame)
                    tmp,_=active_score_data(g.copy(),benchmark_frame,as_of_scale); tmp['_month_label']=str(m); tmp['_dealer_key']=g[hd].astype(str).values
                    score_rows.append(tmp[['_month_label','_dealer_key','attention_score']])
                if score_rows:
                    allscores=pd.concat(score_rows,ignore_index=True)
                    hc['_month_label']=hc[hm].astype(str)
                    hc=hc.merge(allscores,on=['_month_label','_dealer_key'],how='left')
                    eligible=hc[hc['_has_next'] & hc['_deterioration'].notna() & hc['attention_score'].notna()].copy()
                    if len(eligible):
                        # Chronological holdout: tune on earlier months and evaluate later months.
                        unique_months=sorted(eligible['_month'].dropna().unique())
                        split_idx=max(1,min(len(unique_months)-1,int(len(unique_months)*0.70))) if len(unique_months)>1 else 0
                        if len(unique_months)>1:
                            cutoff=unique_months[split_idx]
                            train=eligible[eligible['_month']<cutoff].copy()
                            hist_eval=eligible[eligible['_month']>=cutoff].copy()
                        else:
                            train=eligible.copy(); hist_eval=eligible.copy()
                        if train.empty: train=eligible.copy()
                        # A threshold cannot be learned if the training window has only one outcome class.
                        if train['_deterioration'].nunique()>1:
                            for t in range(20,81,5):
                                pred=train['attention_score']>=t; actual=train['_deterioration'].astype(bool)
                                tp=int((pred & actual).sum()); fp=int((pred & ~actual).sum()); fn=int((~pred & actual).sum())
                                precision=tp/(tp+fp) if tp+fp else 0; recall=tp/(tp+fn) if tp+fn else 0
                                f1=2*precision*recall/(precision+recall) if precision+recall else 0
                                if f1>best_f1: best_f1=f1; best_threshold=t
            threshold=st.slider('Attention score criterion — flag dealers scoring at or above',0,100,int(st.session_state.get('attention_threshold_v2', best_threshold)),5,key='attention_threshold_v2',help='A prototype threshold is tuned only when the earlier training period contains both outcome classes; otherwise it stays at 50. Historical fit does not guarantee future accuracy.')
            scored['Flag status']=np.where(scored.attention_score>=threshold,'Flagged','Below criterion')
            scored['Risk category']=classify_risk_band(scored.attention_score)
            k1,k2,k3,k4,k5=st.columns(5)
            k1.metric('Dealers analysed',len(scored)); k2.metric('Flagged at selected criterion',int((scored.attention_score>=threshold).sum())); k3.metric('Attention criterion',f'≥ {threshold}/100'); k4.metric('Attention list (>50)',int((scored.attention_score>ATTENTION_LIST_CUTOFF).sum())); k5.metric('Reporting period',str(selected))
            st.subheader('Risk distribution')
            dist=scored.groupby('Risk category',observed=False).attention_score.agg(['count','mean']).reindex(['No attention','Low-risk','Mid-risk','High-risk']).reset_index()
            cc=st.columns(4)
            for i,r in dist.iterrows():
                avg=f"Mean score {r['mean']:.1f}" if pd.notna(r['mean']) else 'No scored dealers'
                cc[i].metric(str(r['Risk category']),f"{int(r['count'])} dealers",avg)
            st.subheader('What is driving underperformance?')
            factor_cols=[f+' risk' for f in WEIGHTS if f+' risk' in scored.columns]
            if factor_cols:
                scored['Primary contributing factor']=scored.apply(lambda r: (priority_risk_drivers({f:r.get(f+' risk',np.nan) for f in WEIGHTS}) or [('No material driver',0)])[0][0],axis=1)
                factor_groups=scored.groupby('Primary contributing factor',dropna=False).agg(Dealer_count=('Dealer display','count')).reset_index().sort_values('Dealer_count',ascending=False)
                st.plotly_chart(px.bar(factor_groups,x='Primary contributing factor',y='Dealer_count',text='Dealer_count',title='Dealers grouped by their highest-risk factor'),width='stretch')
            st.subheader('Did prior-month attention capture next-month deterioration?')
            st.caption('The holdout compares each dealer-month score with the same dealer’s next month. A case is counted when any available operating signal crosses its deterioration rule; local market potential is context only.')
            if hist_eval is not None and len(hist_eval):
                eval_df=hist_eval.copy(); eval_df['_predicted_hit']=((eval_df['attention_score']>=threshold) & eval_df['_deterioration'].astype(bool)).astype(int)
                monthly=eval_df.groupby('_month',as_index=False).agg(**{'Total deterioration':('_deterioration','sum'),'Predicted deterioration':('_predicted_hit','sum')})
                monthly['Total deterioration']=monthly['Total deterioration'].astype(int); monthly['Predicted deterioration']=monthly['Predicted deterioration'].astype(int)
                actual=int(eval_df['_deterioration'].sum()); hits=int(eval_df['_predicted_hit'].sum()); flagged=int((eval_df['attention_score']>=threshold).sum())
                recall=hits/actual*100 if actual else np.nan; precision=hits/flagged*100 if flagged else np.nan
                a,b,c,d=st.columns(4); a.metric('Holdout dealer-months',len(eval_df)); b.metric('Deterioration cases',actual); c.metric('Cases flagged in advance',hits); d.metric('Captured deterioration',f'{recall:.1f}%' if pd.notna(recall) else 'Not measurable')
                if actual:
                    fig=go.Figure()
                    fig.add_trace(go.Scatter(x=monthly['_month'],y=monthly['Total deterioration'],name='Actual deterioration',mode='lines+markers',line=dict(width=2)))
                    fig.add_trace(go.Scatter(x=monthly['_month'],y=monthly['Predicted deterioration'],name='Also flagged by prior-month score',mode='lines+markers',line=dict(width=2)))
                    max_events=int(monthly[['Total deterioration','Predicted deterioration']].to_numpy().max())
                    fig.update_layout(title='Next-month deterioration cases in the holdout period',xaxis_title='Month of original dealer observation',yaxis_title='Dealer-months',legend_title='',hovermode='x unified',margin=dict(t=45,b=10))
                    fig.update_yaxes(rangemode='tozero',range=[0,max(1,max_events*1.15)],dtick=1 if max_events<=12 else None,tickformat=',d')
                    st.plotly_chart(fig,width='stretch')
                else:
                    st.info('No qualifying deterioration events occurred in this holdout period. The capture rate cannot be measured, so a zero-only chart is not shown.')
                precision_text=f'{precision:.1f}%' if pd.notna(precision) else 'not measurable (no alerts)'
                source_caveat='The selected data is synthetic.' if synthetic_data else 'Uploaded source values have not been independently audited.'
                st.caption(f'Holdout only: {precision_text} of flagged dealer-months were followed by a qualifying deterioration event. Rules: target achievement falls ≥20% relative; sales growth falls ≥20 percentage points; inventory ageing, payment delays, or complaints rate rises ≥20% relative; or service SLA falls ≥20% relative. Only measures present in both consecutive months are evaluated. A zero baseline is treated as a new increase when the next value becomes positive. The threshold is tuned on earlier months only when both outcome classes are present. Historical fit is not proof of future accuracy. {source_caveat}')
            else: st.warning('No adjacent dealer-months with both a valid prior-month score and comparable outcome data were available for the holdout.')
        elif page=='Dealer Ranking & Diagnosis':
            st.markdown('''<div class="manager-hero"><div class="eyebrow">Selected dealer</div><h1>Dealer diagnosis</h1><p>Review this dealer’s score, evidence, likely causes, and follow-up questions.</p></div>''',unsafe_allow_html=True)
            st.caption(f'Reporting period · {selected}   •   Source · {data_source_label}')
            ranked=scored.sort_values('attention_score',ascending=False).copy()
            ranked['priority_band']=classify_risk_band(ranked.attention_score)
            choices=ranked['Dealer display'].astype(str).tolist()
            if st.session_state.get('diagnosis_dealer') not in choices:
                st.session_state.pop('diagnosis_dealer',None)
            selected_dealer=st.selectbox('Dealer',choices,key='diagnosis_dealer')
            row=ranked[ranked['Dealer display']==selected_dealer].iloc[0]
            selected_row_df=pd.DataFrame([row])
            region_field=col(current,['region','state','state_name'])
            region_value=row.get(region_field) if region_field else None
            if region_field and pd.notna(region_value):
                regional_current=current[current[region_field].astype(str).str.strip().str.casefold()==str(region_value).strip().casefold()].copy()
                comparison_label=f'{region_value} regional median'
            else:
                regional_current=current.copy()
                comparison_label='network median'
            source_id=col(current,['dealer_id','dealer_code'])
            selected_id=row.get(source_id) if source_id else selected_dealer
            if source_id:
                regional_peers=regional_current[regional_current[source_id].astype(str)!=str(selected_id)].copy()
            else:
                regional_peers=regional_current[regional_current['Dealer display'].astype(str)!=str(selected_dealer)].copy() if 'Dealer display' in regional_current else regional_current.iloc[0:0]

            def target_achievement_values(frame):
                values=numeric(frame,['target_achievement_pct','sales_target_achievement_pct'])
                if values.notna().any(): return values
                sales=numeric(frame,['retail_sales_units','actual_retail_sales_units','sales_actual_units'])
                target=numeric(frame,['sales_target_units','target_units'])
                return sales.div(target.replace(0,np.nan))*100

            def complaint_rate_values(frame):
                values=numeric(frame,['complaints_per_100_retail_sales','complaints_rate'])
                if values.notna().any(): return values
                complaints=numeric(frame,['customer_complaints','complaints'])
                retail=numeric(frame,['retail_sales_units','actual_retail_sales_units','sales_actual_units'])
                if complaints.notna().any() and retail.notna().any(): return complaints.div(retail.replace(0,np.nan))*100
                return numeric(frame,['customer_complaints','complaints'])

            factor_inputs={
                'Sales versus target':(target_achievement_values,'%',1),
                'Sales growth':(lambda frame:numeric(frame,['sales_growth_yoy_pct','yoy_sales_growth_pct','sales_growth']),'%',1),
                'Inventory ageing':(lambda frame:numeric(frame,['inventory_days','stock_days','inventory_ageing_days']),' days',1),
                'Payment delays':(lambda frame:numeric(frame,['average_payment_days','payment_days','payment_delay_days']),' days',1),
                'Customer complaints':(complaint_rate_values,'/100 sales',2),
            }
            service_inputs={
                'FRT':(lambda frame:numeric(frame,['first_response_time_hours','frt_hours','first_response_hours']),' hours',1),
                'ART':(lambda frame:numeric(frame,['average_resolution_time_hours','art_hours','average_resolution_hours']),' hours',1),
                'Customer satisfaction':(lambda frame:numeric(frame,['customer_satisfaction_score_5','customer_satisfaction_score','csat_score_5']),' / 5',1),
            }
            st.markdown(f"## {selected_dealer}")
            ident_col=col(row.to_frame().T,['dealer_id','dealer_code'])
            geo_col=col(row.to_frame().T,['state'])
            summary_cols=st.columns(2)
            score_tone='semantic-negative' if float(row['attention_score'])>=40 else 'semantic-positive'
            band_tone='semantic-negative' if float(row['attention_score'])>=40 else 'semantic-positive'
            summary_cols[0].markdown(f'<div class="comparison-card"><div class="label">Overall attention score</div><div class="value {score_tone}">{float(row["attention_score"]):.1f}<span style="font-size:.9rem"> / 100</span></div></div>',unsafe_allow_html=True)
            summary_cols[1].markdown(f'<div class="comparison-card"><div class="label">Risk band</div><div class="value {band_tone}">{str(row.get("priority_band","Unclassified"))}</div></div>',unsafe_allow_html=True)
            detail_bits=[]
            if ident_col: detail_bits.append(f"Dealer ID · {row[ident_col]}")
            if geo_col: detail_bits.append(f"State · {row[geo_col]}")
            if detail_bits: st.caption('   •   '.join(detail_bits))
            if SCORE_METHOD_VERSION=='specification-weighted-v3':
                st.subheader('Factor scores')
                score_coverage=float(row.get('score_coverage_pct',0) or 0)
                score_specs=[
                    ('Sales versus target','Sales versus target score','Sales versus target',True),
                    ('Sales growth','Sales growth score','Less sales growth',True),
                    ('Inventory ageing','Inventory ageing score','Inventory ageing',True),
                    ('Payment delays','Payment delays score','Payment delays',False),
                    ('Service performance','Service performance score','Service performance',True),
                    ('Customer complaints','Customer complaints score','Customer complaints',False),
                ]
                factor_columns=st.columns(3)
                for index,(factor,score_field,weight_key,score_higher_is_better) in enumerate(score_specs):
                    risk_value=pd.to_numeric(pd.Series([row.get(weight_key+' risk',np.nan)]),errors='coerce').iloc[0]
                    factor_score=pd.to_numeric(pd.Series([row.get(score_field,np.nan)]),errors='coerce').iloc[0]
                    weight=SPECIFICATION_WEIGHTS.get(weight_key,0)
                    with factor_columns[index%3]:
                        with st.container(border=True):
                            st.markdown(f'**{factor}**')
                            st.markdown('<div class="factor-score-label">Factor score</div>',unsafe_allow_html=True)
                            score_text=f'{float(factor_score):.1f}' if pd.notna(factor_score) else '—'
                            score_good=(factor_score>=50 if score_higher_is_better else factor_score<=50) if pd.notna(factor_score) else None
                            score_tone='semantic-positive' if score_good is True else ('semantic-negative' if score_good is False else 'semantic-neutral')
                            st.markdown(f'<div class="factor-score-value {score_tone}">{score_text}<span> / 100</span></div>',unsafe_allow_html=True)
                            if pd.notna(risk_value):
                                risk_pct=float(np.clip(risk_value,0,100))
                                risk_color='#c03935' if risk_pct>50 else '#15803d'
                                st.markdown(f'<div class="factor-compare">Attention risk <b class="{"semantic-negative" if risk_pct>50 else "semantic-positive"}">{risk_pct:.0f}/100</b></div><div class="risk-meter"><span style="width:{risk_pct:.1f}%;background:{risk_color}"></span></div>',unsafe_allow_html=True)
                            weight_label=f'{weight*100:.0f}% model weight'
                            if factor=='Service performance':
                                service_lines=[]
                                for metric,(series_fn,unit,precision) in service_inputs.items():
                                    dealer_values=series_fn(selected_row_df); peer_values=series_fn(regional_peers).dropna()
                                    dealer_value=pd.to_numeric(dealer_values,errors='coerce').iloc[0] if len(dealer_values) else np.nan
                                    median_value=float(peer_values.median()) if len(peer_values) else np.nan
                                    if pd.notna(dealer_value) and pd.notna(median_value):
                                        better_is_higher=(metric=='Customer satisfaction')
                                        favorable=(dealer_value>median_value if better_is_higher else dealer_value<median_value)
                                        tone='semantic-positive' if favorable else ('semantic-negative' if dealer_value!=median_value else 'semantic-neutral')
                                        service_lines.append(f'<div class="factor-compare">{metric}: <span class="{tone}">{dealer_value:.{precision}f}{unit}</span> · region median {median_value:.{precision}f}{unit}</div>')
                                    elif pd.notna(dealer_value):
                                        service_lines.append(f'<div class="factor-compare">{metric}: {dealer_value:.{precision}f}{unit} · median unavailable</div>')
                                st.markdown(''.join(service_lines) if service_lines else '<div class="factor-compare">FRT, ART and satisfaction values unavailable.</div>',unsafe_allow_html=True)
                            else:
                                series_fn,unit,precision=factor_inputs[factor]
                                dealer_values=series_fn(selected_row_df); peer_values=series_fn(regional_peers).dropna()
                                dealer_value=pd.to_numeric(dealer_values,errors='coerce').iloc[0] if len(dealer_values) else np.nan
                                median_value=float(peer_values.median()) if len(peer_values) else np.nan
                                if pd.notna(dealer_value):
                                    if pd.notna(median_value):
                                        higher_is_better=factor in ('Sales versus target','Sales growth')
                                        favorable=(dealer_value>median_value if higher_is_better else dealer_value<median_value)
                                        tone=('semantic-positive' if dealer_value>0 else ('semantic-negative' if dealer_value<0 else 'semantic-neutral')) if factor=='Sales growth' else ('semantic-positive' if favorable else ('semantic-negative' if dealer_value!=median_value else 'semantic-neutral'))
                                        median_tone=('semantic-positive' if median_value>0 else ('semantic-negative' if median_value<0 else 'semantic-neutral')) if factor=='Sales growth' else 'semantic-neutral'
                                        st.markdown(f'<div class="factor-compare">Dealer: <span class="{tone}">{dealer_value:.{precision}f}{unit}</span><br>{comparison_label}: <span class="{median_tone}">{median_value:.{precision}f}{unit}</span> · n={len(peer_values)}</div>',unsafe_allow_html=True)
                                    else:
                                        st.markdown(f'<div class="factor-compare">Dealer: {dealer_value:.{precision}f}{unit}<br>Regional median unavailable</div>',unsafe_allow_html=True)
                                else:
                                    st.markdown('<div class="factor-compare">Dealer input unavailable</div>',unsafe_allow_html=True)
                            st.caption(weight_label)
                st.markdown('### Regional demand and sales')
                if region_field and pd.notna(region_value):
                    local_demand_now=market_potential_monthly(regional_current)
                    regional_sales_now=numeric(regional_current,['retail_sales_units','actual_retail_sales_units','sales_actual_units','actual_sales_units','dealer_sales_units','monthly_sales_units'])
                    avg_local_demand=float(local_demand_now.mean()) if local_demand_now.notna().any() else np.nan
                    avg_regional_sales=float(regional_sales_now.mean()) if regional_sales_now.notna().any() else np.nan
                    regional_target_achievement=target_achievement_values(regional_current)
                    avg_target_achievement=float(regional_target_achievement.mean()) if regional_target_achievement.notna().any() else np.nan
                    sales_demand_gap=avg_regional_sales-avg_local_demand if pd.notna(avg_regional_sales) and pd.notna(avg_local_demand) else np.nan
                    demand_yoy=sales_yoy=np.nan
                    hist_month_field=col(history,['month','reporting_month'])
                    hist_region_field=col(history,['region','state','state_name'])
                    if hist_month_field and hist_region_field:
                        region_history=history[history[hist_region_field].astype(str).str.strip().str.casefold()==str(region_value).strip().casefold()].copy()
                        region_history['_period']=pd.to_datetime(region_history[hist_month_field],errors='coerce').dt.to_period('M')
                        selected_period=pd.to_datetime(str(selected),errors='coerce')
                        if pd.notna(selected_period):
                            current_period=selected_period.to_period('M'); prior_period=current_period-12
                            region_history['_local_demand']=market_potential_monthly(region_history)
                            region_history['_retail_sales']=numeric(region_history,['retail_sales_units','actual_retail_sales_units','sales_actual_units','actual_sales_units','dealer_sales_units','monthly_sales_units'])
                            current_period_rows=region_history[region_history['_period']==current_period]
                            prior_period_rows=region_history[region_history['_period']==prior_period]
                            current_demand=float(current_period_rows['_local_demand'].mean()) if current_period_rows['_local_demand'].notna().any() else np.nan
                            prior_demand=float(prior_period_rows['_local_demand'].mean()) if prior_period_rows['_local_demand'].notna().any() else np.nan
                            if pd.notna(current_demand) and pd.notna(prior_demand) and prior_demand>0:
                                demand_yoy=(current_demand/prior_demand-1)*100
                            reported_sales_growth=numeric(current_period_rows,['sales_growth_yoy_pct','yoy_sales_growth_pct','sales_growth'])
                            if reported_sales_growth.notna().any():
                                sales_yoy=float(reported_sales_growth.mean())
                            else:
                                current_sales=float(current_period_rows['_retail_sales'].mean()) if current_period_rows['_retail_sales'].notna().any() else np.nan
                                prior_sales=float(prior_period_rows['_retail_sales'].mean()) if prior_period_rows['_retail_sales'].notna().any() else np.nan
                                if pd.notna(current_sales) and pd.notna(prior_sales) and prior_sales>0:
                                    sales_yoy=(current_sales/prior_sales-1)*100
                    demand_value=f'{avg_local_demand:,.1f} units / dealer / month' if pd.notna(avg_local_demand) else 'Unavailable'
                    sales_value=f'{avg_regional_sales:,.1f} units / dealer / month' if pd.notna(avg_regional_sales) else 'Unavailable'
                    target_tone='semantic-positive' if pd.notna(avg_target_achievement) and avg_target_achievement>=100 else ('semantic-negative' if pd.notna(avg_target_achievement) else 'semantic-neutral')
                    target_achievement_value=f'<span class="{target_tone}">{avg_target_achievement:.1f}%</span>' if pd.notna(avg_target_achievement) else '<span class="semantic-neutral">Unavailable</span>'
                    gap_class='semantic-positive' if pd.notna(sales_demand_gap) and sales_demand_gap>=0 else ('semantic-negative' if pd.notna(sales_demand_gap) else 'semantic-neutral')
                    demand_growth_class='semantic-positive' if pd.notna(demand_yoy) and demand_yoy>=0 else ('semantic-negative' if pd.notna(demand_yoy) else 'semantic-neutral')
                    sales_growth_class='semantic-positive' if pd.notna(sales_yoy) and sales_yoy>=0 else ('semantic-negative' if pd.notna(sales_yoy) else 'semantic-neutral')
                    gap_value=f'<span class="{gap_class}">{sales_demand_gap:+,.1f} units</span>' if pd.notna(sales_demand_gap) else 'Unavailable'
                    demand_growth_value=f'<span class="{demand_growth_class}">{demand_yoy:+.1f}%</span>' if pd.notna(demand_yoy) else '<span class="semantic-neutral">Unavailable</span>'
                    sales_growth_value=f'<span class="{sales_growth_class}">{sales_yoy:+.1f}%</span>' if pd.notna(sales_yoy) else '<span class="semantic-neutral">Unavailable</span>'
                    region_count=len(regional_current)
                    sales_detail=(f'Retail sales: <strong>{sales_value}</strong><br>Sales minus estimated demand: {gap_value}' if pd.notna(avg_regional_sales) else f'Retail sales units: <span class="semantic-neutral">not supplied</span><br>Average target achievement: <strong>{target_achievement_value}</strong> · percentage, not units')
                    st.markdown(f'''<div class="comparison-card"><div class="label">{region_value} · regional average · {selected}</div><div class="detail">Estimated local demand: <strong>{demand_value}</strong><br>{sales_detail}</div></div>''',unsafe_allow_html=True)
                    yoy_cols=st.columns(2)
                    yoy_cols[0].markdown(f'''<div class="comparison-card"><div class="label">Estimated demand · year over year</div><div class="value">{demand_growth_value}</div><div class="detail">Same month vs the same month last year · {region_count} regional dealer records in selected month</div></div>''',unsafe_allow_html=True)
                    yoy_cols[1].markdown(f'''<div class="comparison-card"><div class="label">Dealer sales · year over year</div><div class="value">{sales_growth_value}</div><div class="detail">Average reported YoY sales growth for {region_value}; negative contraction is shown in red.</div></div>''',unsafe_allow_html=True)
                    st.caption('Demand is the average supplied monthly estimate across dealers in this region. It is not dealer sales or confirmed dealer catchment demand.')
                else:
                    st.info('A region/state field is required to show this comparison.')
                market_avg=row.get('market_trailing_12m_monthly_average')
                market_yoy=row.get('market_trailing_12m_yoy_growth_pct')
                if pd.notna(market_avg):
                    market_scope_note=benchmark_scope_text or 'vehicle scope not supplied'
                    market_growth_class='semantic-positive' if pd.notna(market_yoy) and float(market_yoy)>=0 else ('semantic-negative' if pd.notna(market_yoy) else 'semantic-neutral')
                    market_growth_text=f' · <span class="{market_growth_class}">{float(market_yoy):+.1f}% demand trend</span>' if pd.notna(market_yoy) else ''
                    st.markdown(f"State market context · {float(market_avg):,.0f} registrations/month trailing average{market_growth_text} · {html_escape(market_scope_note)} · broad state context, not dealer-catchment demand.",unsafe_allow_html=True)
                    if pd.notna(market_yoy) and pd.notna(row.get('dealer_reported_growth_pct')):
                        dealer_market_growth=float(row['dealer_reported_growth_pct']); growth_gap=float(row.get('growth_market_comparison_gap_pp'))
                        dealer_growth_class='semantic-positive' if dealer_market_growth>=0 else 'semantic-negative'
                        growth_gap_class='semantic-positive' if growth_gap>=0 else 'semantic-negative'
                        comparison_note='The scope was confirmed comparable, so this difference adjusts the growth score.' if MARKET_SCOPE_COMPATIBLE else 'Context only; scope is not confirmed comparable and this does not adjust the growth score.'
                        st.markdown(f'Dealer YoY growth <span class="{dealer_growth_class}">{dealer_market_growth:+.1f}%</span> vs state registrations <span class="{market_growth_class}">{float(market_yoy):+.1f}%</span> · gap <span class="{growth_gap_class}">{growth_gap:+.1f} pp</span>. {comparison_note}',unsafe_allow_html=True)
                if score_coverage<100:
                    st.warning(f'{score_coverage:.0f}% of scoring weight has usable data. The score uses available factors only; review missing metrics before acting.')
            # Model x dealer x month data: use actual monthly model rows when the workbook provides them.
            if not model_history.empty:
                mh=model_history.copy(); mh.columns=[str(c).strip() for c in mh.columns]
                mid=col(mh,['dealer_id','dealer_code']); mm=col(mh,['month','reporting_month']); modelname=col(mh,['model_name','model','model_id'])
                retailm=col(mh,['retail_sales_units','actual_retail_sales_units']); demandm=col(mh,['estimated_model_demand_units']); lostm=col(mh,['estimated_lost_sales_due_to_unavailability_units']); availm=col(mh,['model_availability_pct']); aged91=col(mh,['inventory_age_91_180_units']); aged180=col(mh,['inventory_age_over_180_units'])
                if mid and mm and modelname and retailm:
                    match=mh[(mh[mid].astype(str)==str(row.get(idcol))) & (mh[mm].astype(str)==str(selected))].copy()
                    if not match.empty:
                        for c in [retailm,demandm,lostm,availm,aged91,aged180]:
                            if c: match[c]=pd.to_numeric(match[c],errors='coerce')
                        match['_retail']=match[retailm].fillna(0)
                        match['_lost']=match[lostm].fillna(0) if lostm else 0
                        match['_demand']=match[demandm].fillna(0) if demandm else np.nan
                        match['_availability']=match[availm] if availm else np.nan
                        match['_aged']=match[aged91].fillna(0)+match[aged180].fillna(0) if aged91 and aged180 else np.nan
                        st.subheader('Model-level evidence for this dealer')
                        st.caption('Monthly model records help distinguish weak demand from lost sales caused by unavailable models, and identify models with ageing stock.')
                        model_roll=match.groupby(modelname,as_index=False).agg(**{'Retail sales':('_retail','sum'),'Estimated demand':('_demand','sum'),'Estimated lost sales':('_lost','sum'),'Average availability %':('_availability','mean'),'Units aged 91+ days':('_aged','sum')})
                        model_roll['Unmet demand proxy']=model_roll['Estimated lost sales'].fillna(0)
                        model_roll=model_roll.sort_values(['Estimated lost sales','Units aged 91+ days'],ascending=False)
                        top_lost=model_roll['Estimated lost sales'].sum(); total_retail=model_roll['Retail sales'].sum(); top_model=model_roll.iloc[0]
                        a,b,c=st.columns(3); a.metric('Model retail sales',f'{total_retail:.0f} units'); b.metric('Estimated lost sales from unavailability',f'{top_lost:.0f} units'); c.metric('Models with aged stock',int((model_roll['Units aged 91+ days'].fillna(0)>0).sum()))
                        if top_lost>0:
                            st.info(f"Supply constraint signal: {top_lost:.0f} estimated lost sales are attributed to unavailability across models. Highest estimated lost-sales model: {top_model[modelname]} ({top_model['Estimated lost sales']:.0f} units). Validate the simulated/estimated lost-sales field before making allocation decisions.")
                        aged_models=model_roll[model_roll['Units aged 91+ days'].fillna(0)>0].sort_values('Units aged 91+ days',ascending=False)
                        if not aged_models.empty:
                            mrow=aged_models.iloc[0]
                            st.info(f"Ageing-stock signal: {mrow[modelname]} has the most 91+ day stock ({mrow['Units aged 91+ days']:.0f} units). Compare its estimated demand and lost sales before replenishing or transferring inventory.")
                        figm=px.bar(model_roll.head(10),x=modelname,y=['Retail sales','Estimated lost sales','Units aged 91+ days'],barmode='group',title='Top model-level sales, estimated lost sales and ageing stock')
                        figm.update_layout(xaxis_title='Model',yaxis_title='Units',legend_title='Measure')
                        st.plotly_chart(figm,width='stretch')
                        with st.expander('View model-level figures'):
                            st.dataframe(model_roll,width='stretch',hide_index=True)
                    else:
                        st.caption('No model-level records matched this dealer and reporting month; diagnosis uses dealer-level KPIs only.')
            st.subheader('Underlying-cause diagnosis')
            raw_checks=[('Target achievement', ['target_achievement_pct','sales_target_units']),('Sales growth (comparison)', ['sales_growth_yoy_pct']),('Inventory days', ['inventory_days']),('Stock aged over 90 days', ['units_over_90_days']),('Stock aged over 180 days', ['units_over_180_days']),('Overdue receivables %', ['overdue_pct_receivables']),('Average payment days', ['average_payment_days']),('Service SLA compliance', ['service_sla_compliance_pct']),('Repeat repair rate', ['repeat_repair_rate_pct']),('Complaints per 100 sales', ['complaints_per_100_retail_sales'])]
            diag=[]
            for label,candidates in raw_checks:
                v=numeric(pd.DataFrame([row]),candidates).iloc[0]
                if pd.notna(v): diag.append({'Measure':label,'Observed value':round(float(v),2)})
            if diag:
                # Show only meaningful signal cards rather than a raw KPI table.
                vals_by={d['Measure']:d['Observed value'] for d in diag}
                cards=[]
                ach=numeric(pd.DataFrame([row]),['target_achievement_pct']).iloc[0]
                if pd.isna(ach):
                    tar=numeric(pd.DataFrame([row]),['sales_target_units']).iloc[0]; sal=numeric(pd.DataFrame([row]),['retail_sales_units']).iloc[0]
                    ach=sal/tar*100 if pd.notna(sal) and pd.notna(tar) and tar>0 else np.nan
                growth=numeric(pd.DataFrame([row]),['sales_growth_yoy_pct']).iloc[0]
                inv=numeric(pd.DataFrame([row]),['inventory_days']).iloc[0]
                over90=numeric(pd.DataFrame([row]),['units_over_90_days']).iloc[0]
                over180=numeric(pd.DataFrame([row]),['units_over_180_days']).iloc[0]
                overdue=numeric(pd.DataFrame([row]),['overdue_pct_receivables']).iloc[0]
                paydays=numeric(pd.DataFrame([row]),['average_payment_days']).iloc[0]
                sla=numeric(pd.DataFrame([row]),['service_sla_compliance_pct']).iloc[0]
                repeat=numeric(pd.DataFrame([row]),['repeat_repair_rate_pct']).iloc[0]
                cpr=numeric(pd.DataFrame([row]),['complaints_per_100_retail_sales']).iloc[0]
                if pd.notna(ach) and ach<90: cards.append(('Below sales target',f'{ach:.1f}% achievement','Check lead funnel, conversion, model availability and target realism.'))
                if pd.notna(growth) and growth<0: cards.append(('Negative year-on-year sales growth',f'{growth:.1f}%','Compare model mix, enquiries, conversion and competitor changes.'))
                if SCORE_METHOD_VERSION=='specification-weighted-v3' and pd.notna(inv) and inv>120: cards.append(('Inventory age above 120-day midpoint',f'{inv:.0f} days','The specification score falls below its 50-point midpoint above 120 days; review ageing by model/variant before changing replenishment.'))
                elif SCORE_METHOD_VERSION!='specification-weighted-v3' and pd.notna(inv) and inv>60: cards.append(('More than 60 days of inventory',f'{inv:.0f} days','Review stock turns, replenishment and ageing by model/variant.'))
                if pd.notna(over90) and over90>0: cards.append(('Inventory aged over 90 days',f'{over90:.0f} units','Check model-level demand mismatch and stock-transfer options.'))
                if pd.notna(over180) and over180>0: cards.append(('Inventory aged over 180 days',f'{over180:.0f} units','Prioritise aged units for a specific liquidation or transfer decision.'))
                if pd.notna(overdue) and overdue>=30: cards.append(('High overdue receivables',f'{overdue:.1f}%','Separate invoice disputes from genuinely late payments.'))
                if pd.notna(paydays) and paydays>45: cards.append(('Extended payment cycle',f'{paydays:.0f} days','Review invoice ageing and collection commitments.'))
                if pd.notna(sla) and sla<85: cards.append(('Service SLA below 85%',f'{sla:.1f}%','Investigate backlog, parts availability and technician capacity.'))
                if pd.notna(repeat) and repeat>=10: cards.append(('High repeat-repair rate',f'{repeat:.1f}%','Audit recurring fault types and repair quality.'))
                if pd.notna(cpr) and cpr>=5: cards.append(('Elevated complaints per 100 sales',f'{cpr:.1f}','Group complaint themes and unresolved cases.'))
                market=market_potential_monthly(pd.DataFrame([row])).iloc[0]
                retailv=numeric(pd.DataFrame([row]),['retail_sales_units']).iloc[0]
                if pd.notna(market) and market>0 and pd.notna(retailv): cards.append(('Dealer sales vs monthly market potential',f'{retailv:.0f} dealer units vs {market:,.0f} estimated monthly category units ({retailv/market*100:.1f}% ratio)' if market>0 else f'{retailv:.0f} dealer units vs {market:,.0f} estimated monthly category units','Monthly potential is annual same-category market estimate ÷ 12 where annual data exists. Comparison only—not part of the attention score; validate catchment and vehicle-category coverage.'))
                if not cards: cards=[('No threshold-based KPI alert','No major signal detected from available fields','Check missing data and use the follow-up questions to investigate context.')]
                cc=st.columns(2)
                for i,(title,value,detail) in enumerate(cards):
                    with cc[i%2]:
                        tone='semantic-positive' if title.startswith('No threshold-based') else ('semantic-neutral' if title.startswith('Dealer sales vs monthly market') else 'semantic-negative')
                        st.markdown(f'''<div class="comparison-card"><div style="font-weight:700">{html_escape(title)}</div><div class="value {tone}">{html_escape(value)}</div><div class="detail">{html_escape(detail)}</div></div>''',unsafe_allow_html=True)
            st.subheader('Primary risk drivers')
            st.caption('Only factors with a risk score above 50 are shown, so the chart highlights material issues rather than every factor.')
            risks={k:row.get(k+' risk',np.nan) for k in WEIGHTS}
            material_risks=priority_risk_drivers(risks,50)
            if material_risks:
                visible_riskdf=pd.DataFrame(material_risks,columns=['Factor','Risk score']).sort_values('Risk score',ascending=True)
                riskfig=px.bar(visible_riskdf,x='Risk score',y='Factor',orientation='h',range_x=[0,110],text='Risk score',title=f'{selected_dealer}: material risk drivers')
                riskfig.update_traces(marker_color='#c03935',texttemplate='%{text:.0f}',textposition='outside',cliponaxis=False)
                riskfig.update_layout(showlegend=False,margin=dict(l=10,r=55,t=55,b=20),yaxis_title='',xaxis_title='Risk score (operational drivers first; sales shown only when no operational driver exceeds 50)',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(color='#20263a'))
                st.plotly_chart(riskfig,width='stretch')
            else:
                st.success('No individual factor exceeds 50/100. Review the overall score and the KPI cards below, but avoid over-prioritising low-severity signals.')
            st.subheader('Investigate underlying causes')
            st.caption('Please add operational context. The app will combine these answers with the dealer KPIs to produce more specific diagnostic insights.')
            operational_driver_present=any(factor in OPERATIONAL_RISK_FACTORS for factor,_ in material_risks)
            if operational_driver_present:
                st.info('Sales measures are treated as outcomes. Investigate the operational drivers shown above first; sales-specific follow-up is available when no operational driver is identified.')
                q1='Not yet known'
            else:
                q1=st.selectbox('Sales outcome: what may explain the result?', ['Not yet known','Low enquiry/footfall','Low conversion','Model/variant unavailable','Competitor offer or new launch','Target may be unrealistic'],key='diag_q_sales_'+str(selected_dealer))
            q2=st.selectbox('Inventory: what is happening?', ['Not yet known','Specific models are ageing','Stock mix mismatch with local demand','Recent dispatches but weak retail movement','No major inventory issue'],key='diag_q_inv_'+str(selected_dealer))
            q3=st.selectbox('Payments: what explains overdue balances?', ['Not yet known','Invoice/credit-note dispute','Weak collection follow-up','Dealer cash-flow issue','Due dates/credit terms need reconciliation'],key='diag_q_pay_'+str(selected_dealer))
            q4=st.selectbox('Service/complaints: likely issue?', ['Not yet known','Parts shortage','Technician capacity/skills','Repeat unresolved faults','Delivery/expectation mismatch','Not yet known / other'],key='diag_q_service_'+str(selected_dealer))
            context=st.text_area('Additional evidence from dealer / regional manager',key='diag_context_'+str(selected_dealer),placeholder='e.g. top two models unavailable for 3 weeks; 4 invoices disputed; competitor opened nearby...')
            insights=[]
            if q1=='Low enquiry/footfall': insights.append('Sales diagnosis: test catchment reach and enquiry trend before focusing on salesperson conversion.')
            elif q1=='Low conversion': insights.append('Sales diagnosis: inspect response time, test rides, quotations and lost-lead reasons; compare conversion by salesperson/model.')
            elif q1=='Model/variant unavailable': insights.append('Sales diagnosis: cross-check lost orders with stockout history and replenishment lead times before treating this as weak demand.')
            elif q1=='Competitor offer or new launch': insights.append('Sales diagnosis: compare competitor offers and lost-deal feedback; quantify impact before recommending discounting.')
            elif q1=='Target may be unrealistic': insights.append('Sales diagnosis: benchmark target against prior run-rate, seasonality, catchment demand and dealer capacity.')
            if q2=='Specific models are ageing' or q2=='Stock mix mismatch with local demand': insights.append('Inventory diagnosis: likely model-mix mismatch; analyse ageing by model/variant rather than only total inventory days.')
            elif q2=='Recent dispatches but weak retail movement': insights.append('Inventory diagnosis: compare wholesale dispatches with retail sales; possible channel loading or demand slowdown needs validation.')
            if q3=='Invoice/credit-note dispute': insights.append('Payment diagnosis: separate disputed balances from collectible overdue debt and resolve documentation first.')
            elif q3=='Weak collection follow-up': insights.append('Payment diagnosis: assign invoice owners, promised dates and escalation for missed commitments.')
            elif q3=='Dealer cash-flow issue': insights.append('Payment diagnosis: review exposure, payment pattern and credit limit; escalate according to credit policy.')
            elif q3=='Due dates/credit terms need reconciliation': insights.append('Payment diagnosis: reconcile invoice due dates and contractual credit terms before classifying the full balance as late.')
            if q4=='Parts shortage': insights.append('Service diagnosis: compare SLA misses with parts fill rate and back-order duration.')
            elif q4=='Technician capacity/skills': insights.append('Service diagnosis: compare job inflow with technician capacity, skill coverage and backlog by repair type.')
            elif q4=='Repeat unresolved faults': insights.append('Service diagnosis: analyse repeat repair by model/fault code and audit repair quality.')
            elif q4=='Delivery/expectation mismatch': insights.append('Customer diagnosis: split complaints by delivery, product expectation and service resolution to identify the dominant theme.')
            if context.strip(): insights.append('Additional context to validate: '+context.strip())
            if insights:
                for insight in insights:
                    tone='semantic-neutral' if insight.startswith('Additional context') else 'semantic-negative'
                    st.markdown(f'<div class="insight-card"><div class="body {tone}">{html_escape(insight)}</div></div>',unsafe_allow_html=True)
            else: st.info('Select the best-known operational causes above or add field evidence to refine the diagnosis. Until then, the app will show KPI-based hypotheses only.')
            triggered=sorted([(k,v) for k,v in risks.items() if pd.notna(v) and v>=50],key=lambda x:x[1],reverse=True)
            if triggered: st.caption('Highest numeric risk signals: '+', '.join(f'{k} ({v:.0f}/100)' for k,v in triggered)+'.')
            st.caption('Recommendations are conditional hypotheses, not confirmed root causes. Local market potential and positive sales growth are comparison/context metrics, not negative scoring factors.')
            if st.button('Action Plan', type='primary', key='devise_plan_'+str(selected_dealer)):
                workbook_answers={'sales':q1, 'inventory':q2, 'payments':q3, 'service':q4, 'context':context}
                dealer_id_col=col(scored, ['dealer_id','dealer code','dealer_code'])
                if dealer_id_col and not scored[scored['Dealer display'].astype(str)==str(selected_dealer)].empty:
                    selected_row=scored[scored['Dealer display'].astype(str)==str(selected_dealer)].iloc[0]
                    plan_dealer_id=str(selected_row[dealer_id_col])
                else:
                    plan_dealer_id=str(selected_dealer)
                record_assessment({'assessment_type':'workbook_action_plan_created','dealer_id':plan_dealer_id,
                    'dealer_name':str(selected_dealer),'reporting_period':str(selected),
                    'original_model_score':json_safe(row.get('attention_score')),
                    'original_model_band':str(row.get('priority_band','')),
                    'investigation_answers':workbook_answers})
                plan_label=register_action_plan('workbook', plan_dealer_id, str(selected_dealer), None, workbook_answers)
                st.session_state['active_action_plan_key']=st.session_state['action_plans'][-1]['key']
                st.session_state['pending_navigation']='Action Plan'
                st.rerun()
            with st.expander('Export complete dealer evidence'):
                st.download_button('Download ranked dealers CSV',ranked.drop(columns=['_risk_components'],errors='ignore').to_csv(index=False).encode(),'Dealer360_Ranked_Dealers.csv','text/csv')
        elif page=='Action Plan':
            st.header('Dealer Action Plan')
            selected_dealer=st.session_state.get('action_plan_dealer')
            answers=st.session_state.get('action_plan_answers',{})
            if not selected_dealer:
                st.info('Choose a dealer in Dealer Ranking & Diagnosis, answer the investigation questions, then select “Devise action plan”.')
            else:
                plan_matches=scored[scored['Dealer display'].astype(str)==str(selected_dealer)]
                if plan_matches.empty:
                    st.warning('The selected dealer is not present in the current workbook. Return to Dealer Ranking & Diagnosis and select a dealer again.')
                else:
                    pr=plan_matches.iloc[0]
                    risks_plan={k:pr.get(k+' risk',np.nan) for k in WEIGHTS}
                    drivers_plan=priority_risk_drivers(risks_plan,50)
                    st.markdown('''<div class="manager-hero"><div class="eyebrow">Evidence-led action plan</div><p>Peer benchmarks, operational evidence, prioritized actions, and validation checklist</p></div>''',unsafe_allow_html=True)
                    st.markdown(f"## Action Plan ({html_escape(str(st.session_state.get('action_plan_dealer_id', selected_dealer)))})")
                    plan_score=float(pr['attention_score'])
                    plan_tone='semantic-negative' if plan_score>=40 else 'semantic-positive'
                    st.markdown(f'<div class="comparison-card"><div class="label">Attention score · {str(pr.get("priority_band","Unclassified"))}</div><div class="value {plan_tone}">{plan_score:.1f}<span style="font-size:.9rem"> / 100</span></div></div>',unsafe_allow_html=True)
                    if drivers_plan:
                        st.subheader('Management takeaway')
                        top3=drivers_plan[:3]
                        st.markdown(' '.join([f'<span class="semantic-negative">{i+1}. {html_escape(k)} ({v:.0f}/100)</span>' for i,(k,v) in enumerate(top3)]),unsafe_allow_html=True)
                        st.caption('Operational risks are prioritized as potential causes. Sales target and growth are outcome signals and become action priorities only when no operational risk or actionable operating issue is identified. Risk scores guide investigation; they do not prove cause.')
                    # Measured evidence and specific, conditional decisions
                    prdf=pd.DataFrame([pr])
                    target=numeric(prdf,['sales_target_units']).iloc[0]; retail=numeric(prdf,['retail_sales_units']).iloc[0]
                    ach=(retail/target*100) if pd.notna(target) and target>0 and pd.notna(retail) else numeric(prdf,['target_achievement_pct']).iloc[0]
                    gap=max(0,target-retail) if pd.notna(target) and pd.notna(retail) else np.nan
                    growth=numeric(prdf,['sales_growth_yoy_pct']).iloc[0]
                    invdays=numeric(prdf,['inventory_days']).iloc[0]; age90=numeric(prdf,['units_over_90_days']).iloc[0]; age90pct=numeric(prdf,['units_over_90_days_pct']).iloc[0]; age180=numeric(prdf,['units_over_180_days']).iloc[0]
                    overdue_pct=numeric(prdf,['overdue_pct_receivables']).iloc[0]; overdue_amt=numeric(prdf,['overdue_receivables_inr_lakh']).iloc[0]; paydays=numeric(prdf,['average_payment_days']).iloc[0]
                    sla=numeric(prdf,['service_sla_compliance_pct']).iloc[0]; complaints=numeric(prdf,['complaints_per_100_retail_sales']).iloc[0]
                    market_share=numeric(prdf,['estimated_dealer_market_share_pct']).iloc[0]
                    has_operational_driver=(
                        any(pd.notna(risks_plan.get(k)) and float(risks_plan[k])>MATERIAL_OPERATIONAL_RISK for k in OPERATIONAL_RISK_FACTORS)
                        or (pd.notna(invdays) and invdays>120) or (pd.notna(age90pct) and age90pct>=25)
                        or (pd.notna(overdue_pct) and overdue_pct>=25) or (pd.notna(paydays) and paydays>45)
                        or (pd.notna(sla) and sla<85) or (pd.notna(complaints) and complaints>5)
                        or answers.get('inventory') not in (None,'Not yet known','No major inventory issue')
                        or answers.get('payments') not in (None,'Not yet known')
                        or answers.get('service') not in (None,'Not yet known','Not yet known / other')
                    )
                    peers=scored.copy()
                    region_col=col(peers,['region']); this_region=pr.get(region_col) if region_col else None
                    if region_col and pd.notna(this_region): peers=peers[peers[region_col]==this_region]
                    ps=numeric(peers,['retail_sales_units']); pt=numeric(peers,['sales_target_units']); peer_ach=ps/pt.replace(0,np.nan)*100
                    if peer_ach.notna().sum()==0: peer_ach=numeric(peers,['target_achievement_pct'])
                    peer_median=float(peer_ach.median()) if peer_ach.notna().any() else np.nan
                    # Keep the two comparison cohorts separate so low-risk and no-attention
                    # patterns can be distinguished from one another.
                    cohort_scores=pd.to_numeric(scored['attention_score'],errors='coerce')
                    low_risk_all=scored[(cohort_scores>=20)&(cohort_scores<40)].copy()
                    no_attention_all=scored[(cohort_scores>=0)&(cohort_scores<20)].copy()
                    low_risk_region=low_risk_all[low_risk_all[region_col]==this_region] if region_col and pd.notna(this_region) else low_risk_all.iloc[0:0]
                    no_attention_region=no_attention_all[no_attention_all[region_col]==this_region] if region_col and pd.notna(this_region) else no_attention_all.iloc[0:0]
                    low_risk_peers=low_risk_region if len(low_risk_region)>=3 else low_risk_all
                    no_attention_peers=no_attention_region if len(no_attention_region)>=3 else no_attention_all
                    dealer_key_value=str(pr.get(idcol,selected_dealer))
                    low_risk_peers=low_risk_peers[low_risk_peers[idcol].astype(str)!=dealer_key_value]
                    no_attention_peers=no_attention_peers[no_attention_peers[idcol].astype(str)!=dealer_key_value]
                    cohort_caption='same-region peers when at least 3 are available; otherwise all dealers in the cohort'
                    st.subheader('Dealer-specific issue or wider pattern?')
                    st.caption(f'Compare operational factors and sales growth with low-risk dealers (20–<40) and no-attention dealers (0–<20). Sales versus target is excluded from this comparison. Cohorts use {cohort_caption}. The separate attention-list cutoff remains strictly >50.')
                    peer_rows=[]
                    for factor in WEIGHTS:
                        if factor=='Sales versus target':
                            continue
                        dealer_risk=pd.to_numeric(pd.Series([pr.get(factor+' risk',np.nan)]),errors='coerce').iloc[0]
                        low_values=pd.to_numeric(low_risk_peers.get(factor+' risk',pd.Series(dtype=float)),errors='coerce').dropna()
                        no_values=pd.to_numeric(no_attention_peers.get(factor+' risk',pd.Series(dtype=float)),errors='coerce').dropna()
                        low_med=float(low_values.median()) if len(low_values) else np.nan
                        no_med=float(no_values.median()) if len(no_values) else np.nan
                        if pd.notna(dealer_risk) and (pd.notna(low_med) or pd.notna(no_med)):
                            deltas=[dealer_risk-v for v in (low_med,no_med) if pd.notna(v)]
                            max_gap=max(deltas) if deltas else np.nan
                            peer_rows.append({'Factor':factor,'Selected dealer risk':round(float(dealer_risk),1),
                                'Low-risk median':round(low_med,1) if pd.notna(low_med) else np.nan,
                                'Low-risk n':int(len(low_values)),'Gap vs low-risk':round(dealer_risk-low_med,1) if pd.notna(low_med) else np.nan,
                                'No-attention median':round(no_med,1) if pd.notna(no_med) else np.nan,
                                'No-attention n':int(len(no_values)),'Gap vs no-attention':round(dealer_risk-no_med,1) if pd.notna(no_med) else np.nan,
                                'Largest peer gap':round(max_gap,1) if pd.notna(max_gap) else np.nan})
                    if peer_rows:
                        peer_df=pd.DataFrame(peer_rows).sort_values('Largest peer gap',ascending=False)
                        unique_gaps=peer_df[(peer_df['Gap vs low-risk']>=15)|(peer_df['Gap vs no-attention']>=15)]
                        systemic=peer_df[(peer_df['Low-risk median']>50)&(peer_df['No-attention median']>50)]
                        st.markdown('**Risk profile against the two comparison groups**')
                        cohort_labels=['Selected dealer risk','Low-risk median','No-attention median']
                        peer_chart=peer_df.melt(id_vars=['Factor'],value_vars=cohort_labels,var_name='Comparison',value_name='Risk score').dropna(subset=['Risk score'])
                        peer_chart['Comparison']=peer_chart['Comparison'].map({'Selected dealer risk':'Selected dealer','Low-risk median':'Low-risk median','No-attention median':'No-attention median'})
                        peer_fig=px.bar(peer_chart,x='Risk score',y='Factor',color='Comparison',barmode='group',orientation='h',range_x=[0,100],
                            category_orders={'Factor':peer_df['Factor'].tolist(),'Comparison':['Selected dealer','Low-risk median','No-attention median']},
                            color_discrete_map={'Selected dealer':'#3049bf','Low-risk median':'#287a78','No-attention median':'#e2a33b'})
                        peer_fig.update_layout(height=330,margin=dict(l=5,r=15,t=8,b=10),xaxis_title='Risk score · 0–100',yaxis_title='',legend_title='',
                            paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(color='#20314b'))
                        peer_fig.update_yaxes(categoryorder='array',categoryarray=peer_df['Factor'].tolist(),autorange='reversed')
                        peer_fig.update_xaxes(showgrid=True,gridcolor='#e5eaf1')
                        st.plotly_chart(peer_fig,width='stretch',config={'displayModeBar':False})
                        summary_cols=st.columns(2)
                        if not unique_gaps.empty:
                            leading=unique_gaps.iloc[0]
                            best_low=leading['Gap vs low-risk'] if pd.notna(leading['Gap vs low-risk']) else -np.inf
                            best_no=leading['Gap vs no-attention'] if pd.notna(leading['Gap vs no-attention']) else -np.inf
                            peer_group='low-risk' if best_low>=best_no else 'no-attention'
                            peer_median_value=leading['Low-risk median'] if peer_group=='low-risk' else leading['No-attention median']
                            peer_n=int(leading['Low-risk n'] if peer_group=='low-risk' else leading['No-attention n'])
                            peer_gap=max(best_low,best_no)
                            summary_cols[0].markdown(f'''<div class="insight-card"><div class="eyebrow">Largest dealer-specific gap</div><div class="headline">{leading['Factor']}</div><div class="body">Selected dealer risk <b>{leading['Selected dealer risk']:.1f}</b> vs {peer_group} median <b>{peer_median_value:.1f}</b> (n={peer_n}); a {peer_gap:.1f}-point gap. Validate the underlying records before attributing cause.</div></div>''',unsafe_allow_html=True)
                        else:
                            summary_cols[0].markdown('<div class="insight-card"><div class="eyebrow">Dealer-specific signal</div><div class="headline">No large peer gap found</div><div class="body">No factor is at least 15 risk points above either comparison group.</div></div>',unsafe_allow_html=True)
                        if not systemic.empty:
                            shared=', '.join(systemic['Factor'].head(3).tolist())
                            summary_cols[1].markdown(f'''<div class="insight-card"><div class="eyebrow">Potential wider pattern</div><div class="headline">{shared}</div><div class="body">Both comparison groups have median risk above 50 for these factors. Check shared constraints before treating the issue as dealer-specific.</div></div>''',unsafe_allow_html=True)
                        else:
                            summary_cols[1].markdown('<div class="insight-card"><div class="eyebrow">Wider pattern</div><div class="headline">No shared high-risk factor</div><div class="body">No factor has median risk above 50 in both comparison groups.</div></div>',unsafe_allow_html=True)
                        with st.expander('Detailed peer scores and cohort sizes'):
                            st.dataframe(peer_df,width='stretch',hide_index=True)
                    else:
                        st.info('No comparison cohort has usable factor scores. The action plan will rely on the selected dealer’s own evidence and label causal explanations as hypotheses.')
                    st.subheader('Evidence snapshot')
                    metrics=[]
                    if pd.notna(ach): metrics.append(('Target achievement',f'{ach:.1f}%',f'{gap:.0f} units short of target' if pd.notna(gap) else 'Source-reported percentage; raw sales and target units were not supplied'))
                    if pd.notna(growth): metrics.append(('Year-on-year growth',f'{growth:+.1f}%', 'Negative growth indicates contraction; compare against same-period model and market trends'))
                    if pd.notna(invdays): metrics.append(('Inventory age',f'{invdays:.0f} days','Specification score midpoint is 120 days; confirm model-level ageing before action' if SCORE_METHOD_VERSION=='specification-weighted-v3' else 'Review against the original operating trigger and model-level ageing'))
                    if pd.notna(age90): metrics.append(('Stock aged 90+ days',f'{age90:.0f} units','Potential working-capital and model-mix exposure'))
                    if pd.notna(overdue_pct): metrics.append(('Receivables overdue',f'{overdue_pct:.1f}%',f'₹{overdue_amt:.1f} lakh overdue' if pd.notna(overdue_amt) else 'Review invoice-level ageing'))
                    if pd.notna(sla): metrics.append(('Service SLA',f'{sla:.1f}%','Check backlog, parts and technician capacity'))
                    if pd.notna(complaints): metrics.append(('Complaints / 100 retail sales',f'{complaints:.1f}','Volume-adjusted customer-experience signal'))
                    if pd.notna(market_share): metrics.append(('Estimated local market share',f'{market_share:.1f}%','Comparison only; market estimate is not a scoring penalty'))
                    monthly_market=market_potential_monthly(prdf).iloc[0]
                    retail_units=numeric(prdf,['retail_sales_units']).iloc[0]
                    if pd.notna(monthly_market) and monthly_market>0:
                        market_label='Monthly local market potential'
                        market_note='Supplied monthly potential estimate; it is not dealer sales or a confirmed market share.'
                        if pd.notna(retail_units):
                            market_note=f'Dealer retail {retail_units:,.0f} units versus estimate ({retail_units/monthly_market*100:.1f}% directional ratio); validate catchment coverage.'
                        metrics.append((market_label,f'{monthly_market:,.0f} units/month',market_note))
                    # Compare this dealer with its own prior periods when a valid month key exists.
                    dealer_history=pd.DataFrame()
                    history_id_col=col(history,['dealer_id','dealer_code'])
                    if monthcol and history_id_col:
                        history_dates=pd.to_datetime(history[monthcol],errors='coerce')
                        selected_date=pd.to_datetime(str(pr.get(monthcol,selected)),errors='coerce')
                        dealer_history=history[(history[history_id_col].astype(str)==str(pr.get(idcol,''))) & (history_dates<selected_date)].copy()
                        dealer_history['_period_date']=history_dates.loc[dealer_history.index]
                        dealer_history=dealer_history.sort_values('_period_date').tail(3)
                    if not dealer_history.empty:
                        own_rows=[]
                        own_history_gaps=[]
                        inventory_history_spec=('Inventory age (days)',['inventory_days'],'lower',20) if SCORE_METHOD_VERSION=='specification-weighted-v3' else ('90+ day inventory share',['units_over_90_days_pct'],'lower',5)
                        own_specs=[('Target achievement',['target_achievement_pct'],'higher',10),('Sales growth YoY',['sales_growth_yoy_pct'],'higher',5),inventory_history_spec,('Payment delay days',['average_payment_days'],'lower',10),('Service SLA %',['service_sla_compliance_pct'],'higher',5),('Complaints per 100 retail sales',['complaints_per_100_retail_sales'],'lower',1)]
                        if has_operational_driver:
                            own_specs=[spec for spec in own_specs if spec[0] not in {'Target achievement','Sales growth YoY'}]
                        own_units={'Target achievement':('%','pp'),'Sales growth YoY':('%','pp'),'Inventory age (days)':(' days','days'),'90+ day inventory share':('%','pp'),'Payment delay days':(' days','days'),'Service SLA %':('%','pp'),'Complaints per 100 retail sales':(' /100','/100')}
                        for label,fields,direction,materiality in own_specs:
                            if label=='Target achievement':
                                past_retail=numeric(dealer_history,['retail_sales_units']); past_target=numeric(dealer_history,['sales_target_units'])
                                prior_values=(past_retail/past_target.replace(0,np.nan)*100)
                                if prior_values.notna().sum()==0: prior_values=numeric(dealer_history,fields)
                            else: prior_values=numeric(dealer_history,fields)
                            current_value=(retail/target*100) if label=='Target achievement' and pd.notna(target) and target>0 and pd.notna(retail) else numeric(prdf,fields).iloc[0]
                            prior_values=prior_values.dropna()
                            if len(prior_values) and pd.notna(current_value):
                                prior_median=float(prior_values.median())
                                change=float(current_value)-prior_median
                                adverse_change=-change if direction=='higher' else change
                                review_multiple=adverse_change/materiality
                                deteriorated=(direction=='higher' and current_value<=prior_median-materiality) or (direction=='lower' and current_value>=prior_median+materiality)
                                improved=(direction=='higher' and current_value>=prior_median+materiality) or (direction=='lower' and current_value<=prior_median-materiality)
                                signal='Worsening beyond band' if deteriorated else ('Improving beyond band' if improved else 'Within review band')
                                value_unit,delta_unit=own_units[label]
                                own_rows.append({'Metric':label,'Current period':str(pr.get(monthcol,selected)),'Current value':round(float(current_value),1),'Prior 3-month median':round(prior_median,1),'Prior periods':int(len(prior_values)),'Change vs median':round(change,1),'Adverse movement / review band':round(review_multiple,2),'Review signal':signal,'Direction':direction,'Value unit':value_unit,'Delta unit':delta_unit})
                                if deteriorated: own_history_gaps.append(f'{label}: {current_value:.1f} vs own prior median {prior_median:.1f} (n={len(prior_values)})')
                        if own_rows:
                            st.markdown('**Own history · current period vs recent baseline**')
                            st.caption('Bars show adverse movement as a multiple of the review band. Positive values are worsening; values at or above +1 cross the review band.')
                            own_df=pd.DataFrame(own_rows)
                            own_fig=px.bar(own_df.sort_values('Adverse movement / review band'),x='Adverse movement / review band',y='Metric',color='Review signal',orientation='h',
                                color_discrete_map={'Worsening beyond band':'#c85b54','Within review band':'#7c8ca3','Improving beyond band':'#287a78'},
                                hover_data={'Current value':':.1f','Prior 3-month median':':.1f','Prior periods':True,'Change vs median':':+.1f','Adverse movement / review band':':+.2f','Metric':False})
                            x_low=min(-1.2,float(own_df['Adverse movement / review band'].min())-.2); x_high=max(1.25,float(own_df['Adverse movement / review band'].max())+.2)
                            own_fig.add_vline(x=0,line_color='#8491a4',line_width=1)
                            own_fig.add_vline(x=1,line_dash='dash',line_color='#c85b54',annotation_text='Review band',annotation_position='top right')
                            own_fig.update_layout(template='plotly_white',height=260,margin=dict(l=5,r=10,t=28,b=8),xaxis_title='Adverse movement · multiples of review band',yaxis_title='',legend_title='',
                                paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(color='#20314b',size=13),
                                legend=dict(font=dict(color='#20314b',size=12),bgcolor='rgba(255,255,255,0.92)'))
                            own_fig.update_xaxes(range=[x_low,x_high],showgrid=True,gridcolor='#e5eaf1',zeroline=False,
                                title_font=dict(color='#20314b'),tickfont=dict(color='#53627a'))
                            own_fig.update_yaxes(autorange='reversed',tickfont=dict(color='#20314b',size=12))
                            st.plotly_chart(own_fig,width='stretch',config={'displayModeBar':False})
                            own_cards=st.columns(3)
                            for own_ix,own_metric in enumerate(own_rows):
                                card=own_cards[own_ix%3]
                                with card:
                                    with st.container(border=True):
                                        card_value=f"{own_metric['Current value']:.1f}{own_metric['Value unit']}"
                                        card_delta=f"{own_metric['Change vs median']:+.1f} {own_metric['Delta unit']} vs median"
                                        card_delta_color='normal' if own_metric['Direction']=='higher' else 'inverse'
                                        st.metric(own_metric['Metric'],card_value,card_delta,delta_color=card_delta_color)
                                        st.caption(f"3-period median {own_metric['Prior 3-month median']:.1f}{own_metric['Value unit']} · n={own_metric['Prior periods']} · {own_metric['Review signal']}")
                            with st.expander('Detailed own-history values'):
                                detail_cols=['Metric','Current period','Current value','Prior 3-month median','Change vs median','Prior periods','Review signal']
                                st.dataframe(own_df[detail_cols],width='stretch',hide_index=True)
                        else:
                            st.info('Own-history comparison is unavailable because prior periods do not contain comparable values for these measures.')
                    else:
                        own_history_gaps=[]
                    projections=project_dealer_metrics(history,pr.get(history_id_col) if history_id_col else None,history_id_col,monthcol,str(pr.get(monthcol,selected)))
                    projected_alerts=[]
                    projection_limits={'Sales versus target (%)':('lower',5.0),'Sales growth YoY (%)':('lower',5.0),'Inventory age (days)':('higher',20.0),'Payment delays (days)':('higher',5.0),'Service performance SLA (%)':('lower',5.0),'Customer complaints per 100 sales':('higher',1.0)}
                    for _,forecast in projections.iterrows():
                        rule=projection_limits.get(forecast['Measure'])
                        if has_operational_driver and forecast['Measure'] in {'Sales versus target (%)','Sales growth YoY (%)'}:
                            continue
                        delta=pd.to_numeric(pd.Series([forecast['Change from latest']]),errors='coerce').iloc[0]
                        if rule and pd.notna(delta) and ((rule[0]=='lower' and delta<=-rule[1]) or (rule[0]=='higher' and delta>=rule[1])):
                            projected_alerts.append(f"{forecast['Measure']} projected change {delta:+.1f}")
                    # Exact period/state join only. A regional registration count remains context,
                    # and is never converted into dealer-level sales or market share.
                    plan_market_context=None
                    if benchmark_validation is not None and benchmark_validation.accepted:
                        pr_state_col=col(prdf,['state','state_name'])
                        pr_state=str(pr.get(pr_state_col,'')).strip() if pr_state_col else ''
                        pr_period=str(pr.get(monthcol,selected)) if monthcol else str(selected)
                        plan_market=benchmark_frame[(benchmark_frame['month'].astype(str)==pr_period) & (benchmark_frame['state'].astype(str).str.strip().str.casefold()==pr_state.casefold())]
                        plan_market_context=state_market_demand_context(benchmark_frame,pr_state,pr_period)
                        if not plan_market.empty:
                            st.markdown('**Observed market-demand context · exact state and period match**')
                            display_cols=[c for c in ['month','state','geography_level','rto','vehicle_segment','fuel_type','manufacturer','registrations','unit','vehicle_scope','record_status'] if c in plan_market.columns]
                            st.dataframe(plan_market[display_cols],width='stretch',hide_index=True)
                            if plan_market_context is not None:
                                if pd.notna(growth) and pd.notna(plan_market_context['trailing_12_yoy_growth_pct']):
                                    difference=growth-plan_market_context['trailing_12_yoy_growth_pct']
                                    st.info(f"Dealer-reported sales growth is {growth:+.1f}% versus statewide registrations growth of {plan_market_context['trailing_12_yoy_growth_pct']:+.1f}% ({difference:+.1f} percentage-point difference). This is a cross-scope screening comparison only; it does not establish dealer share or cause.")
                            st.caption(f"Source: {benchmark_validation.provenance.get('source')} · Extracted: {benchmark_validation.provenance.get('last_updated','Not supplied')} · Scope: {benchmark_validation.provenance.get('vehicle_scope','Not supplied')}. State registrations do not identify a dealer catchment, specific brand, or vehicle segment.")
                        else:
                            st.caption('No external registration observation matched this dealer’s exact state and reporting period.')
                    for ix in range(0,len(metrics),3):
                        cc=st.columns(3)
                        for j,(label,value,note) in enumerate(metrics[ix:ix+3]):
                            with cc[j]:
                                st.markdown(f'<div class="insight-card"><div class="eyebrow">{label}</div><div class="headline">{value}</div><div class="body">{note}</div></div>',unsafe_allow_html=True)
                    st.subheader('Prioritised actions')
                    action_items=[]
                    if projected_alerts:
                        action_items.append(('P1 · Verify emerging trend','Recent six-period trajectories point to a potentially worsening direction in: '+', '.join(projected_alerts)+'. This is a simple extrapolation, not evidence that the trend will continue.','Check the next monthly close against the projected range, investigate seasonality, target resets, supply changes and reporting completeness, and assign a reversible response only after the signal is confirmed. Record the actual next-period value and projection error.','Evidence: straight-line continuation from six observed periods; confidence is low to moderate and falls when periods are missing or volatile.','Owner: Regional manager + affected functional lead · Review: next monthly close'))
                    if own_history_gaps:
                        action_items.append(('P1 · Investigate own-history deterioration','The current period is materially worse than this dealer’s recent baseline for: '+ '; '.join(own_history_gaps)+'. This is evidence of a change, not proof of its cause.','Reconcile the affected KPI definitions and records first, then split the change by model, transaction or case type. Check seasonality, target changes and data completeness; set the next review against both the prior-period median and comparable dealer cohorts.','Evidence: prior three available dealer periods; investigate explanations before attributing cause. Confidence: stronger with three complete prior periods, lower with fewer.','Owner: Regional manager + affected functional lead · Review: 14 days'))
                    if peer_rows:
                        systemic_factors=[r['Factor'] for r in peer_rows if pd.notna(r['Low-risk median']) and pd.notna(r['No-attention median']) and r['Low-risk median']>50 and r['No-attention median']>50]
                        if systemic_factors:
                            action_items.append(('P1 · Investigate shared/systemic causes','The same factors have median risk above 50 in both low-risk and no-attention cohorts: '+', '.join(systemic_factors)+'. This suggests a wider pattern may be present, although the score itself cannot establish the cause.','Compare common constraints across dealers—allocation, credit terms, service parts, training, market seasonality and reporting definitions. Pilot a regional/process fix with a comparison group before imposing dealer-specific penalties or broad policy changes.','Peer benchmark: both comparison cohorts have factor risk above 50. This is a signal for investigation, not proof of a shared cause.','Owner: Regional head + central functional lead · Review: 30 days'))
                    # Sales
                    if not has_operational_driver and ((pd.notna(ach) and ach<90) or (pd.notna(growth) and growth<0) or ('Sales versus target' in risks_plan and pd.notna(risks_plan['Sales versus target']) and risks_plan['Sales versus target']>=35) or ('Less sales growth' in risks_plan and pd.notna(risks_plan['Less sales growth']) and risks_plan['Less sales growth']>50)):
                        if pd.notna(growth) and growth<0 and (pd.isna(ach) or ach>=90) and answers.get('sales') in (None,'Not yet known'):
                            diagnosis='Sales growth is negative even though target achievement is not currently below 90%. This may indicate contraction from a prior base, changing targets or seasonality; the KPI alone does not identify the cause.'
                            action='Compare the same months year over year and the latest six-month run-rate. Split the change by model, lead volume, conversion and stock availability using source records; compare the same period across regional peers and available public registration context before deciding whether to support demand or adjust supply.'
                        elif answers.get('sales')=='Low enquiry/footfall':
                            diagnosis='The selected field context points to a lead-volume problem. Do not start with discounting until enquiry volume and catchment reach are checked.'
                            action='For the next 2 weeks, track daily enquiries by source, walk-ins, test rides and qualified leads; compare with regional peers. Run targeted local outreach only in catchments where enquiry density is below peer level.'
                        elif answers.get('sales')=='Low conversion':
                            diagnosis='The selected context points to conversion rather than simply a shortage of stock. Validate lead response time, test-ride completion, quotations and lost-lead reasons.'
                            action='Review the last 30 days of leads; identify the stage with the largest drop-off and the two salespeople/models with the weakest conversion. Introduce a 24-hour lead follow-up SLA and weekly conversion review. Measure incremental retail units, not calls made.'
                        elif answers.get('sales')=='Model/variant unavailable':
                            diagnosis='Potential demand is being lost at model/variant level. Confirm with stockout days and lost-order records before reallocating inventory.'
                            action='Build a model-variant list of lost orders and stockout duration; replenish only variants with evidenced lost demand, and compare estimated lost sales with aged stock elsewhere in the network before transferring inventory.'
                        else:
                            diagnosis='Sales performance is below the target/benchmark; the current data alone cannot separate weak demand, conversion, stock availability and target-setting effects.'
                            action='Create a weekly unit bridge: target units → retail units → model availability/lost orders → qualified leads → conversion. Assign an owner to the largest quantified gap and review actual versus planned recovery each week.'
                        sales_evidence=f'Measured gap: {gap:.0f} units; achievement {ach:.1f}%; peer median {peer_median:.1f}%.' if pd.notna(gap) and pd.notna(peer_median) else (f'Measured target achievement: {ach:.1f}%.' if pd.notna(ach) else 'Target/retail fields are incomplete; quantify the gap before committing a unit target.')
                        if pd.notna(growth): sales_evidence+=f' Year-on-year sales growth: {growth:+.1f}%.'
                        action_items.append(('P1 · Recover retail sales',diagnosis,action,sales_evidence,'Owner: Dealer principal + regional sales manager · Review: 7 days'))
                    # Inventory and demand context
                    inventory_age_trigger=(pd.notna(invdays) and invdays>120) if SCORE_METHOD_VERSION=='specification-weighted-v3' else (pd.notna(invdays) and invdays>60)
                    if inventory_age_trigger or (pd.notna(risks_plan.get('Inventory ageing')) and risks_plan['Inventory ageing']>50) or (pd.notna(age90) and age90>0) or (pd.notna(age90pct) and age90pct>=25) or answers.get('inventory') not in (None,'Not yet known','No major inventory issue'):
                        if answers.get('inventory')=='Stock mix mismatch with local demand' or (pd.notna(age90) and age90>0 and pd.notna(market_share) and market_share<5):
                            diagnosis='The evidence is consistent with a stock-mix issue: aged stock can coexist with low local share, but the market estimate is only a directional comparison.'
                            action='Create a model/variant matrix with on-hand units, 90+/180+ day stock, monthly retail run-rate, stockout days and local category demand proxy. Transfer slow-moving variants where another dealer has demand; protect replenishment for variants with recurring stockouts. Avoid broad inventory cuts.'
                        else:
                            diagnosis=('Inventory age is above the model midpoint of 120 days, which is a risk signal but does not show which models are responsible without model-level records.' if SCORE_METHOD_VERSION=='specification-weighted-v3' and pd.notna(invdays) and invdays>120 else 'Inventory cover/ageing indicates cash may be tied up in slow-moving units. The data does not establish which models are responsible unless model-level records are available.')
                            action='Split inventory by model and ageing bucket; pause replenishment only for variants whose age/cover is high and whose retail run-rate is weak. Review aged units weekly and test transfers or focused retail offers before broad allocation cuts.'
                        inventory_evidence=[]
                        if pd.notna(invdays): inventory_evidence.append(f'Inventory cover {invdays:.0f} days')
                        if pd.notna(age90): inventory_evidence.append(f'90+ day units {age90:.0f}')
                        if pd.notna(age90pct): inventory_evidence.append(f'90+ day inventory share {age90pct:.1f}%')
                        if pd.notna(age180): inventory_evidence.append(f'180+ day units {age180:.0f}')
                        action_items.append(('P1/P2 · Rebalance inventory',diagnosis,action,'; '.join(inventory_evidence) if inventory_evidence else 'Ageing inputs are missing; validate model-level ageing before changing allocation.', 'Owner: Dealer stock manager + regional supply planner · Review: 14 days'))
                    if (pd.notna(overdue_pct) and overdue_pct>=25) or (pd.notna(paydays) and paydays>45) or (pd.notna(risks_plan.get('Payment delays')) and risks_plan['Payment delays']>50) or answers.get('payments') not in (None,'Not yet known'):
                        if answers.get('payments')=='Invoice/credit-note dispute':
                            action='Within 5 working days, reconcile disputed invoices/credit notes against delivery proof and ledger; separate disputed from undisputed overdue exposure. Track each case with owner and closure date before escalating credit restrictions.'
                            diagnosis='A documentation dispute can make the overdue balance look worse than the collectible exposure. Separate the disputed amount before deciding on credit action.'
                        elif answers.get('payments')=='Dealer cash-flow issue':
                            action='Prepare an invoice-wise collection calendar with promised dates, weekly cash commitments and exposure by ageing bucket. Escalate any revised credit terms through the formal credit policy; do not rely on verbal commitments.'
                            diagnosis='The selected context suggests liquidity constraints. Payment plans and credit decisions need to follow company policy and verified exposure.'
                        else:
                            action='Within 48 hours, list overdue invoices by amount and days past due, assign a named owner, confirm disputes and obtain dated payment commitments. Review missed promises twice weekly and escalate according to credit policy.'
                            diagnosis='Receivables exposure needs invoice-level separation of collectible debt, disputes and due-date mismatches before changing dealer terms.'
                        action_items.append(('P1 · Reduce overdue exposure',diagnosis,action, f'Overdue: {overdue_pct:.1f}% of receivables; ₹{overdue_amt:.1f} lakh; average payment {paydays:.0f} days.' if pd.notna(overdue_pct) and pd.notna(overdue_amt) and pd.notna(paydays) else 'Overdue percentage, amount or payment days are incomplete; reconcile ledger.', 'Owner: Finance controller + dealer accounts lead · Review: 7 days'))
                    if (pd.notna(sla) and sla<85) or (pd.notna(complaints) and complaints>5) or any(pd.notna(risks_plan.get(k)) and risks_plan[k]>50 for k in ['Service performance','Customer complaints']) or answers.get('service') not in (None,'Not yet known','Not yet known / other'):
                        if answers.get('service')=='Parts shortage':
                            diagnosis='Service delays may be linked to parts availability. Validate back-orders and waiting time by part number against SLA misses.'
                            action='Rank the top parts by open jobs and days waiting; escalate recurring shortages to the parts planner and provide customers with committed dates. Review SLA recovery and repeat repairs weekly.'
                        elif answers.get('service')=='Technician capacity/skills':
                            diagnosis='Capacity or skill coverage may be constraining closure. Compare job inflow, technician hours, repair complexity and backlog by job type.'
                            action='Run a 2-week capacity review: jobs received versus closed, ageing backlog, productive hours and skill gaps. Reallocate trained technicians or targeted training to the highest backlog categories.'
                        elif answers.get('service')=='Repeat unresolved faults':
                            diagnosis='Repeat unresolved faults point to potential first-time-fix or repair-quality issues.'
                            action='Audit repeat repairs by model/fault code, inspect a sample of reopened jobs, and require technical sign-off for recurring failures. Track repeat-repair rate and SLA together to ensure faster closure does not worsen quality.'
                        else:
                            diagnosis='Service or customer-experience indicators suggest a need to identify the dominant complaint theme before choosing a remedy.'
                            action='Segment complaints by theme, model, service centre and days unresolved. Contact high-severity unresolved customers first, then track closure time, repeat repair and complaints per 100 retail sales.'
                        action_items.append(('P2 · Restore service reliability',diagnosis,action, f'Service SLA {sla:.1f}%; complaints per 100 retail sales {complaints:.1f}.' if pd.notna(sla) and pd.notna(complaints) else 'Service/complaint indicators are incomplete; inspect case-level records.', 'Owner: Service manager · Review: 14 days'))
                    # Context and market comparison
                    if plan_market_context is not None:
                        market_yoy=plan_market_context['trailing_12_yoy_growth_pct']
                        market_evidence=f"VAHAN observed {plan_market_context['registrations']:,.0f} statewide registrations in {plan_market_context['period']}; trailing 12-month monthly average {plan_market_context['trailing_12_monthly_average']:,.0f} units"
                        if pd.notna(market_yoy): market_evidence+=f"; trailing 12-month registrations change {market_yoy:+.1f}%"
                        if pd.notna(growth) and pd.notna(market_yoy): market_evidence+=f"; dealer-reported sales growth {growth:+.1f}% (cross-scope difference {growth-market_yoy:+.1f} pp)"
                        action_items.append(('P2 · Match market demand to dealer scope','Observed registrations provide a state-level demand run-rate and trend, but this extract covers all makers, vehicle types, categories and fuels. The trend is not a like-for-like comparison with a dealer’s sales or catchment.','Before using the trend to change targets, supply or local marketing, obtain a VAHAN extract filtered to the relevant RTO/catchment, manufacturer and vehicle category where available. Align its period with dealer retail sales and compare model availability and lost sales; until then retain this figure as broad context only. ',market_evidence+'. Source: '+str(benchmark_validation.provenance.get('source'))+'; extracted '+str(benchmark_validation.provenance.get('last_updated','date not supplied'))+'.','Owner: Regional manager + market insights lead · Review: next monthly close'))
                    if plan_market_context is None and pd.notna(market_share):
                        action_items.append(('P2 · Validate local-market opportunity','Estimated dealer market share is a comparison proxy, not a direct measure of addressable demand. A low share may reflect competition, catchment differences or imperfect market estimates.','Compare the dealer’s retail run-rate with same-category regional registrations and peer share; map the top models sold locally, competitor locations/offers, and stockout/lost-order history. Decide whether the gap calls for local demand generation, a model-mix change or supply recovery only after these checks. ',f'Estimated market share: {market_share:.1f}% (directional estimate; not included in risk score).','Owner: Regional manager + dealer sales lead · Review: 30 days'))
                    elif plan_market_context is None and pd.notna(monthly_market) and monthly_market>0:
                        action_items.append(('P2 · Validate local market potential','The supplied local market potential is an estimate and cannot establish dealer share or dealer-level sales.','Confirm the catchment, vehicle scope, reporting period and estimate owner. Where an external public registration extract is available, compare the same period and state/category as context; keep registrations separate from dealer sales. Use the result to frame a local demand review, not to assign a sales quota by itself.','Supplied potential of '+f'{monthly_market:,.0f} units/month; source and estimation method require confirmation.','Owner: Regional manager + dealer sales lead · Review: 30 days'))
                    if answers.get('context','').strip():
                        action_items.append(('Field evidence to validate', 'The dealer/manager supplied additional context. Treat it as a hypothesis until matched to records.', 'Validate this note against lead records, model availability, invoices, service cases or complaint details: '+answers['context'].strip(), 'Evidence source: dealer/manager note', 'Owner: Regional manager · Review: next review meeting'))
                    if not action_items:
                        action_items.append(('P1 · Establish a baseline','No material risk trigger was found in the available fields, or key fields are missing.','Validate the latest month’s target, retail sales, inventory ageing, overdue invoices, service SLA and complaint rate. Set a monthly baseline before committing a corrective intervention.', 'Evidence gap: no action-specific threshold crossed in available data.', 'Owner: Dealer manager · Review: 14 days'))
                    for title,diagnosis,action,evidence,owner in action_items:
                        with st.container(border=True):
                            action_tone='semantic-negative' if title.startswith('P1') else ('semantic-neutral' if title.startswith('P2') else 'semantic-positive')
                            st.markdown(f'<div class="{action_tone}">{html_escape(title)}</div>',unsafe_allow_html=True)
                            st.markdown('**Next step**')
                            st.write(action)
                            st.caption('Owner / review · '+owner)
                            with st.expander('Evidence, rationale and limits'):
                                st.write('Why this matters: '+diagnosis)
                                st.write('Supporting data: '+evidence)
                                st.caption('This is a directional recommendation, not proof of cause. Check seasonality, target changes, model mix, supply timing and data completeness.')
                    st.subheader('Validation checklist')
                    st.write('Use this checklist before closing the plan; it distinguishes measured facts from assumptions.')
                    for item in ['Confirm model-level retail, stockout and ageing data for the same month.','Reconcile receivables against invoice due dates and disputed balances.','Compare the dealer with the same region and vehicle category, not a national average alone.','Record the baseline, action owner, due date and measurable outcome before the next review.']:
                        st.checkbox(item,key='plan_check_'+str(selected_dealer)+'_'+str(abs(hash(item))))
                    st.download_button('Download this action plan',pd.DataFrame(action_items,columns=['Priority','Diagnosis','Action','Evidence','Owner / review']).to_csv(index=False).encode('utf-8'),f'{str(selected_dealer).replace(" ","_")}_Action_Plan.csv','text/csv')
                    if st.button('Return to dealer diagnosis',key='return_diagnosis'):
                        st.session_state['pending_navigation']='Dealer Ranking & Diagnosis'
                        st.rerun()
    except Exception as e:
        st.error('Could not process the workbook. Check the expected columns or use the provided template.')
        st.exception(e)
elif data_source is None and page == 'Dealer Ranking & Diagnosis':
    st.info('Choose a file or sample in the File upload tab before opening a dealer diagnosis.')
