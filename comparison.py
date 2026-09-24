"""Descriptive comparisons of existing observations; no model fitting."""
import pandas as pd


COHORTS = ('All observed in movement', 'Same age group', 'Same sex',
           'Same age group + sex', 'Same original KINECAL group')


def age_group(age):
    """Descriptive bands from the completed modeling notebook: <60, 60–64, 65+."""
    if age < 60:
        return '<60'
    if age < 65:
        return '60–64'
    return '65+'


def reference_cohort(observed, movement, profile, choice):
    cohort = observed.loc[observed.movement.eq(movement)].copy()
    if choice in ('Same age group', 'Same age group + sex'):
        cohort = cohort.loc[cohort.age.map(age_group).eq(age_group(profile.age))]
    if choice in ('Same sex', 'Same age group + sex'):
        cohort = cohort.loc[cohort.sex.eq(profile.sex)]
    if choice == 'Same original KINECAL group':
        cohort = cohort.loc[cohort.group.eq(profile['group'])]
    return cohort


def percentile(cohort, participant_id, metric):
    """Average tied rank / cohort size, including the participant (export convention)."""
    values = cohort[['part_id', metric]].dropna()
    if len(values) < 2 or participant_id not in set(values.part_id):
        return None
    ranks = values[metric].rank(method='average', pct=True) * 100
    return float(ranks.loc[values.part_id.eq(participant_id)].iloc[0])


def paired_percent_change(eo, ec):
    """(EC - EO) / EO * 100; undefined when EO is zero."""
    if pd.isna(eo) or pd.isna(ec) or eo == 0:
        return None
    return (ec - eo) / eo * 100
