"""Read and check existing results. No model fitting or prediction is performed."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
METRICS = ['RDIST', 'MVELO', 'MFREQ', 'AREA_CE']
MOVEMENTS = {
    'Quiet-Standing-Eyes-Open': 'Quiet standing · EO',
    'Quiet-Standing-Eyes-Closed': 'Quiet standing · EC',
    'Foam-Quiet-Standing-Eyes-Open': 'Foam · EO',
    'Foam-Quiet-Standing-Eyes-Closed': 'Foam · EC',
    'Semi-Tandem-Balance': 'Semi-tandem',
    'Tandem-Balance': 'Tandem',
    'Unilateral-Stance-Eyes-Open': 'Unilateral · EO',
    'Unilateral-Stance-Eyes-Closed': 'Unilateral · EC',
}
CONDITIONS = {'EO': 'Quiet-Standing-Eyes-Open', 'EC': 'Quiet-Standing-Eyes-Closed'}
FILES = ['sway_clean_long', 'participants', 'model_summary',
         'participant_expected_sway', 'eo_ec_paired', 'movement_summary']


class DataError(ValueError):
    """A source file is missing, malformed, or conflicts with another export."""


def require(ok, message):
    if not ok:
        raise DataError(message)


def match_numeric(left, right, description):
    require(np.allclose(np.asarray(left, dtype=float), np.asarray(right, dtype=float),
                        rtol=1e-7, atol=1e-9, equal_nan=True),
            f'Conflicting source values: {description}.')


def load_data(directory=None):
    directory = Path(directory) if directory is not None else ROOT / 'data'
    tables = {}
    for name in FILES:
        try:
            tables[name] = pd.read_csv(directory / f'{name}.csv', encoding='utf-8-sig')
        except (OSError, ValueError) as exc:
            raise DataError(f'Cannot read {name}.csv: {exc}') from exc
    validate(tables)
    return tables


def validate(t):
    contracts = {
        'sway_clean_long': (['part_id', 'movement', 'age', 'sex', 'group'] + METRICS,
                            ['part_id', 'movement']),
        'participants': (['part_id', 'age', 'sex', 'group', 'fall_history'], ['part_id']),
        'model_summary': (['condition', 'outcome', 'selected_model', 'reference_type',
                           'OOF_MAE', 'OOF_RMSE', 'OOF_R2', 'baseline_MAE',
                           'MAE_improvement_pct', 'dashboard_use_note_th'], ['condition', 'outcome']),
        'participant_expected_sway': (['part_id', 'condition', 'movement', 'outcome',
            'observed_sway', 'observed_percentile_within_condition', 'selected_model',
            'reference_type', 'expected_sway', 'observed_minus_expected',
            'prediction_interval_95_low', 'prediction_interval_95_high'],
            ['part_id', 'condition', 'outcome']),
        'eo_ec_paired': (['part_id', 'outcome', 'EO_observed', 'EC_observed', 'EC_minus_EO'],
                          ['part_id', 'outcome']),
        'movement_summary': (['movement', 'outcome', 'n', 'mean', 'median', 'q25', 'q75', 'min', 'max'],
                              ['movement', 'outcome']),
    }
    for name, (columns, keys) in contracts.items():
        require(set(columns) <= set(t[name]), f'{name}.csv is missing required columns: {set(columns)-set(t[name])}')
        require(not t[name][keys].isna().any().any(), f'Missing keys in {name}.csv.')
        require(not t[name].duplicated(keys).any(), f'Duplicate keys in {name}.csv.')
    obs, people, models, expected, pairs, summary = (t[k] for k in FILES)
    require(len(people) == 90 and len(obs) == 517, 'This release requires 90 participants and 517 observed records.')
    require(set(obs.part_id) <= set(people.part_id), 'Observed participant IDs are missing from participants.csv.')
    require(set(obs.movement) == set(MOVEMENTS), 'Unexpected movement names.')
    require(np.isfinite(obs[METRICS].to_numpy(dtype=float)).all(), 'Missing or non-finite observed metrics.')
    profile = obs.merge(people, on='part_id', suffixes=('', '_registry'), validate='many_to_one')
    for field in ['age', 'sex', 'group']:
        require(profile[field].eq(profile[field + '_registry']).all(), f'Participant {field} differs between sources.')
    combinations = {(c, m) for c in CONDITIONS for m in METRICS}
    require(set(zip(models.condition, models.outcome)) == combinations, 'The model summary must cover all eight condition–metric combinations.')
    personalized = {('EO', 'RDIST'), ('EO', 'MVELO'), ('EO', 'AREA_CE')}
    for row in models.itertuples():
        reference = 'Personalized regression' if (row.condition, row.outcome) in personalized else 'Cohort baseline'
        require(row.reference_type == reference, 'Model reference selection differs from the primary specification.')
        require((row.selected_model == 'Baseline') == (reference == 'Cohort baseline'), 'Selected model conflicts with reference type.')
    long = obs.melt(id_vars=['part_id', 'movement'], value_vars=METRICS,
                    var_name='outcome', value_name='source_observed')
    quiet = long[long.movement.isin(CONDITIONS.values())].copy()
    quiet['condition'] = quiet.movement.map({v: k for k, v in CONDITIONS.items()})
    require(len(expected) == len(quiet), 'Expected-sway export does not cover all quiet-standing observations.')
    checked = expected.merge(quiet, on=['part_id', 'movement', 'condition', 'outcome'],
                              how='left', validate='one_to_one')
    require(checked.source_observed.notna().all(), 'Expected-sway rows have unknown source keys.')
    match_numeric(checked.observed_sway, checked.source_observed, 'observed sway')
    checked = expected.merge(models, on=['condition', 'outcome'], suffixes=('', '_summary'), validate='many_to_one')
    for field in ['selected_model', 'reference_type']:
        require(checked[field].eq(checked[field + '_summary']).all(), f'{field} differs from model_summary.csv.')
    match_numeric(expected.observed_minus_expected, expected.observed_sway - expected.expected_sway, 'observed minus expected')
    ranks = expected.groupby(['condition', 'outcome']).observed_sway.rank(method='average', pct=True) * 100
    match_numeric(expected.observed_percentile_within_condition, ranks, 'condition percentiles')
    lo, hi = expected.prediction_interval_95_low, expected.prediction_interval_95_high
    require(lo.isna().eq(hi.isna()).all(), 'Prediction interval has only one endpoint.')
    require((lo.isna() | ((lo <= expected.expected_sway) & (hi >= expected.expected_sway))).all(), 'Invalid prediction interval endpoints.')
    wide = quiet.pivot(index=['part_id', 'outcome'], columns='condition', values='source_observed').dropna().reset_index()
    require(len(wide) == len(pairs), 'Paired export does not cover the complete EO/EC cohort.')
    paired_check = pairs.merge(wide, on=['part_id', 'outcome'], how='left', validate='one_to_one')
    require(paired_check[['EO', 'EC']].notna().all().all(), 'Paired export includes an incomplete participant.')
    match_numeric(paired_check.EO_observed, paired_check.EO, 'paired EO')
    match_numeric(paired_check.EC_observed, paired_check.EC, 'paired EC')
    match_numeric(pairs.EC_minus_EO, pairs.EC_observed-pairs.EO_observed, 'EC minus EO')
    computed = long.groupby(['movement', 'outcome']).source_observed.agg(
        n='count', mean='mean', median='median', q25=lambda x: x.quantile(.25),
        q75=lambda x: x.quantile(.75), min='min', max='max').reset_index()
    require(len(summary) == len(computed), 'Incomplete movement summary.')
    joined = summary.merge(computed, on=['movement', 'outcome'], how='left', suffixes=('', '_check'), validate='one_to_one')
    for field in ['n', 'mean', 'median', 'q25', 'q75', 'min', 'max']:
        match_numeric(joined[field], joined[field + '_check'], f'movement summary {field}')


def participant_ids(frame):
    return sorted(frame.part_id.unique(), key=lambda v: int(v.removeprefix('SPPB')))


def filter_observed(obs, age_range, sexes, groups):
    return obs[obs.age.between(*age_range) & obs.sex.isin(sexes) & obs.group.isin(groups)].copy()


def coverage(obs):
    counts = obs.groupby('movement').part_id.nunique().reindex(MOVEMENTS, fill_value=0)
    return pd.DataFrame({'Movement': [MOVEMENTS[x] for x in counts.index],
                         'n': counts.values})
