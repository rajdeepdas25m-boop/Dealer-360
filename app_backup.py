import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(page_title='Dealer 360 | Management Attention', page_icon='🚘', layout='wide')
WEIGHTS = {'Sales versus target':.25,'Less sales growth':.10,'Inventory ageing':.20,'Payment delays':.20,'Service performance':.10,'Customer complaints':.15}
RECS = {
'Sales versus target':'Review target achievement, conversion, lead follow-up and create a weekly sales recovery plan.',
'Less sales growth':'Compare retail sales with the same period last year, then split the decline by model, lead conversion and lost orders.',
'Inventory ageing':'Review 90+/180+ day stock, pause avoidable replenishment and plan targeted movement of slow-selling inventory.',
'Payment delays':'Create an invoice-wise collection plan, prioritise overdue balances and review credit limits.',
'Service performance':'Audit SLA misses, technician capacity, spare-parts availability and repeat repairs.',
'Customer complaints':'Identify top complaint causes, contact unresolved customers and track complaint rates.'}

st.markdown('''<style>
:root{--ink:#20263a;--muted:#687386;--line:#dce2eb;--paper:#f1f3f8;--panel:#ffffff;--blue:#3049bf;--blue-soft:#e4e9ff}
.stApp{background:var(--paper);color:var(--ink)}
.block-container{padding-top:1.45rem;padding-bottom:2.5rem;max-width:1600px}
[data-testid="stSidebar"]{background:#f9faff;border-right:1px solid #dfe4ed}
[data-testid="stSidebar"]>div:first-child{padding-top:1.2rem}
[data-testid="stSidebar"] [data-testid="stRadio"] label{padding:8px 10px;border-radius:11px;margin:2px 0}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked){background:#e2e7fb;color:#263fae;font-weight:650}
.hero{background:linear-gradient(115deg,#fff 0%,#f8f9ff 70%,#e8edff 100%);padding:22px 26px;border:1px solid var(--line);border-radius:19px;color:var(--ink);margin-bottom:18px;box-shadow:0 5px 18px rgba(33,45,75,.04)}
.hero h1{color:#20263a;margin:0;font-family:Georgia,serif;font-size:2.25rem;letter-spacing:-.7px}.hero p{color:#687386;margin:6px 0 0;font-size:1rem}
h1,h2,h3{letter-spacing:-.25px;color:#20263a}h1{font-family:Georgia,serif}
[data-testid="stMetric"]{background:rgba(255,255,255,.88);border:1px solid var(--line);border-radius:15px;padding:16px 18px;box-shadow:0 4px 15px rgba(33,45,75,.035);min-height:112px}
[data-testid="stMetricLabel"]{color:#667085;font-size:.9rem}[data-testid="stMetricValue"]{color:#252b3d;font-weight:650}
[data-testid="stVerticalBlockBorderWrapper"]{background:rgba(255,255,255,.82);border:1px solid var(--line);border-radius:16px;padding:14px}
[data-testid="stForm"]{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px}
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,[data-testid="stSelectbox"]>div>div,[data-testid="stTextArea"] textarea{border-radius:10px}
.stButton>button,.stDownloadButton>button{border-radius:12px;font-weight:700;min-height:3.15rem;padding:.65rem 1.15rem;font-size:1rem;color:#20263a!important;background:#fff!important;border:1px solid #c8d1e1!important;box-shadow:0 2px 5px rgba(32,38,58,.06)}
.stButton>button[kind=primary],.stFormSubmitButton>button[kind=primary]{background:#3049bf!important;border-color:#3049bf!important;color:#fff!important;min-height:3.35rem;font-size:1.05rem;box-shadow:0 4px 12px rgba(48,73,191,.2)}
[data-testid='stSidebar'] .stButton>button,[data-testid='stSidebar'] .stDownloadButton>button{background:#fff!important;color:#20263a!important;border:1px solid #c8d1e1!important}
[data-testid="stDataFrame"],[data-testid="stTable"]{border:1px solid var(--line);border-radius:12px;overflow:hidden}
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
.insight-card{background:#fff;border:1px solid #dce2eb;border-radius:15px;padding:16px 18px;margin:8px 0;box-shadow:0 4px 14px rgba(33,45,75,.045);color:#20263a}
.insight-card .eyebrow{font-size:.78rem;text-transform:uppercase;letter-spacing:.06em;font-weight:700;color:#596782}
.insight-card .headline{font-size:1.15rem;font-weight:750;color:#20263a;margin:5px 0}
.insight-card .body{font-size:.93rem;line-height:1.5;color:#465168}
.action-card{background:linear-gradient(120deg,#fff 0%,#f8f9ff 100%);border:1px solid #d7deed;border-left:5px solid #3049bf;border-radius:15px;padding:17px 19px;margin:10px 0;color:#20263a}
.action-card h4{margin:4px 0 8px;color:#20263a;font-size:1.08rem}
.action-card p{color:#465168;line-height:1.5;margin:5px 0}
@media(max-width:900px){.hero h1{font-size:1.7rem}.block-container{padding-left:1rem;padding-right:1rem}}
</style><div class="hero"><h1>Dealer 360</h1><p>Management attention workspace · Identify underperformance, investigate root causes, and decide what to do next.</p></div>''',unsafe_allow_html=True)
st.sidebar.markdown('### 🚘 Dealer 360')
st.sidebar.caption('Management attention workspace')
action_dealer_label = st.session_state.get('action_plan_dealer')
nav_pages=['Overview','Dealer Ranking & Diagnosis']
if action_dealer_label:
    nav_pages.append(f'Action Plan [{action_dealer_label}]')
nav_pages += ['Data & Methodology','Manual Dealer Score']
if st.session_state.get('pending_navigation'):
    pending = st.session_state.pop('pending_navigation')
    if pending == 'Action Plan' and action_dealer_label:
        pending = f'Action Plan [{action_dealer_label}]'
    st.session_state['main_navigation']=pending
page=st.sidebar.radio('Navigate to', nav_pages, key='main_navigation', format_func=lambda x: 'Action Plan' if str(x).startswith('Action Plan [') else x)
if isinstance(page, str) and page.startswith('Action Plan ['):
    page='Action Plan'
st.sidebar.divider()
st.sidebar.caption('Upload once. Explore priority dealers, evidence-led diagnosis, and manual assessment from the navigation.')

# Downloadable input template
sample=pd.DataFrame([{'dealer_id':'D001','dealer_name':'Example Motors','state':'Jharkhand','month':'2026-09','sales_target_units':100,'retail_sales_units':78,'sales_growth_yoy_pct':-5,'inventory_days':72,'units_over_90_days':18,'overdue_receivables_inr_lakh':8,'receivables_inr_lakh':20,'average_payment_days':54,'service_sla_compliance_pct':76,'customer_complaints':9,'complaints_per_100_retail_sales':11.5,'estimated_dealer_market_share_pct':12}])
buf=BytesIO()
with pd.ExcelWriter(buf,engine='openpyxl') as writer: sample.to_excel(writer,index=False,sheet_name='Dealer_Input')
st.sidebar.download_button('Download input template',buf.getvalue(),'Dealer360_Input_Template.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
upload=st.sidebar.file_uploader('Upload Dealer 360 workbook (.xlsx)',type=['xlsx'])

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
        'estimated_monthly_market_potential_units'
    ])
    return annual.div(12).where(annual.notna(), monthly)

def scale_risk(s):
    s=pd.to_numeric(s,errors='coerce'); lo,hi=s.quantile(.1),s.quantile(.9)
    if s.notna().sum()==0:return pd.Series(np.nan,index=s.index)
    if pd.isna(lo) or pd.isna(hi) or hi<=lo: lo,hi=s.min(),s.max()
    if pd.isna(lo) or pd.isna(hi) or hi<=lo:return pd.Series(50.,index=s.index)
    return ((s.clip(lo,hi)-lo)/(hi-lo)*100).clip(0,100)

def score_data(df):
    target=numeric(df,['sales_target_units','target_units']); sales=numeric(df,['retail_sales_units','actual_retail_sales_units','sales_actual_units'])
    ach=sales/target.replace(0,np.nan)*100
    if ach.notna().sum()==0: ach=numeric(df,['target_achievement_pct','sales_target_achievement_pct'])
    growth=numeric(df,['sales_growth_yoy_pct','yoy_sales_growth_pct'])
    aged=numeric(df,['units_over_90_days','stock_over_90_days']); invdays=numeric(df,['inventory_days','stock_days'])
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
    comps['Inventory ageing']=pd.concat([agedrisk,invrisk],axis=1).mean(axis=1,skipna=True)
    comps['Payment delays']=pd.concat([scale_risk(overdue),scale_risk(paydays)],axis=1).mean(axis=1,skipna=True)
    comps['Service performance']=(100-service.clip(0,100)).clip(0,100)
    comps['Customer complaints']=scale_risk(complaints)
    # Local market potential is intentionally excluded from risk scoring.
    active_weights=WEIGHTS
    weights=pd.Series(active_weights)
    nume=comps.mul(weights).sum(axis=1,skipna=True); deno=comps.notna().mul(weights).sum(axis=1)
    out=df.copy(); out['attention_score']=(nume/deno.replace(0,np.nan)).round(1)
    out['priority_band']=pd.cut(out.attention_score,[-1,34,64,100],labels=['Low-risk','Mid-risk','High-risk'])
    for c in comps: out[c+' risk']=comps[c].round(1)
    out['_risk_components']=list(comps.to_dict('records'))
    return out,comps

if page=='Manual Dealer Score':
    st.header('Manual Dealer Attention Score')
    st.caption('Enter real operating figures. The app converts them into risk scores using transparent rules; no client-side score calculation is required.')
    with st.form('manual_score_form'):
        name=st.text_input('Dealer name or ID','Manual assessment')
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
        active=st.session_state.get('active_weights',WEIGHTS); denom=sum(active[k] for k,v in vals.items() if pd.notna(v)); score=sum(vals[k]*active[k] for k in vals if pd.notna(vals[k]))/denom if denom else np.nan
        band='Low-risk' if score<35 else ('Mid-risk' if score<65 else 'High-risk')
        a,b,c=st.columns(3); a.metric('Dealer',name or 'Manual assessment'); b.metric('Attention score',f'{score:.1f}/100'); c.metric('Risk category',band)
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
                st.markdown(f'''<div style="border:1px solid #D7DEE7;border-radius:12px;padding:14px;margin-bottom:10px"><div style="font-weight:700">{title}</div><div style="font-size:1.2rem;margin:5px 0">{value}</div><div style="color:#657386;font-size:.9rem">{detail}</div></div>''',unsafe_allow_html=True)
        st.subheader('Factor risk breakdown')
        detail=pd.DataFrame({'Factor':list(vals),'Weight':[f'{active[k]*100:.1f}%' for k in vals],'Calculated risk':[round(vals[k],1) if pd.notna(vals[k]) else np.nan for k in vals],'Weighted contribution':[round(vals[k]*active[k],1) if pd.notna(vals[k]) else np.nan for k in vals]})
        st.dataframe(detail,use_container_width=True,hide_index=True)
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
            st.session_state['action_plan_source']='manual'
            st.session_state['action_plan_dealer']=str(name or 'Manual assessment')
            st.session_state['action_plan_manual_data']={
                'name':str(name or 'Manual assessment'),'target':float(target),'retail':float(retail),'prior':float(prior),
                'stock':float(stock),'over90':float(over90),'over180':float(over180),'receiv':float(receiv),
                'overdue':float(overdue),'paydays':float(paydays),'sla':float(sla),'complaints':float(complaints),
                'annual_market':float(annual_market),'monthly_market':float(retail_market),'score':float(score),'band':band,
                'achievement':float(achievement) if pd.notna(achievement) else None,'growth':float(growth) if pd.notna(growth) else None,
                'overdue_pct':float(overdue_pct) if pd.notna(overdue_pct) else None,'aged_pct':float(aged_pct) if pd.notna(aged_pct) else None,
                'market_ratio':float(share) if pd.notna(share) else None,'risk_values':{k:(float(v) if pd.notna(v) else None) for k,v in vals.items()}}
            st.session_state['action_plan_answers']={'sales':q1,'inventory':q2,'payments':q3,'service':q4,'context':context}
            st.session_state['pending_navigation']='Action Plan'
            st.rerun()

elif page=='Data & Methodology':
    st.header('Data & Methodology')
    st.write('The attention score uses six operational risk factors; local market demand is a comparison variable only. When available, model-by-dealer-by-month data is used to identify likely supply constraints and ageing-model risks. Default weights: '+', '.join(f'{k} ({v*100:.0f}%)' for k,v in WEIGHTS.items())+'. Default weights are Sales versus target 25%, Less sales growth 10%, Inventory ageing 20%, Payment delays 20%, Service performance 10%, and Customer complaints 15%.')
    st.write('Risk scores are scaled against the uploaded dealer group where appropriate. Missing components are excluded and remaining weights re-normalised.')
    st.warning("Local market potential is a comparison-only estimate and is excluded from the attention score. Sales growth is also displayed as context; only negative growth contributes to the 'Less sales growth' risk factor. The supplied dataset is synthetic; weights and thresholds require business validation.")
    st.markdown('**Expected workbook:** `monthly_dealer_kpis` sheet, optionally with `dealer_master`; a simpler `Dealer_Input` sheet is also supported.')

elif page=='Overview' and not upload:
    st.header('Overview')
    st.write('Upload the detailed Dealer 360 workbook in the sidebar to explore monthly attention trends and dealer rankings.')
    st.info('You can use Manual Dealer Score independently of a workbook upload.')

if page=='Action Plan' and st.session_state.get('action_plan_source')=='manual':
    md=st.session_state.get('action_plan_manual_data',{})
    ans=st.session_state.get('action_plan_answers',{})
    dealer_name=st.session_state.get('action_plan_dealer','Manual assessment')
    st.markdown("<div class='hero'><h1>Action Plan ["+str(dealer_name)+"]</h1><p>Manual dealer assessment · Attention score "+format(float(md.get('score',0)),'.1f')+"/100 · "+str(md.get('band','Unclassified'))+"</p></div>",unsafe_allow_html=True)
    st.subheader('Management takeaway')
    st.write('This plan combines the entered operating metrics with the investigation responses. Validate hypotheses against dealer records before making credit, inventory or allocation decisions.')
    action_items=[]
    achievement=md.get('achievement'); growth=md.get('growth'); aged_pct=md.get('aged_pct'); overdue_pct=md.get('overdue_pct')
    retail=md.get('retail',0); target=md.get('target',0); stock=md.get('stock',0); over90=md.get('over90',0); over180=md.get('over180',0)
    paydays=md.get('paydays',0); sla=md.get('sla',100); complaints=md.get('complaints',0); market=md.get('monthly_market',0)
    if achievement is not None and achievement<90:
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
    if (aged_pct is not None and aged_pct>=25) or over180>0 or ans.get('inventory') in ['Specific models/variants are ageing','Stock arrived recently but demand is weak','Stock mix does not match local preference']:
        diagnosis='Ageing inventory may be tying up working capital; the selected context helps distinguish slow demand from a model-mix mismatch.'
        action='Build a model/variant ageing ladder (0–30, 31–60, 61–90, 91–180 and 180+ days) and compare each variant’s on-hand stock with its last 3-month retail run-rate. Transfer variants with high age and weak local movement; protect variants with recurring stockouts. Avoid blanket replenishment cuts or discounting before checking margin and demand.'
        if ans.get('inventory')=='Stock mix does not match local preference':
            action='Prepare a model/variant matrix of current stock, 90+/180+ day units, last 3-month retail sales and local category demand proxy. Identify variants with both high ageing and weak movement for transfer or targeted offers; preserve supply for variants with proven lost orders. Review weekly for 30 days.'
        aged_evidence=f'Inventory {stock:.0f} units; 90+ day {over90:.0f}; 180+ day {over180:.0f}.'
        if aged_pct is not None: aged_evidence+=f' 90+ share {aged_pct:.1f}%.'
        action_items.append(('P1 · Correct inventory mix',diagnosis,action,aged_evidence,'Dealer stock manager + regional supply planner · Weekly review for 30 days'))
    if (overdue_pct is not None and overdue_pct>=25) or paydays>=45 or ans.get('payments') not in ['Not yet known',None]:
        diagnosis='Payment delays need invoice-level separation of genuinely overdue collectible debt, disputes and due-date/credit-term mismatches.'
        pay_answer=ans.get('payments')
        if pay_answer=='Invoice or credit-note dispute': action='Within five working days, reconcile disputed invoices and credit notes against delivery proof and the ledger. Split disputed from undisputed exposure, assign an owner and closure date to each case, then calculate collectible overdue exposure before any credit decision.'
        elif pay_answer=='Collection follow-up is weak': action='Create an invoice-wise collection tracker with amount, days overdue, named owner, promised date and actual receipt. Contact the largest/oldest undisputed balances first, review missed promises twice weekly and escalate only under company credit policy.'
        elif pay_answer=='Customer/dealer cash-flow issue': action='Prepare a cash commitment calendar backed by invoice ageing and actual payment history. Review exposure and revised terms with the authorised credit team; do not rely on verbal promises or relax limits without approval.'
        else: action='Reconcile due dates and contractual credit terms, then prioritise the oldest and largest undisputed invoices. Record dated commitments and review missed promises twice weekly; separate documentation disputes from cash collection issues.'
        pay_evidence=f'Average payment delay {paydays:.0f} days; overdue {md.get("overdue",0):.1f} lakh / receivables {md.get("receiv",0):.1f} lakh.'
        if overdue_pct is not None: pay_evidence+=f' Overdue share {overdue_pct:.1f}%.'
        action_items.append(('P1 · Reduce overdue exposure',diagnosis,action,pay_evidence,'Finance controller + dealer accounts lead · Review in 7 days'))
    if sla<85 or (retail>0 and complaints/retail*100>=5) or ans.get('service') not in ['Not yet known',None,'No clear service issue']:
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
        card="<div class='action-card'><div class='eyebrow'>"+title+"</div><h4>Why this matters</h4><p>"+diagnosis+"</p><h4>Recommended decision and execution</h4><p>"+action+"</p><p><b>Evidence:</b> "+evidence+"</p><p><b>Accountability:</b> "+owner+"</p></div>"
        st.markdown(card,unsafe_allow_html=True)
    st.subheader('Validation checklist')
    for item in ['Confirm model-level retail, stockout and ageing data for the same month.','Reconcile receivables against invoice due dates and disputed balances.','Validate the local market estimate and catchment before treating it as share.','Record the baseline, owner, due date and measurable outcome before the next review.']:
        st.checkbox(item,key='manual_plan_check_'+str(abs(hash(item))))
    st.download_button('Download this action plan',pd.DataFrame(action_items,columns=['Priority','Diagnosis','Action','Evidence','Owner / review']).to_csv(index=False).encode('utf-8'),f'{str(dealer_name).replace(" ","_")}_Action_Plan.csv','text/csv')
elif upload and page not in ['Manual Dealer Score','Data & Methodology']:
    try:
        xls=pd.ExcelFile(upload); names={s.lower():s for s in xls.sheet_names}
        model_history=pd.read_excel(upload,sheet_name=names['model_month_performance']) if 'model_month_performance' in names else pd.DataFrame()
        if 'monthly_dealer_kpis' in names:
            history=pd.read_excel(upload,sheet_name=names['monthly_dealer_kpis'])
            master=pd.read_excel(upload,sheet_name=names['dealer_master']) if 'dealer_master' in names else pd.DataFrame()
        elif 'dealer_input' in names: history=pd.read_excel(upload,sheet_name=names['dealer_input']); master=pd.DataFrame()
        else: history=pd.read_excel(upload,sheet_name=xls.sheet_names[0]); master=pd.DataFrame()
        history.columns=[str(c).strip() for c in history.columns]
        monthcol=col(history,['month','reporting_month'])
        if monthcol:
            history[monthcol]=history[monthcol].astype(str); months=sorted(history[monthcol].dropna().unique())
            selected=st.sidebar.selectbox('Reporting month',months,index=len(months)-1)
            current=history[history[monthcol]==selected].copy()
        else: selected='Uploaded snapshot'; current=history.copy()
        scored,components=score_data(current)
        idcol=col(scored,['dealer_id','dealer_code']) or col(scored,['dealer_name','dealer','outlet_name'])
        namecol=col(scored,['dealer_name','dealer','outlet_name']) or idcol
        if not namecol: scored['Dealer']='Dealer'; namecol='Dealer'
        if not idcol: idcol=namecol
        scored['Dealer display']=scored[namecol].astype(str)
        if page=='Overview':
            st.header('Overview')
            threshold_default=50
            # Create the historical outcome label and select a threshold that balances precision and recall.
            hm=col(history,['month','reporting_month']); hd=col(history,['dealer_id','dealer_code','dealer_name'])
            hist_eval=None; best_threshold=threshold_default; best_f1=-1
            if hm and hd:
                hc=history.copy(); hc['_month']=pd.to_datetime(hc[hm],errors='coerce').dt.to_period('M').dt.to_timestamp()
                hc['_dealer_key']=hc[hd].astype(str); hc=hc.dropna(subset=['_month']).sort_values(['_dealer_key','_month'])
                achc=numeric(hc,['target_achievement_pct','sales_target_achievement_pct'])
                if achc.isna().all():
                    tarc=numeric(hc,['sales_target_units','target_units']); salc=numeric(hc,['retail_sales_units','actual_retail_sales_units']); achc=salc/tarc.replace(0,np.nan)*100
                invc=numeric(hc,['inventory_days','stock_days']); overc=numeric(hc,['overdue_pct_receivables']); slac=numeric(hc,['service_sla_compliance_pct','service_sla_pct'])
                hc['_ach']=achc; hc['_inv']=invc; hc['_overdue']=overc; hc['_sla']=slac
                for metric in ['_ach','_inv','_overdue','_sla']: hc['_next'+metric]=hc.groupby('_dealer_key')[metric].shift(-1)
                conditions=pd.DataFrame(index=hc.index)
                conditions['Sales deterioration']=(hc['_next_ach'] <= hc['_ach'] * 0.80)
                conditions['Inventory deterioration']=(hc['_next_inv'] >= hc['_inv'] * 1.20)
                conditions['Payment deterioration']=(hc['_next_overdue'] >= hc['_overdue'] * 1.20)
                conditions['Service deterioration']=(hc['_next_sla'] <= hc['_sla'] * 0.80)
                hc['_deterioration']=conditions.fillna(False).any(axis=1)
                hc['_has_next']=hc.groupby('_dealer_key')['_month'].shift(-1).eq(hc['_month']+pd.offsets.MonthBegin(1))
                # Score each dealer-month independently against peers in the same month.
                score_rows=[]
                for m,g in history.groupby(hm,sort=True):
                    tmp,_=score_data(g.copy()); tmp['_month_label']=str(m); tmp['_dealer_key']=g[hd].astype(str).values
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
                        for t in range(20,81,5):
                            pred=train['attention_score']>=t; actual=train['_deterioration'].astype(bool)
                            tp=int((pred & actual).sum()); fp=int((pred & ~actual).sum()); fn=int((~pred & actual).sum())
                            precision=tp/(tp+fp) if tp+fp else 0; recall=tp/(tp+fn) if tp+fn else 0
                            f1=2*precision*recall/(precision+recall) if precision+recall else 0
                            if f1>best_f1: best_f1=f1; best_threshold=t
            threshold=st.slider('Attention score criterion — flag dealers scoring at or above',0,100,int(best_threshold),5,help='Default is selected from historical back-testing to balance precision and recall. It is a prototype threshold, not a guaranteed accuracy level.')
            scored['Flag status']=np.where(scored.attention_score>=threshold,'Flagged','Below criterion')
            scored['Risk category']=pd.cut(scored.attention_score,[-1,34,64,100],labels=['Low-risk','Mid-risk','High-risk'])
            k1,k2,k3,k4=st.columns(4)
            k1.metric('Dealers analysed',len(scored)); k2.metric('Flagged at selected criterion',int((scored.attention_score>=threshold).sum())); k3.metric('Attention criterion',f'≥ {threshold}/100'); k4.metric('Reporting period',str(selected))
            st.subheader('Risk distribution')
            dist=scored.groupby('Risk category',observed=False).attention_score.agg(['count','mean']).reindex(['Low-risk','Mid-risk','High-risk']).reset_index()
            cc=st.columns(3)
            for i,r in dist.iterrows():
                avg=f"Mean score {r['mean']:.1f}" if pd.notna(r['mean']) else 'No scored dealers'
                cc[i].metric(str(r['Risk category']),f"{int(r['count'])} dealers",avg)
            st.subheader('What is driving underperformance?')
            factor_cols=[f+' risk' for f in WEIGHTS if f+' risk' in scored.columns]
            if factor_cols:
                scored['Primary contributing factor']=scored[factor_cols].astype(float).idxmax(axis=1).str.replace(' risk','',regex=False)
                factor_groups=scored.groupby('Primary contributing factor',dropna=False).agg(Dealer_count=('Dealer display','count')).reset_index().sort_values('Dealer_count',ascending=False)
                st.plotly_chart(px.bar(factor_groups,x='Primary contributing factor',y='Dealer_count',text='Dealer_count',title='Dealers grouped by their highest-risk factor'),use_container_width=True)
            st.subheader('Deterioration vs deterioration correctly flagged')
            st.caption('Actual deterioration is a next-month outcome. Predicted deterioration is the subset of those cases whose prior-month attention score met your selected criterion. This measures captured cases, not all alerts.')
            if hist_eval is not None and len(hist_eval):
                eval_df=hist_eval.copy(); eval_df['_predicted_hit']=((eval_df['attention_score']>=threshold) & eval_df['_deterioration'].astype(bool)).astype(int)
                monthly=eval_df.groupby('_month',as_index=False).agg(**{'Total deterioration':('_deterioration','sum'),'Predicted deterioration':('_predicted_hit','sum')})
                monthly['Total deterioration']=monthly['Total deterioration'].astype(int); monthly['Predicted deterioration']=monthly['Predicted deterioration'].astype(int)
                fig=go.Figure()
                fig.add_trace(go.Scatter(x=monthly['_month'],y=monthly['Total deterioration'],name='Total deterioration',mode='lines+markers+text',text=monthly['Total deterioration'],textposition='top center',fill='tozeroy',line=dict(width=2)))
                fig.add_trace(go.Scatter(x=monthly['_month'],y=monthly['Predicted deterioration'],name='Deterioration flagged by model',mode='lines+markers+text',text=monthly['Predicted deterioration'],textposition='bottom center',fill='tozeroy',line=dict(width=2)))
                fig.update_layout(title='How many subsequent deterioration cases did the model flag?',xaxis_title='Month of original dealer observation',yaxis_title='Dealer-months',legend_title='',hovermode='x unified')
                st.plotly_chart(fig,use_container_width=True)
                actual=int(eval_df['_deterioration'].sum()); hits=int(eval_df['_predicted_hit'].sum()); flagged=int((eval_df['attention_score']>=threshold).sum())
                recall=hits/actual*100 if actual else 0; precision=hits/flagged*100 if flagged else 0
                a,b,c=st.columns(3); a.metric('Deterioration cases in test set',actual); b.metric('Cases flagged in advance',hits); c.metric('Captured deterioration',f'{recall:.1f}%')
                st.caption(f'Holdout only: {precision:.1f}% of flagged dealer-months were followed by a qualifying deterioration event. The criterion was selected on earlier months; it is not guaranteed to be accurate in future deployments. The deterioration definition uses a ≥20% relative fall in target achievement, ≥20% relative rise in inventory days, ≥20% relative rise in overdue percentage, or ≥20% relative fall in service SLA. Historical fit is not proof of future accuracy; the data is synthetic.')
            else: st.warning('The workbook does not have enough matched dealer-month history to validate deterioration against the selected criterion.')
        elif page=='Dealer Ranking & Diagnosis':
            st.header('Dealer Ranking & Diagnosis')
            ranked=scored.sort_values('attention_score',ascending=False).copy()
            ranked['priority_band']=pd.cut(ranked.attention_score,[-1,34,64,100],labels=['Low-risk','Mid-risk','High-risk'])
            st.caption('Start with the risk distribution, then focus on the dealers whose scores cross the selected attention criterion. The full diagnostic table is intentionally hidden.')
            band_order=['Low-risk','Mid-risk','High-risk']
            band_cols=st.columns(3)
            for ix,band in enumerate(band_order):
                bg=ranked[ranked['priority_band'].astype(str)==band]
                mean_score=bg['attention_score'].mean()
                band_cols[ix].metric(band, f'{len(bg)} dealers', f'Attention criterion ≥ {threshold}/100' if 'threshold' in locals() else (f'Mean score {mean_score:.1f}/100' if pd.notna(mean_score) else 'No scored dealers'))
            flagged=ranked[ranked['attention_score']>=threshold].copy() if 'threshold' in locals() else ranked[ranked['attention_score']>=50].copy()
            st.subheader('Dealers requiring the most attention')
            if flagged.empty:
                st.success('No dealers meet the current attention criterion. You can still select any dealer below for diagnosis.')
                shortlist=ranked.head(min(5,len(ranked)))
            else:
                shortlist=flagged.head(min(8,len(flagged)))
                st.caption(f'{len(flagged)} dealers are flagged. Showing the highest-priority {len(shortlist)} first.')
                cols=st.columns(2)
                for ix,(_,dr) in enumerate(shortlist.iterrows()):
                    factor_risks={k:dr.get(k+' risk',np.nan) for k in WEIGHTS}
                    drivers=sorted([(k,v) for k,v in factor_risks.items() if pd.notna(v)],key=lambda z:z[1],reverse=True)[:2]
                    driver_text=' · '.join(f'{k} ({v:.0f}/100)' for k,v in drivers) or 'Risk drivers unavailable'
                    band=str(dr.get('priority_band','Unclassified'))
                    with cols[ix%2]:
                        st.markdown(f'''<div class="insight-card"><div class="eyebrow">{band} · Attention {dr['attention_score']:.1f}/100</div><div class="headline">{dr['Dealer display']}</div><div class="body"><b>Main drivers:</b> {driver_text}</div></div>''',unsafe_allow_html=True)
            choices=shortlist['Dealer display'].astype(str).tolist()
            if not choices: choices=ranked['Dealer display'].astype(str).tolist()
            selected_dealer=st.selectbox('Choose a priority dealer for full diagnosis',choices)
            row=ranked[ranked['Dealer display']==selected_dealer].iloc[0]
            risks={k:row.get(k+' risk',np.nan) for k in WEIGHTS}; riskdf=pd.DataFrame({'Factor':list(risks),'Risk score':[risks[k] for k in risks]})
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
                        st.plotly_chart(figm,use_container_width=True)
                        with st.expander('View model-level figures'):
                            st.dataframe(model_roll,use_container_width=True,hide_index=True)
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
                if pd.notna(inv) and inv>60: cards.append(('More than 60 days of inventory',f'{inv:.0f} days','Review stock turns, replenishment and ageing by model/variant.'))
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
                    with cc[i%2]: st.markdown(f'''<div style="border:1px solid #D7DEE7;border-radius:12px;padding:14px;margin-bottom:10px"><div style="font-weight:700">{title}</div><div style="font-size:1.2rem;margin:5px 0">{value}</div><div style="color:#657386;font-size:.9rem">{detail}</div></div>''',unsafe_allow_html=True)
            st.subheader('Primary risk drivers')
            st.caption('Focus on the highest-risk factors and investigate the likely operational cause before generating an action plan.')
            top_risks=sorted([(k,v) for k,v in risks.items() if pd.notna(v)],key=lambda z:z[1],reverse=True)
            st.plotly_chart(px.bar(riskdf,x='Risk score',y='Factor',orientation='h',range_x=[0,100],title=f'{selected_dealer}: factor-level risk'),use_container_width=True)
            st.subheader('Investigate underlying causes')
            st.caption('Please add operational context. The app will combine these answers with the dealer KPIs to produce more specific diagnostic insights.')
            q1=st.selectbox('Sales: which best describes the issue?', ['Not yet known','Low enquiry/footfall','Low conversion','Model/variant unavailable','Competitor offer or new launch','Target may be unrealistic'],key='diag_q_sales_'+str(selected_dealer))
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
                for insight in insights: st.markdown('- '+insight)
            else: st.info('Select the best-known operational causes above or add field evidence to refine the diagnosis. Until then, the app will show KPI-based hypotheses only.')
            triggered=sorted([(k,v) for k,v in risks.items() if pd.notna(v) and v>=50],key=lambda x:x[1],reverse=True)
            if triggered: st.caption('Highest numeric risk signals: '+', '.join(f'{k} ({v:.0f}/100)' for k,v in triggered)+'.')
            st.caption('Recommendations are conditional hypotheses, not confirmed root causes. Local market potential and positive sales growth are comparison/context metrics, not negative scoring factors.')
            st.divider()
            st.markdown('### Ready to turn this diagnosis into a plan?')
            st.write('Your selected operational answers and the dealer’s measured KPIs will be carried into a separate action-plan workspace.')
            if st.button('Devise action plan', type='primary', key='devise_plan_'+str(selected_dealer)):
                st.session_state['action_plan_source']='workbook'
                st.session_state['action_plan_dealer']=str(selected_dealer)
                st.session_state['action_plan_answers']={
                    'sales':q1, 'inventory':q2, 'payments':q3, 'service':q4, 'context':context
                }
                st.session_state['pending_navigation']='Action Plan'
                st.rerun()
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
                    drivers_plan=sorted([(k,float(v)) for k,v in risks_plan.items() if pd.notna(v)],key=lambda x:x[1],reverse=True)
                    st.markdown(f'''<div class="hero"><h1>Action Plan [{selected_dealer}]</h1><p>Evidence-led action plan · Attention score {float(pr['attention_score']):.1f}/100 · {str(pr.get('priority_band','Unclassified'))}</p></div>''',unsafe_allow_html=True)
                    if drivers_plan:
                        st.subheader('Management takeaway')
                        top3=drivers_plan[:3]
                        st.markdown(' '.join([f'**{i+1}. {k} ({v:.0f}/100)**' for i,(k,v) in enumerate(top3)]))
                        st.caption('Priorities are ordered by the current model’s factor risk scores. Treat them as investigation priorities, not proof of cause.')
                    # Measured evidence and specific, conditional decisions
                    prdf=pd.DataFrame([pr])
                    target=numeric(prdf,['sales_target_units']).iloc[0]; retail=numeric(prdf,['retail_sales_units']).iloc[0]
                    ach=numeric(prdf,['target_achievement_pct']).iloc[0]
                    if pd.isna(ach) and pd.notna(target) and target>0 and pd.notna(retail): ach=retail/target*100
                    gap=max(0,target-retail) if pd.notna(target) and pd.notna(retail) else np.nan
                    growth=numeric(prdf,['sales_growth_yoy_pct']).iloc[0]
                    invdays=numeric(prdf,['inventory_days']).iloc[0]; age90=numeric(prdf,['units_over_90_days']).iloc[0]; age180=numeric(prdf,['units_over_180_days']).iloc[0]
                    overdue_pct=numeric(prdf,['overdue_pct_receivables']).iloc[0]; overdue_amt=numeric(prdf,['overdue_receivables_inr_lakh']).iloc[0]; paydays=numeric(prdf,['average_payment_days']).iloc[0]
                    sla=numeric(prdf,['service_sla_compliance_pct']).iloc[0]; complaints=numeric(prdf,['complaints_per_100_retail_sales']).iloc[0]
                    market_share=numeric(prdf,['estimated_dealer_market_share_pct']).iloc[0]
                    peers=scored.copy()
                    region_col=col(peers,['region']); this_region=pr.get(region_col) if region_col else None
                    if region_col and pd.notna(this_region): peers=peers[peers[region_col]==this_region]
                    peer_ach=numeric(peers,['target_achievement_pct'])
                    if peer_ach.notna().sum()==0:
                        ps=numeric(peers,['retail_sales_units']); pt=numeric(peers,['sales_target_units']); peer_ach=ps/pt.replace(0,np.nan)*100
                    peer_median=float(peer_ach.median()) if peer_ach.notna().any() else np.nan
                    st.subheader('Evidence snapshot')
                    metrics=[]
                    if pd.notna(ach): metrics.append(('Target achievement',f'{ach:.1f}%',f'{gap:.0f} units short of target' if pd.notna(gap) else 'Calculated from retail sales and target'))
                    if pd.notna(growth): metrics.append(('Year-on-year growth',f'{growth:+.1f}%', 'Negative growth indicates contraction; compare against same-period model and market trends'))
                    if pd.notna(invdays): metrics.append(('Inventory cover',f'{invdays:.0f} days','Review against 60-day operating trigger and model-level ageing'))
                    if pd.notna(age90): metrics.append(('Stock aged 90+ days',f'{age90:.0f} units','Potential working-capital and model-mix exposure'))
                    if pd.notna(overdue_pct): metrics.append(('Receivables overdue',f'{overdue_pct:.1f}%',f'₹{overdue_amt:.1f} lakh overdue' if pd.notna(overdue_amt) else 'Review invoice-level ageing'))
                    if pd.notna(sla): metrics.append(('Service SLA',f'{sla:.1f}%','Check backlog, parts and technician capacity'))
                    if pd.notna(complaints): metrics.append(('Complaints / 100 retail sales',f'{complaints:.1f}','Volume-adjusted customer-experience signal'))
                    if pd.notna(market_share): metrics.append(('Estimated local market share',f'{market_share:.1f}%','Comparison only; market estimate is not a scoring penalty'))
                    monthly_market=market_potential_monthly(prdf).iloc[0]
                    retail_units=numeric(prdf,['retail_sales_units']).iloc[0]
                    if pd.notna(monthly_market) and monthly_market>0 and pd.notna(retail_units):
                        annual_market=monthly_market*12
                        metrics.append(('Monthly regional market potential',f'{monthly_market:,.0f} units/month',f'Annual estimate {annual_market:,.0f} ÷ 12; dealer retail sales {retail_units:,.0f} units ({retail_units/monthly_market*100:.1f}% directional ratio). Comparison only; validate catchment coverage.'))
                    for ix in range(0,len(metrics),3):
                        cc=st.columns(3)
                        for j,(label,value,note) in enumerate(metrics[ix:ix+3]):
                            with cc[j]:
                                st.markdown(f'<div class="insight-card"><div class="eyebrow">{label}</div><div class="headline">{value}</div><div class="body">{note}</div></div>',unsafe_allow_html=True)
                    st.subheader('Prioritised actions')
                    action_items=[]
                    # Sales
                    if pd.notna(ach) and ach<90 or ('Sales versus target' in risks_plan and pd.notna(risks_plan['Sales versus target']) and risks_plan['Sales versus target']>=35):
                        if answers.get('sales')=='Low enquiry/footfall':
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
                        action_items.append(('P1 · Recover retail sales',diagnosis,action, f'Measured gap: {gap:.0f} units; achievement {ach:.1f}%; peer median {peer_median:.1f}%.' if pd.notna(gap) and pd.notna(peer_median) else (f'Measured target achievement: {ach:.1f}%.' if pd.notna(ach) else 'Target/retail fields are incomplete; quantify the gap before committing a unit target.'), 'Owner: Dealer principal + regional sales manager · Review: 7 days'))
                    # Inventory and demand context
                    if (pd.notna(invdays) and invdays>60) or (pd.notna(age90) and age90>0) or answers.get('inventory') not in (None,'Not yet known','No major inventory issue'):
                        if answers.get('inventory')=='Stock mix mismatch with local demand' or (pd.notna(age90) and age90>0 and pd.notna(market_share) and market_share<5):
                            diagnosis='The evidence is consistent with a stock-mix issue: aged stock can coexist with low local share, but the market estimate is only a directional comparison.'
                            action='Create a model/variant matrix with on-hand units, 90+/180+ day stock, monthly retail run-rate, stockout days and local category demand proxy. Transfer slow-moving variants where another dealer has demand; protect replenishment for variants with recurring stockouts. Avoid broad inventory cuts.'
                        else:
                            diagnosis='Inventory cover/ageing indicates cash may be tied up in slow-moving units. The data does not establish which models are responsible unless model-level records are available.'
                            action='Split inventory by model and ageing bucket; pause replenishment only for variants whose cover exceeds the agreed limit and whose retail run-rate is weak. Review 90+ and 180+ day units weekly and test transfers or focused retail offers.'
                        action_items.append(('P1/P2 · Rebalance inventory',diagnosis,action, f'Inventory cover: {invdays:.0f} days; 90+ day units: {age90:.0f}; 180+ day units: {age180:.0f}.' if pd.notna(invdays) and pd.notna(age90) and pd.notna(age180) else 'Some inventory indicators are missing; validate model-level ageing before changing allocation.', 'Owner: Dealer stock manager + regional supply planner · Review: 14 days'))
                    if (pd.notna(overdue_pct) and overdue_pct>=25) or (pd.notna(paydays) and paydays>45) or answers.get('payments') not in (None,'Not yet known'):
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
                    if (pd.notna(sla) and sla<85) or (pd.notna(complaints) and complaints>5) or answers.get('service') not in (None,'Not yet known','Not yet known / other'):
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
                    if pd.notna(market_share):
                        action_items.append(('P2 · Validate local-market opportunity','Estimated dealer market share is a comparison proxy, not a direct measure of addressable demand. A low share may reflect competition, catchment differences or imperfect market estimates.','Compare the dealer’s retail run-rate with same-category regional registrations and peer share; map the top models sold locally, competitor locations/offers, and stockout/lost-order history. Decide whether the gap calls for local demand generation, a model-mix change or supply recovery only after these checks. ',f'Estimated market share: {market_share:.1f}% (directional estimate; not included in risk score).','Owner: Regional manager + dealer sales lead · Review: 30 days'))
                    if answers.get('context','').strip():
                        action_items.append(('Field evidence to validate', 'The dealer/manager supplied additional context. Treat it as a hypothesis until matched to records.', 'Validate this note against lead records, model availability, invoices, service cases or complaint details: '+answers['context'].strip(), 'Evidence source: dealer/manager note', 'Owner: Regional manager · Review: next review meeting'))
                    if not action_items:
                        action_items.append(('P1 · Establish a baseline','No material risk trigger was found in the available fields, or key fields are missing.','Validate the latest month’s target, retail sales, inventory ageing, overdue invoices, service SLA and complaint rate. Set a monthly baseline before committing a corrective intervention.', 'Evidence gap: no action-specific threshold crossed in available data.', 'Owner: Dealer manager · Review: 14 days'))
                    for title,diagnosis,action,evidence,owner in action_items:
                        st.markdown(f'''<div class="action-card"><div class="eyebrow">{title}</div><h4>Why this matters</h4><p>{diagnosis}</p><h4>Recommended decision and execution</h4><p>{action}</p><p><b>Evidence:</b> {evidence}</p><p><b>Accountability:</b> {owner}</p></div>''',unsafe_allow_html=True)
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
elif not upload and page == 'Dealer Ranking & Diagnosis':
    st.info('Upload a Dealer 360 workbook in the sidebar to use this section.')
