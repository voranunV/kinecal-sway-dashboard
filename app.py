"""ActiveAge Lab • camera-derived postural sway, using supplied CSV exports only."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from html import escape
from math import cos, sin, pi
from pathlib import Path
from urllib.parse import quote
from data_access import (load_data, DataError, METRICS, MOVEMENTS, CONDITIONS,
                         participant_ids, filter_observed, coverage)
from comparison import COHORTS, age_group, reference_cohort, percentile, paired_percent_change

st.set_page_config(page_title='ActiveAge Lab | Sway Explorer', page_icon='◌', layout='wide')
INDIGO = '#343A73'
SKY = '#5DADE2'
TURQUOISE = '#5BC0BE'
COLORS = [INDIGO, SKY, TURQUOISE, '#8978BA']
DISCLAIMER = ('This dashboard provides measurement and statistical comparison of camera-derived '
              'postural sway. It is not a diagnostic tool and does not predict future falls.')
DESCRIPTIONS = {'RDIST': 'Root-mean-square sway distance', 'MVELO': 'Mean sway velocity',
                'MFREQ': 'Mean sway-frequency measure', 'AREA_CE': 'Confidence-ellipse area'}
PAGES = ['Overview', 'Participant Comparison', 'Eyes Open vs Eyes Closed',
         'Movement Comparison', 'Model Evidence / Limitations']

# Inline SVG masks leave the native radio controls accessible by keyboard.
NAV_PATHS = [
    '<path d="m3 10 9-7 9 7v10H3zM9 20v-6h6v6"/>',
    '<circle cx="12" cy="7" r="3"/><path d="M5 21v-2a7 7 0 0 1 14 0v2"/>',
    '<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    '<path d="M3 20h18M5 16v-5h3v5M11 16V5h3v11M17 16V9h3v7"/>',
    '<path d="M5 2h10l4 4v16H5zM15 2v5h4M8 12h8M8 16h6"/>',
]
ASSETS = Path(__file__).resolve().parent / 'assets'


def nav_icon_css():
    rules = []
    for index, drawing in enumerate(NAV_PATHS, 1):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
               f'fill="none" stroke="black" stroke-width="2" stroke-linecap="round" '
               f'stroke-linejoin="round">{drawing}</svg>')
        rules.append(f'[data-testid="stSidebar"] [role="radiogroup"] > div:nth-child({index}) '
                     f'[data-testid="stRadioOption"]::before '
                     '{mask-image:url("data:image/svg+xml,' + quote(svg, safe='') + '");}')
    return '\n'.join(rules)

st.markdown('''<style>
.stApp {background: #F6F9FC; color: #202C48;}
.block-container {max-width: 1440px; padding-top: 2.5rem; padding-bottom: 2rem;}
h1 {letter-spacing: -.045em; font-weight: 750 !important;
 height: auto; line-height: 1.3; overflow: visible;}
h2, h3 {letter-spacing: -.025em;}
[data-testid="stMetric"] {background: #FFFFFF; border: 1px solid #DFE6F0;
 border-radius: 16px; padding: 16px 19px; box-shadow: 0 4px 18px rgba(42,49,99,.04);}
[data-testid="stMetricValue"] {font-variant-numeric: tabular-nums;}
[data-testid="stMetricValue"] > div {white-space: normal; overflow-wrap: anywhere;
 font-size: 1.8rem; line-height: 1.25;}
[data-testid="stMetricLabel"] p {white-space: normal;}
[data-testid="stSidebar"] {background:#2A3163; color:#F5F8FF; border-right: 0;}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {color:#F5F8FF;}
[data-testid="stSidebar"] hr {border-color:rgba(255,255,255,.2);}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {gap:.35rem;}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > div {width:100%;}
[data-testid="stSidebar"] [data-testid="stRadioOption"] {
  display:flex; width:100%; min-height:48px; padding:.65rem .85rem;
  border-radius:12px; background:transparent; color:#F5F8FF;
  transition:background-color .15s ease; cursor:pointer; align-items:center; box-sizing:border-box;
  gap:.75rem;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"]::before {
  content:""; display:block; width:20px; height:20px; flex:0 0 20px;
  background:currentColor; mask-repeat:no-repeat; mask-position:center; mask-size:contain;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {background:rgba(255,255,255,.08);}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {background:#5DADE2; color:#14254A; font-weight:700;}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:focus-within {outline:2px solid #5BC0BE; outline-offset:2px;}
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child {display:none;}
[data-testid="stSidebar"] [data-testid="stRadioOption"] p {color:inherit; white-space:normal; overflow-wrap:anywhere; line-height:1.3;}
[data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] {
  min-height:calc(100vh - 8rem); display:flex; flex-direction:column;
}
[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-footer) {margin-top:auto;}
.brand-lockup {display:flex; align-items:center; gap:.8rem; margin:.3rem 0 .55rem;}
.brand-lockup svg {width:62px; height:62px; flex:0 0 62px;}
.brand-name {font-size:1.32rem; font-weight:800; letter-spacing:.15em; line-height:1.1; color:white;}
.brand-sub {font-size:.78rem; color:#B8D8E9; margin-top:.25rem; line-height:1.3;}
.sidebar-footer {border-top:1px solid rgba(196,222,244,.3); margin-top:1.2rem; padding-top:.5rem;}
.sidebar-footer svg {display:block; width:100%; max-height:150px; margin:0 auto -.3rem;}
.sidebar-footer .tagline {font-size:1rem; font-style:italic; line-height:1.35;
  color:#D9F3FA; margin:0 0 .8rem; letter-spacing:.01em;}
.sidebar-footer .version {font-size:.73rem; color:#BCD3E9; line-height:1.55; margin:0;}
.sidebar-footer .detail {font-size:.7rem; color:#BACFE5; line-height:1.5; margin:.55rem 0 0;}
.eyebrow {font-size: .76rem; letter-spacing: .17em; font-weight: 700; color: #343A73;
 height: auto; line-height: 1.6; padding-block: .15rem; overflow: visible;}
.sidebar-brand {color:#8BD8DC !important; font-size:.76rem; letter-spacing:.15em; font-weight:750;}
.scope {border-left: 3px solid #7B91AF; padding: .7rem 1rem; background:#EDF2F7;
 color: #42536B; font-size:.87rem; border-radius: 0 8px 8px 0; margin-bottom:1.4rem;}
.gauge-grid {display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin:1rem 0;}
.gauge-card {background:#FFF; border:1px solid #DFE6F0; border-radius:16px;
 padding:18px 12px 15px; text-align:center; min-width:0; box-shadow:0 4px 18px rgba(42,49,99,.04);}
.gauge-card h3 {font-size:1rem; color:#273653; margin:0;}
.gauge-card svg {display:block; width:100%; max-width:210px; margin:0 auto;}
.gauge-card .gauge-note {font-size:.78rem; color:#596A83; line-height:1.35; margin:.1rem 0 0;}
.gauge-card .gauge-value {font-size:1.6rem; font-weight:750; fill:#273653;}
.gauge-card .gauge-sub {font-size:.7rem; fill:#596A83;}
@media(max-width:1100px) {.gauge-grid {grid-template-columns:repeat(2,minmax(0,1fr));}}
@media(max-width:650px) {.gauge-grid {grid-template-columns:1fr;}}
</style>''', unsafe_allow_html=True)
st.markdown('<style>' + nav_icon_css() + '</style>', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def get_data():
    return load_data()


try:
    data = get_data()
except DataError as exc:
    st.error(f'Data validation failed. {exc}')
    st.info('Restore the original CSV exports in the data folder, then restart the app.')
    st.stop()

obs = data['sway_clean_long']
people = data['participants']
models = data['model_summary']
expected = data['participant_expected_sway']
pairs = data['eo_ec_paired']
summary = data['movement_summary']


def fmt(value, signed=False):
    if pd.isna(value):
        return 'Not available'
    return format(float(value), '+.3f' if signed else '.3f')


def gauge_card(metric, value, count):
    """A semantic, neutral semicircle for a rank within the selected cohort."""
    if value is None:
        return (f'<article class="gauge-card"><h3>{escape(metric)}</h3>'
                '<p>Percentile unavailable</p><p class="gauge-note">At least two observations are required.</p></article>')
    angle = pi * (1 - value / 100)
    x, y = 100 + 80 * cos(angle), 104 - 80 * sin(angle)
    progress = f'M 20 104 A 80 80 0 0 1 {x:.2f} {y:.2f}'
    label = f'{metric}: {value:.1f} percentile among {count} participants'
    return (f'<article class="gauge-card"><h3>{escape(metric)}</h3>'
            f'<svg viewBox="0 0 200 142" role="img" aria-label="{escape(label)}">'
            '<path d="M 20 104 A 80 80 0 0 1 180 104" fill="none" stroke="#E5EBF4" stroke-width="12"/>'
            f'<path d="{progress}" fill="none" stroke="{TURQUOISE}" stroke-width="12"/>'
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{INDIGO}"/>'
            f'<text class="gauge-value" x="100" y="88" text-anchor="middle">{value:.1f}</text>'
            '<text class="gauge-sub" x="100" y="103" text-anchor="middle">percentile</text>'
            '<text class="gauge-sub" x="20" y="125" text-anchor="middle">0</text>'
            '<text class="gauge-sub" x="180" y="125" text-anchor="middle">100</text></svg>'
            f'<p class="gauge-note">Within selected KINECAL cohort · n={count}</p></article>')


def change_gauge(change, extent):
    """Neutral diverging semicircle; the endpoints are derived from the paired cohort."""
    if change is None:
        return '<p>Percentage change unavailable because the EO observation is zero.</p>'
    fraction = (change / extent + 1) / 2
    angle = pi * (1 - fraction)
    x, y = 100 + 80 * cos(angle), 104 - 80 * sin(angle)
    return (f'<article class="gauge-card" style="max-width:360px;margin:1rem auto">'
            '<h3>EO → EC percentage change</h3>'
            f'<svg viewBox="0 0 200 142" role="img" aria-label="EO to EC change {change:+.1f} percent">'
            '<path d="M 20 104 A 80 80 0 0 1 180 104" fill="none" stroke="#DEE8F3" stroke-width="12"/>'
            '<path d="M 100 24 L 100 104" stroke="#9BAAC0" stroke-width="1" stroke-dasharray="3 4"/>'
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="{INDIGO}"/>'
            f'<text class="gauge-value" x="100" y="86" text-anchor="middle">{change:+.1f}%</text>'
            '<text class="gauge-sub" x="100" y="103" text-anchor="middle">EC relative to EO</text>'
            f'<text class="gauge-sub" x="22" y="125" text-anchor="middle">−{extent:.0f}%</text>'
            '<text class="gauge-sub" x="100" y="19" text-anchor="middle">0</text>'
            f'<text class="gauge-sub" x="178" y="125" text-anchor="middle">+{extent:.0f}%</text></svg>'
            '<p class="gauge-note">Symmetric scale from available paired observations</p></article>')


def chart(fig, key, height=380):
    fig.update_layout(template='plotly_white', height=height,
        font=dict(family='Arial, sans-serif', size=13, color='#33465E'),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=20, t=25, b=20),
        legend=dict(orientation='h', y=1.15, title_text=''),
        colorway=COLORS)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor='#E3E9F1', zerolinecolor='#B5C3D3')
    st.plotly_chart(fig, width='stretch', key=key,
                    config={'displaylogo': False, 'toImageButtonOptions': {'format': 'png', 'scale': 2}})


def table(frame, key):
    st.dataframe(frame, hide_index=True, width='stretch', key=key)


def download(frame, name, label='Download displayed data (CSV)'):
    st.download_button(label, frame.to_csv(index=False).encode('utf-8-sig'),
                        file_name=name, mime='text/csv', key='download_' + name)


def metric_select(key):
    selected = st.selectbox('Sway metric', METRICS, key=key)
    st.caption(f'{DESCRIPTIONS[selected]} · Original source scale; measurement units are not confirmed.')
    return selected


with st.sidebar:
    mark = (ASSETS / 'brand_mark.svg').read_text(encoding='utf-8')
    st.markdown('<div class="brand-lockup">' + mark +
                '<div><div class="brand-name">KINECAL</div>'
                '<div class="brand-sub">Sway Explorer<br>Movement insights</div></div></div>',
                unsafe_allow_html=True)
    page = st.radio('Explore', PAGES, key='page', label_visibility='collapsed',
                    format_func=lambda value: value)
    motion = (ASSETS / 'sidebar_motion.svg').read_text(encoding='utf-8')
    st.markdown('<div class="sidebar-footer">' + motion +
                '<p class="tagline">Move Well<br>Age Well<br>Live Brighter</p>'
                '<p class="version">KINECAL v1.0.3<br>ActiveAge Lab · Final Capstone</p>'
                f'<p class="detail">{people.part_id.nunique()} participants · {len(obs)} records<br>'
                f'{obs.movement.nunique()} movements · {len(METRICS)} separate metrics<br>'
                'EO = Eyes Open · EC = Eyes Closed<br>'
                'Measurement · Comparison · Decision support</p></div>',
                unsafe_allow_html=True)

st.markdown('<p class="eyebrow">KINECAL / CAMERA-DERIVED POSTURAL SWAY</p>', unsafe_allow_html=True)
st.title(page)
st.markdown(f'<div class="scope">{DISCLAIMER}</div>', unsafe_allow_html=True)


def overview():
    st.write('Explore observed measurements, then compare within a clearly defined movement and cohort.')
    a, b, c, d = st.columns(4)
    a.metric('Participants · full dataset', people.part_id.nunique())
    b.metric('Sway records · full dataset', len(obs))
    c.metric('Movement conditions', obs.movement.nunique())
    d.metric('Paired EO / EC participants', pairs.part_id.nunique())
    with st.expander('Explore cohort · age, sex and retrospective group', expanded=False):
        l, m, r = st.columns(3)
        age = l.slider('Age range', int(people.age.min()), int(people.age.max()),
                        (int(people.age.min()), int(people.age.max())), key='age_range')
        sexes = m.multiselect('Sex recorded in source', ['f', 'm'], ['f', 'm'],
                              format_func=lambda x: {'f':'Female', 'm':'Male'}[x], key='sex_filter')
        groups = r.multiselect('Original cohort group', ['HA', 'NF', 'FHs', 'FHm'],
                               ['HA', 'NF', 'FHs', 'FHm'], key='group_filter')
        st.caption('Original group codes are retained. The supplied binary fall-history mapping is HA/NF → No Fall History; FHs/FHm → Fall History. These are retrospective groups.')
        st.button('Reset cohort filters', on_click=reset_filters)
    filtered = filter_observed(obs, age, sexes, groups)
    st.caption(f'Exploration cohort: {filtered.part_id.nunique()} participants with observations · {len(filtered)} records. These filters apply only to Overview; exported statistical references retain their original cohorts.')
    l, r = st.columns([1, 2])
    with l:
        metric = metric_select('overview_metric')
    movement = r.selectbox('Movement', list(MOVEMENTS), format_func=MOVEMENTS.get, key='overview_movement')
    condition = filtered[filtered.movement == movement]
    if condition.empty:
        st.info('No observations match this movement and cohort. Broaden the filters or select another movement.')
    else:
        a, b, c = st.columns(3)
        a.metric('Participants in selected movement', condition.part_id.nunique())
        b.metric(f'Median {metric}', fmt(condition[metric].median()))
        c.metric('Interquartile range', f'{fmt(condition[metric].quantile(.25))} – {fmt(condition[metric].quantile(.75))}')
        st.subheader('Observed distribution')
        fig = px.histogram(condition, x=metric, nbins=24, color_discrete_sequence=COLORS,
                            labels={metric: f'{metric} · source scale'})
        fig.update_layout(yaxis_title='Participants')
        chart(fig, 'overview_distribution')
        view = st.selectbox('Compare by', ['Age', 'Sex', 'Retrospective group'], key='overview_compare')
        if view == 'Age':
            fig = px.scatter(condition, x='age', y=metric, color='group',
                hover_name='part_id', hover_data=['sex'], color_discrete_sequence=COLORS,
                labels={'age':'Age (years)', 'group':'Original group'})
        else:
            category = 'sex' if view == 'Sex' else 'group'
            fig = px.box(condition, x=category, y=metric, color=category, points='all',
                         hover_data=['part_id','age'], color_discrete_sequence=COLORS)
            st.caption('Displayed group sizes: ' + ' · '.join(f'{g}: n={len(s)}' for g,s in condition.groupby(category)))
        chart(fig, 'overview_demographics')
        download(condition[['part_id', 'movement', 'age', 'sex', 'group', metric]], 'overview_observed.csv')
    st.subheader('Movement coverage')
    st.caption('Unique participants with usable observed records, within the exploration cohort. Missing movements are not zero sway.')
    cov = coverage(filtered)
    fig = px.bar(cov, x='n', y='Movement', orientation='h', text='n', color_discrete_sequence=COLORS)
    fig.update_traces(textposition='outside', cliponaxis=False)
    fig.update_yaxes(autorange='reversed')
    fig.update_xaxes(range=[0, max(cov.n.max()*1.15, 1)], title='Participants (n)')
    chart(fig, 'coverage', 400)
    with st.expander('Coverage table'):
        table(cov, 'coverage_table')


def reset_filters():
    st.session_state.age_range = (int(people.age.min()), int(people.age.max()))
    st.session_state.sex_filter = ['f','m']
    st.session_state.group_filter = ['HA','NF','FHs','FHm']


def participant():
    st.write('Locate a participant’s observed measurement within a selected KINECAL cohort.')
    a, b, c = st.columns(3)
    pid = a.selectbox('Select participant', participant_ids(people), key='participant_id')
    available = obs[obs.part_id == pid]
    movements_available = [m for m in MOVEMENTS if m in set(available.movement)]
    movement = b.selectbox('Select movement', movements_available, format_func=MOVEMENTS.get,
                            key='participant_movement')
    cohort_choice = c.selectbox('Select reference cohort', COHORTS, key='participant_cohort')
    profile = people.set_index('part_id').loc[pid]
    a,b,c,d = st.columns(4)
    a.metric('Age (years)', f'{profile.age:g}')
    b.metric('Sex recorded in source', {'f':'Female','m':'Male'}.get(profile.sex, profile.sex))
    c.metric('Original group', profile['group'])
    d.metric('Clinically at risk · source label', str(int(profile.clinically_at_risk)))
    st.caption(f'Retrospective fall history: {profile.fall_history}. The original group, fall history and clinical label are different fields.')
    selected = available.loc[available.movement.eq(movement)].iloc[0]
    cohort = reference_cohort(obs, movement, profile, cohort_choice)
    st.subheader('Position within the selected cohort')
    st.caption(f'{MOVEMENTS[movement]} · {cohort_choice} · n={cohort.part_id.nunique()} participants. '
               'Percentile uses average tied rank ÷ cohort size × 100 and includes the selected participant. '
               'It describes relative position, not a clinical cutoff.')
    ranks = {m: percentile(cohort, pid, m) for m in METRICS}
    st.markdown('<div class="gauge-grid">' + ''.join(
        gauge_card(m, ranks[m], cohort[m].notna().sum()) for m in METRICS) + '</div>',
        unsafe_allow_html=True)
    metric = metric_select('participant_metric')
    st.subheader('Distribution behind the percentile')
    fig = px.histogram(cohort, x=metric, nbins=24, color_discrete_sequence=['#A8B8D9'])
    fig.add_vline(x=selected[metric], line_color=INDIGO, line_width=3,
                  annotation_text=f'{pid}: {fmt(selected[metric])}')
    fig.update_layout(yaxis_title='Participants', xaxis_title=f'{metric} · source scale')
    condition = next((c for c, m in CONDITIONS.items() if m == movement), None)
    row = expected[(expected.part_id == pid) & (expected.condition == condition) &
                   (expected.outcome == metric)]
    if not row.empty:
        fig.add_vline(x=row.iloc[0].expected_sway, line_color=SKY, line_dash='dash',
                      annotation_text='Statistical reference')
    chart(fig, 'participant_distribution', 330)
    st.subheader('Observed vs expected · supplied statistical reference')
    if row.empty:
        st.info('A model reference is available only for quiet standing EO and EC in the supplied exports. '
                'The observed values and cohort percentiles above remain available for this movement.')
    else:
        row = row.iloc[0]
        model = models[(models.condition == condition) & (models.outcome == metric)].iloc[0]
        st.caption(f'{condition} · {model.reference_type} · {model.selected_model}. '
                   'This model reference uses the original full condition cohort; the selected descriptive cohort does not refit it.')
        a,b,c = st.columns(3)
        a.metric(f'Observed {metric}', fmt(row.observed_sway))
        b.metric('Expected / reference', fmt(row.expected_sway))
        c.metric('Observed − expected', fmt(row.observed_minus_expected, signed=True))
        interval = pd.notna(row.prediction_interval_95_low) and pd.notna(row.prediction_interval_95_high)
        fig = go.Figure()
        if interval:
            fig.add_trace(go.Scatter(x=[row.prediction_interval_95_low, row.prediction_interval_95_high],
                y=['Reference']*2, mode='lines', line=dict(color='#B8C6D9', width=14), name='95% prediction interval'))
        fig.add_trace(go.Scatter(x=[row.expected_sway], y=['Reference'], mode='markers',
            marker=dict(color=SKY, size=15, symbol='diamond'), name='Expected / reference'))
        fig.add_trace(go.Scatter(x=[row.observed_sway], y=['Observed'], mode='markers',
            marker=dict(color=INDIGO, size=16), name=f'{pid} observed'))
        fig.update_xaxes(title=f'{metric} · source scale')
        chart(fig, 'participant_reference', 250)
        st.caption('95% prediction interval: ' +
                   (f'{fmt(row.prediction_interval_95_low)} to {fmt(row.prediction_interval_95_high)}. '
                    if interval else 'Not available. ') +
                   'Expected values are supplied full-fit references, not out-of-fold predictions. '
                   'Negative interval endpoints are retained from the export; they are not physiological bounds.')
        st.info(model.dashboard_use_note_th)
    details = pd.DataFrame([{
        'Metric': m, 'Observed': selected[m],
        'Expected / reference': (expected.loc[(expected.part_id.eq(pid)) &
            (expected.condition.eq(condition)) & (expected.outcome.eq(m)), 'expected_sway'].iloc[0]
            if condition is not None else None),
        'Percentile · selected cohort': ranks[m],
    } for m in METRICS])
    st.subheader('Metric details')
    table(details, 'participant_details')
    with st.expander('Exact supplied source rows for this participant and condition'):
        source = expected[(expected.part_id == pid) & (expected.condition == condition)]
        if not source.empty:
            table(source, 'participant_source')
            download(source, f'{pid}_{condition}_statistical_reference.csv')
        else:
            st.caption('No model reference is supplied for this movement.')


def paired():
    st.write('Compare the same people under both quiet-standing conditions. Each connecting line represents one participant.')
    metric = metric_select('paired_metric')
    cohort = pairs[pairs.outcome == metric].copy()
    pid = st.selectbox('Paired participant', participant_ids(cohort), key='paired_id')
    row = cohort.set_index('part_id').loc[pid]
    a,b,c,d = st.columns(4)
    a.metric('Participants with both conditions', cohort.part_id.nunique())
    b.metric(f'{pid} · EO observed', fmt(row.EO_observed))
    c.metric(f'{pid} · EC observed', fmt(row.EC_observed))
    d.metric(f'{pid} · EC − EO', fmt(row.EC_minus_EO, signed=True))
    eo_n = obs.loc[obs.movement.eq(CONDITIONS['EO']), 'part_id'].nunique()
    ec_n = obs.loc[obs.movement.eq(CONDITIONS['EC']), 'part_id'].nunique()
    st.caption(f'Complete pairs only · Full EO cohort: {eo_n} · Full EC cohort: {ec_n} · '
               f'Paired cohort: {cohort.part_id.nunique()}. Missing conditions are never filled.')
    changes = cohort.apply(lambda p: paired_percent_change(p.EO_observed, p.EC_observed), axis=1).dropna()
    change = paired_percent_change(row.EO_observed, row.EC_observed)
    if len(changes):
        extent = max(1, float(changes.abs().max()))
        st.markdown(change_gauge(change, extent), unsafe_allow_html=True)
    if change is not None:
        direction = 'increased' if change > 0 else 'decreased' if change < 0 else 'did not change'
        st.caption(f'{metric} {direction} by {abs(change):.1f}% from EO to EC for {pid}. '
                   'Percentage change = (EC − EO) ÷ EO × 100; the direction is descriptive only.')
    else:
        st.caption('Percentage change is undefined when EO is zero. The absolute difference remains available above.')
    st.subheader('Paired observed measurements')
    fig = go.Figure()
    # A single neutral background trace keeps all pairs visible without a large legend.
    xs, ys = [], []
    for p in cohort.itertuples():
        xs.extend(['EO', 'EC', None]); ys.extend([p.EO_observed, p.EC_observed, None])
    fig.add_trace(go.Scatter(x=xs, y=ys, mode='lines', line=dict(color='#C6D2E0', width=1),
                            name='Paired cohort', hoverinfo='skip'))
    for condition in ['EO', 'EC']:
        fig.add_trace(go.Scatter(x=[condition]*len(cohort), y=cohort[f'{condition}_observed'],
            customdata=cohort[['part_id']], mode='markers', showlegend=False,
            marker=dict(color='#94ABBE', size=5),
            hovertemplate='%{customdata[0]} · '+condition+': %{y:.4f}<extra></extra>'))
    fig.add_trace(go.Scatter(x=['EO','EC'], y=[row.EO_observed,row.EC_observed],
        mode='lines+markers', line=dict(color=COLORS[0],width=3), marker=dict(size=12), name=pid))
    fig.update_yaxes(title=f'{metric} · source scale')
    chart(fig, 'paired_lines', 410)
    st.subheader('Distribution of EC − EO')
    fig = px.histogram(cohort, x='EC_minus_EO', nbins=25, color_discrete_sequence=COLORS,
                        labels={'EC_minus_EO':f'{metric}: EC − EO · source scale'})
    fig.add_vline(x=0, line_dash='dash', line_color='#64748B')
    fig.add_vline(x=row.EC_minus_EO, line_color=COLORS[1], annotation_text=pid)
    fig.update_layout(yaxis_title='Paired participants')
    chart(fig, 'paired_difference', 310)
    st.caption('Positive = the EC value is larger; negative = the EO value is larger. The sign does not establish disease or fall risk.')
    with st.expander('Paired values'):
        table(cohort, 'paired_source')
    download(cohort, f'paired_{metric}.csv')


def movements():
    st.write('Compare each metric separately across movements. Coverage differs; these are not matched-cohort comparisons.')
    metric = metric_select('movement_metric')
    chosen = st.multiselect('Movements to compare', list(MOVEMENTS), default=list(MOVEMENTS),
                            format_func=MOVEMENTS.get, key='movement_selection')
    if not chosen:
        st.info('Select at least one movement to compare.')
        return
    records = obs[obs.movement.isin(chosen)].copy()
    counts = records.groupby('movement').part_id.nunique()
    labels = {m:f'{MOVEMENTS[m]} · n={counts[m]}' for m in chosen}
    records['Movement · sample size'] = records.movement.map(labels)
    fig = px.box(records, x=metric, y='Movement · sample size', orientation='h', points='all',
        hover_data=['part_id','age','sex','group'], color_discrete_sequence=COLORS,
        category_orders={'Movement · sample size':[labels[m] for m in chosen]})
    fig.update_layout(xaxis_title=f'{metric} · source scale', yaxis_title='')
    chart(fig, 'movement_box', max(340, len(chosen)*58))
    st.caption('All observations, including extreme values, are retained. Different movements may include different participants. No composite sway score is calculated.')
    st.subheader('Supplied movement summary')
    selected = summary[(summary.outcome == metric) & summary.movement.isin(chosen)].copy()
    selected['movement'] = pd.Categorical(selected.movement, categories=chosen, ordered=True)
    selected = selected.sort_values('movement')
    display = selected.copy()
    display['movement'] = display.movement.map(MOVEMENTS)
    table(display.rename(columns={'movement':'Movement', 'outcome':'Metric', 'n':'n (participants)'}), 'movement_summary')
    download(selected, f'movement_summary_{metric}.csv')


def evidence():
    st.write('Model selections and evaluation values below come directly from the supplied exports.')
    a,b,c = st.columns(3)
    a.metric('Personalized references', '3 of 8')
    b.metric('Cohort baseline references', '5 of 8')
    c.metric('Model conditions', 'EO / EC')
    st.subheader('Selected statistical references')
    display = models[['condition','outcome','reference_type','selected_model']].copy()
    display['n'] = display.condition.map(expected.groupby('condition').part_id.nunique())
    table(display, 'reference_selection')
    st.caption('EO: RDIST, MVELO and AREA_CE use personalized regression. EO MFREQ and all four EC metrics use the cohort baseline. No references are extended to foam, tandem or unilateral movements.')
    st.subheader('Out-of-fold evidence')
    table(models[['condition','outcome','OOF_MAE','OOF_RMSE','OOF_R2',
                  'baseline_MAE','MAE_improvement_pct']], 'model_evaluation')
    st.markdown('**OOF** = out-of-fold evaluation. **MAE / RMSE** describe prediction error on the original metric scale; lower is better. **R²** can be negative. **MAE improvement (%)** is relative to the exported baseline error. Compare models within the same metric and condition.')
    st.info('Personalization provides limited improvement in these exports. EO MVELO reduces MAE by approximately 1.42% while its OOF R² is negative (−0.031). Retain these references as supporting context.')
    with st.expander('Original model notes (Thai)'):
        table(models[['condition','outcome','dashboard_use_note_th']], 'original_notes')
    st.subheader('Interpretation and limitations')
    st.markdown('''
- Expected sway is a **statistical reference**, not a clinical cutoff.
- Higher sway does not automatically mean higher fall risk.
- Fall history is retrospective information, not a future outcome.
- RDIST, MVELO, MFREQ and AREA_CE remain separate measurements.
- Sample sizes differ across movements; movement comparisons are descriptive and use available observations.
- Exported percentiles use the full condition-specific cohort, including the selected participant, with average ranks for ties.
- Exported expected values and prediction intervals are full-fit results; they are separate from out-of-fold performance estimates.
- Prediction intervals retain the supplied endpoints, including negative values. They are not physiological bounds.
- Spatial units and measurement validity are not fully confirmed in the supplied handoff. Values remain on their original source scales.
''')
    st.subheader('Data provenance')
    sizes = pd.DataFrame([{'File': k+'.csv', 'Rows':len(v)} for k,v in data.items()])
    table(sizes, 'data_provenance')
    st.caption('CSV keys, registry membership, observed values, model labels, percentiles, paired differences, interval ordering and movement summaries are checked when the app loads. Models are not retrained by this dashboard.')
    download(models, 'model_evidence.csv')


{'Overview': overview, 'Participant Comparison': participant,
 'Eyes Open vs Eyes Closed': paired, 'Movement Comparison': movements,
 'Model Evidence / Limitations': evidence}[page]()

st.divider()
st.caption('ActiveAge Lab · KINECAL · Statistical comparison, with observed data at the center.')
