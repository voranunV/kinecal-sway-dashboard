"""ActiveAge Lab • camera-derived postural sway, using supplied CSV exports only."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from data_access import (load_data, DataError, METRICS, MOVEMENTS, CONDITIONS,
                         participant_ids, filter_observed, coverage)

st.set_page_config(page_title='ActiveAge Lab | Sway Explorer', page_icon='◌', layout='wide')
COLORS = ['#276D8A', '#8372B2', '#C89C58', '#64748B']
DISCLAIMER = ('This dashboard provides measurement and statistical comparison of camera-derived '
              'postural sway. It is not a diagnostic tool and does not predict future falls.')
DESCRIPTIONS = {'RDIST': 'Root-mean-square sway distance', 'MVELO': 'Mean sway velocity',
                'MFREQ': 'Mean sway-frequency measure', 'AREA_CE': 'Confidence-ellipse area'}
PAGES = ['Overview', 'Participant Comparison', 'Eyes Open vs Eyes Closed',
         'Movement Comparison', 'Model Evidence / Limitations']

st.markdown('''<style>
.block-container {max-width: 1440px; padding-top: 4.5rem; padding-bottom: 2rem;}
h1 {letter-spacing: -.045em; font-weight: 750 !important;
 height: auto; line-height: 1.3; overflow: visible;}
h2, h3 {letter-spacing: -.025em;}
[data-testid="stMetric"] {background: #FFFFFF; border: 1px solid #DCE4EE;
 border-radius: 12px; padding: 16px 19px;}
[data-testid="stMetricValue"] {font-variant-numeric: tabular-nums;}
[data-testid="stMetricValue"] > div {white-space: normal; overflow-wrap: anywhere;
 font-size: 1.8rem; line-height: 1.25;}
[data-testid="stMetricLabel"] p {white-space: normal;}
[data-testid="stSidebar"] {border-right: 1px solid #DCE4EE;}
.eyebrow {font-size: .76rem; letter-spacing: .17em; font-weight: 700; color: #276D8A;
 height: auto; line-height: 1.6; padding-block: .15rem; overflow: visible;}
.scope {border-left: 3px solid #7B91AF; padding: .7rem 1rem; background:#EDF2F7;
 color: #42536B; font-size:.87rem; border-radius: 0 8px 8px 0; margin-bottom:1.4rem;}
</style>''', unsafe_allow_html=True)


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
    st.markdown('<p class="eyebrow">ActiveAge Lab</p>', unsafe_allow_html=True)
    st.title('Sway Explorer')
    st.caption('KINECAL · Final Capstone')
    page = st.radio('Explore', PAGES, key='page')
    st.divider()
    st.markdown('**Measurement. Comparison.**\n\n**Decision support.**')
    st.caption('90 participants · 517 records\n\n8 movements · 4 separate metrics')
    st.caption('EO = Eyes Open · EC = Eyes Closed')

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
    st.write('Observed sway first. Supplied statistical references add context for quiet standing.')
    a, b, c = st.columns([1, 1, 2])
    pid = a.selectbox('Participant', participant_ids(people), key='participant_id')
    condition = b.selectbox('Quiet-standing condition', ['EO', 'EC'], key='participant_condition')
    with c:
        metric = metric_select('participant_metric')
    profile = people.set_index('part_id').loc[pid]
    a,b,c,d = st.columns(4)
    a.metric('Age (years)', f'{profile.age:g}')
    b.metric('Sex recorded in source', {'f':'Female','m':'Male'}.get(profile.sex, profile.sex))
    c.metric('Original group', profile['group'])
    d.metric('Retrospective fall history', profile.fall_history)
    available = obs[obs.part_id == pid]
    st.caption('Available movements: ' + ' · '.join(MOVEMENTS[m] for m in MOVEMENTS if m in set(available.movement)))
    row = expected[(expected.part_id == pid) & (expected.condition == condition) & (expected.outcome == metric)]
    if row.empty:
        st.info(f'No {condition} observation or statistical reference is available for {pid}. Select another condition or participant. Missing observations are not imputed.')
        return
    row = row.iloc[0]
    model = models[(models.condition == condition) & (models.outcome == metric)].iloc[0]
    cohort = obs[obs.movement == CONDITIONS[condition]]
    a,b,c = st.columns(3)
    a.metric(f'Observed {metric}', fmt(row.observed_sway))
    b.metric('Percentile within condition', f'{row.observed_percentile_within_condition:.1f}%')
    c.metric('Reference cohort', f'n = {len(cohort)}')
    st.caption('Percentile = average tied rank ÷ number of participants × 100, within the full condition–metric cohort. It is not a clinical cutoff.')
    st.subheader('Statistical reference')
    st.markdown(f'**{model.reference_type}** · {model.selected_model}')
    a,b,c = st.columns(3)
    a.metric('Expected / reference sway', fmt(row.expected_sway))
    b.metric('Observed − expected', fmt(row.observed_minus_expected, signed=True))
    interval = pd.notna(row.prediction_interval_95_low) and pd.notna(row.prediction_interval_95_high)
    c.metric('95% prediction interval',
        f'{fmt(row.prediction_interval_95_low)} to {fmt(row.prediction_interval_95_high)}' if interval else 'Not available')
    fig = go.Figure()
    if interval:
        fig.add_trace(go.Scatter(x=[row.prediction_interval_95_low, row.prediction_interval_95_high],
            y=['Statistical reference']*2, mode='lines', line=dict(color='#B8C6D9', width=12), name='95% prediction interval'))
    fig.add_trace(go.Scatter(x=[row.expected_sway], y=['Statistical reference'], mode='markers',
        marker=dict(color=COLORS[1], size=15, symbol='diamond'), name='Expected / reference'))
    fig.add_trace(go.Scatter(x=[row.observed_sway], y=['Observed'], mode='markers',
        marker=dict(color=COLORS[0], size=16), name=f'{pid} observed'))
    fig.update_xaxes(title=f'{metric} · source scale')
    chart(fig, 'participant_reference', 240)
    st.caption('Expected values are supplied full-fit references for existing participants. Out-of-fold evaluation is reported separately on Model Evidence. Prediction intervals are not confidence intervals or clinical thresholds; any negative endpoints are preserved from the export.')
    st.subheader('Participant within the observed cohort')
    fig = px.histogram(cohort, x=metric, nbins=24, color_discrete_sequence=['#9EB8CB'])
    fig.add_vline(x=row.observed_sway, line_color=COLORS[0], line_width=3,
                  annotation_text=f'{pid}: {fmt(row.observed_sway)}')
    fig.update_layout(yaxis_title='Participants', xaxis_title=f'{metric} · source scale')
    chart(fig, 'participant_distribution', 300)
    st.info(model.dashboard_use_note_th)
    with st.expander('Exact source values for this participant and condition'):
        details = expected[(expected.part_id == pid) & (expected.condition == condition)]
        table(details, 'participant_source')
        download(details, f'{pid}_{condition}_statistical_reference.csv')


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
    st.caption('Complete pairs only · Full EO cohort: 85 · Full EC cohort: 87 · Paired cohort: 83. No missing condition is filled or matched across different people.')
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
