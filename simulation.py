"""
Tessera B2B SaaS — Data Simulation
Generates CSV files (Jan 2025 - Sep 2026) and saves them to ./output/
"""

import uuid
import random
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

warnings.filterwarnings('ignore')

from config import (
    SIM_START, SIM_END,
    TOTAL_ACCOUNTS, TARGET_USERS,
    PLAN_MASTER, PLAN_CURRENT,
    DIM_CSM_MASTER, CSM_BY_SEGMENT,
    CHANNELS, CHANNEL_WEIGHTS, CAMPAIGN_CHANNELS, CAMPAIGN_CHANNEL_WEIGHTS, CHANNEL_UTM,
    MOTION_TYPES,
    GEOS, GEO_WEIGHTS,
    INDUSTRIES, INDUSTRY_WEIGHTS,
    ICP_SEGMENTS, ICP_WEIGHTS,
    ICP_EMPLOYEE_RANGE, ICP_REVENUE_RANGE,
    SEGMENT_PLAN_DISTRIBUTION, LIFECYCLE_STATE_WEIGHTS,
    USERS_PER_ACCOUNT,
    ACCOUNT_SIZE_BAND_EDGES, ACCOUNT_SIZE_BANDS,
    DEAL_SIZE_BAND_EDGES, DEAL_SIZE_BANDS,
    UTILISATION_BAND_EDGES, UTILISATION_BANDS,
    USAGE_EVENT_TYPES, EVENT_NAMES, EVENT_WEIGHTS,
    ONBOARDING_STEPS_SELF_SERVE, ONBOARDING_STEPS_SALES_LED,
    EVENTS_PER_MONTH, USER_LIFECYCLE_TO_EVENT_BUCKET,
    QUALIFY_RATE,
    TICKET_CATEGORIES, TICKET_PRIORITIES, TICKET_PRIORITY_WEIGHTS,
    TICKET_CHANNELS, TICKET_CHANNEL_WEIGHTS, RESOLUTION_HOURS_BY_PRIORITY,
    QBR_ELIGIBLE_TIERS,
    EXPANSION_TYPES, EXPANSION_STAGES, EXPANSION_MOTION_TYPES, EXPANSION_MOTION_WEIGHTS,
    BILLING_CYCLES, BILLING_CYCLE_WEIGHTS, DISCOUNT_BY_SEGMENT,
    ADDON_CATALOG,
    ELASTICITY_BY_SEGMENT, WTP_MEAN_MULTIPLIER_BY_SEGMENT, WTP_NOISE_STD,
    COST_LINES, FUNCTIONS, VENDOR_MASTER,
    HEADCOUNT_START, HEADCOUNT_MONTHLY_GROWTH, AVG_MONTHLY_SALARY_USD_BY_FUNCTION,
    CLOUD_COST_PER_ACCOUNT_USD, CLOUD_COST_BASE_FIXED_USD,
    AI_INFERENCE_COST_PER_ACCOUNT_USD_START, AI_INFERENCE_MONTHLY_RAMP,
    OTHER_COST_BASE_FIXED_USD, OTHER_COST_PCT_OF_MRR,
    SERVICES_REVENUE_PCT_OF_MRR, OPENING_CASH_USD,
    LANDING_PAGES, DEVICE_TYPES, DEVICE_WEIGHTS,
    ACCOUNT_MONTHLY_WEIGHTS, AM_OWNERS,
    USER_ROLES, USER_DEPARTMENTS,
    FIRST_NAMES, LAST_NAMES, COMPANY_ADJECTIVES, COMPANY_NOUNS,
)

random.seed(42)
np.random.seed(42)

BASE_PATH   = Path(__file__).parent
OUTPUT_PATH = BASE_PATH / "output"
OUTPUT_PATH.mkdir(exist_ok=True)

MONTH_RANGE = pd.date_range('2025-01-01', '2026-09-01', freq='MS')   # 21 months

SEAT_RANGES_BY_SEGMENT = {'SMB': (2, 10), 'Mid-market': (5, 50), 'Enterprise': (20, 260)}

# Elasticity is wired into tier-selection demand around each real price change,
# so ELASTICITY_BY_SEGMENT actually drives generated volume, not just sits in
# config unused. Demand dips for a few months after a price increase, sized
# by the average segment elasticity — a simplification (elasticity is
# segment-specific in reality; tier selection isn't segment-scoped here).
_PRICE_CHANGE_MONTH = {'Plus': pd.Timestamp('2025-07-01'), 'Business': pd.Timestamp('2025-10-01')}
_PRICE_CHANGE_PCT   = {'Plus': (15.0 - 12.0) / 12.0, 'Business': (40.0 - 35.0) / 35.0}
_AVG_ELASTICITY = sum(ELASTICITY_BY_SEGMENT.values()) / len(ELASTICITY_BY_SEGMENT)


# ─────────────────────────── Helpers ────────────────────────────────────────

def uid():
    return str(uuid.uuid4())

def time_period(dt):
    if pd.isna(dt) or dt is None:
        return None
    return pd.to_datetime(dt).strftime('%Y-%m')

def rand_dt(start: datetime, end: datetime) -> datetime:
    """Random datetime between start and end (inclusive)."""
    delta = int((end - start).total_seconds())
    if delta <= 0:
        return start
    return start + timedelta(seconds=random.randint(0, delta))

def rand_business_dt(start: datetime, end: datetime) -> datetime:
    """Random datetime, biased toward business hours (08:00-20:00)."""
    dt = rand_dt(start, end)
    return dt.replace(hour=random.randint(8, 20), minute=random.randint(0, 59), second=random.randint(0, 59))

def month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

def month_end(dt: datetime) -> datetime:
    next_m = (dt.replace(day=28) + timedelta(days=4)).replace(day=1)
    return (next_m - timedelta(seconds=1))

def fmt(dt) -> str:
    if dt is None:
        return None
    ts = pd.to_datetime(dt, errors='coerce')
    if pd.isna(ts):
        return None
    return ts.strftime('%Y-%m-%d %H:%M:%S')


def parse_dt(val):
    """Return Python datetime from any scalar (string, None, NaN, NaT)."""
    if val is None:
        return None
    ts = pd.to_datetime(val, errors='coerce')
    return None if pd.isna(ts) else ts.to_pydatetime()


def weighted_choice(options, weights):
    return random.choices(options, weights=weights, k=1)[0]


def band_from_edges(value, edges, labels):
    """Which band `value` falls into, given ascending edges and one more label than edges."""
    for i, e in enumerate(edges):
        if value < e:
            return labels[i]
    return labels[-1]


def plan_id_for_tier_at(tier, at_date):
    """The plan version actually effective on `at_date` for `tier` (SCD-2 aware),
    so contracts reflect the real price in force at signup, not always the latest."""
    candidates = [p for p in PLAN_MASTER if p['tier'] == tier]
    at_ts = pd.to_datetime(at_date)
    for p in candidates:
        eff_from = pd.to_datetime(p['effective_from'])
        eff_to = pd.to_datetime(p['effective_to']) if p['effective_to'] else pd.Timestamp(SIM_END)
        if eff_from <= at_ts <= eff_to:
            return p['plan_id']
    return PLAN_CURRENT.get(tier)


def tier_demand_multiplier(tier, month_dt):
    """Demand dip for ~3 months after a real price increase, sized by elasticity."""
    if tier not in _PRICE_CHANGE_MONTH:
        return 1.0
    change_month = _PRICE_CHANGE_MONTH[tier]
    months_since = (month_dt.year - change_month.year) * 12 + (month_dt.month - change_month.month)
    if 0 <= months_since < 3:
        demand_change_pct = _AVG_ELASTICITY * _PRICE_CHANGE_PCT[tier]
        return max(0.5, 1 + demand_change_pct)
    return 1.0


# ─────────────────────────── 1. DimCSM ──────────────────────────────────────

def generate_dim_csm():
    """Monthly snapshot: one row per CSM per active month."""
    rows = []
    for csm in DIM_CSM_MASTER:
        active_from = pd.to_datetime(csm['active_from']).replace(day=1)
        active_to   = pd.to_datetime(csm['active_to']).replace(day=1) if csm['active_to'] else None

        for month_dt in MONTH_RANGE:
            if month_dt < active_from:
                continue
            if active_to is not None and month_dt > active_to:
                continue
            row = dict(csm)
            row['time_period'] = month_dt.strftime('%Y-%m')
            rows.append(row)

    return pd.DataFrame(rows)


# ─────────────────────────── 2. Plan ────────────────────────────────────────

def generate_plan():
    """Monthly snapshot: one row per plan version per month it was active."""
    rows = []
    sim_end_month = pd.Timestamp('2026-09-01')

    for p in PLAN_MASTER:
        eff_from = pd.to_datetime(p['effective_from']).replace(day=1)
        eff_to   = pd.to_datetime(p['effective_to']).replace(day=1) if p['effective_to'] else sim_end_month

        start = max(eff_from, MONTH_RANGE[0])
        end   = min(eff_to,   sim_end_month)

        for month_dt in pd.date_range(start, end, freq='MS'):
            row = dict(p)
            row['time_period'] = month_dt.strftime('%Y-%m')
            rows.append(row)

    return pd.DataFrame(rows)


# ─────────────────────────── 3. Campaign ────────────────────────────────────

def generate_campaign():
    """Only real ad/content efforts get a Campaign row — Referral traffic is
    word-of-mouth, not campaign-driven, so it draws from CAMPAIGN_CHANNELS
    (Paid/Organic/Direct), not the full CHANNELS list."""
    rows = []
    cid = 1
    for month_dt in MONTH_RANGE:
        month_s = month_dt.to_pydatetime()
        month_e = month_end(month_s)
        for _ in range(4):
            channel  = weighted_choice(CAMPAIGN_CHANNELS, CAMPAIGN_CHANNEL_WEIGHTS)
            geo      = weighted_choice(GEOS, GEO_WEIGHTS)
            industry = weighted_choice(INDUSTRIES, INDUSTRY_WEIGHTS)
            icp_seg  = weighted_choice(ICP_SEGMENTS, ICP_WEIGHTS)

            budget   = round(random.uniform(3_000, 25_000), 2)
            spend    = round(budget * random.uniform(0.75, 1.0), 2)
            cpm      = round(random.uniform(4.0, 18.0), 2)   # used for impressions calc only
            impressions = int(spend / cpm * 1000)
            ctr      = round(random.uniform(0.008, 0.045), 4)
            clicks   = max(1, int(impressions * ctr))
            cpc      = round(spend / clicks, 4)
            cvr      = round(random.uniform(0.01, 0.06), 4)
            conversions = max(1, int(clicks * cvr))

            start_dt = rand_business_dt(month_s, month_s + timedelta(days=5))
            end_dt   = rand_business_dt(month_e - timedelta(days=5), month_e)

            rows.append({
                'campaign_id':         f'CAM-{cid:04d}',
                'campaign_name':       f'{channel} {industry} {month_s.strftime("%b%Y")}',
                'channel':             channel,
                'geo_target':          geo['country'],
                'icp_segment_target':  icp_seg,
                'industry_target':     industry,
                'start_at':            fmt(start_dt),
                'end_at':              fmt(end_dt),
                'budget_usd':          budget,
                'impressions':         impressions,
                'clicks':              clicks,
                'conversions':         conversions,
                'spend':               spend,
                'cpc':                 cpc,
                'ctr':                 ctr,
                'time_period':         month_s.strftime('%Y-%m'),
            })
            cid += 1
    return pd.DataFrame(rows)


# ─────────────────────────── 3b. Creative ───────────────────────────────────

def generate_creative(campaign_df):
    """A creative/ad-variant catalog per campaign — the HTML's `Creative` entity."""
    rows = []
    formats = ['image', 'video', 'text']
    cid = 1
    for _, camp in campaign_df.iterrows():
        n_creatives = random.randint(2, 3)
        for i in range(n_creatives):
            rows.append({
                'creative_id':   f'CRV-{cid:05d}',
                'campaign_id':   camp['campaign_id'],
                'creative_name': f"{camp['channel']} creative {i + 1}",
                'format':        random.choice(formats),
                'created_at':    camp['start_at'],
                'time_period':   camp['time_period'],
            })
            cid += 1
    return pd.DataFrame(rows)


# ─────────────────────────── 4. Account ─────────────────────────────────────

def generate_account(plan_df, csm_df):
    price_map = {row['plan_id']: row['list_price_per_seat'] for _, row in plan_df.iterrows()}

    rows = []
    company_names_used = set()

    monthly_counts = np.random.multinomial(TOTAL_ACCOUNTS, ACCOUNT_MONTHLY_WEIGHTS)

    for month_idx, (month_dt, n_accounts) in enumerate(zip(MONTH_RANGE, monthly_counts)):
        month_s = month_dt.to_pydatetime()
        month_e = month_end(month_s)

        for _ in range(n_accounts):
            icp_seg  = weighted_choice(ICP_SEGMENTS, ICP_WEIGHTS)
            industry = weighted_choice(INDUSTRIES, INDUSTRY_WEIGHTS)
            geo      = weighted_choice(GEOS, GEO_WEIGHTS)
            channel  = weighted_choice(CHANNELS, CHANNEL_WEIGHTS)

            created_at = rand_business_dt(month_s, month_e)

            tier_options = list(SEGMENT_PLAN_DISTRIBUTION[icp_seg].keys())
            base_wts     = list(SEGMENT_PLAN_DISTRIBUTION[icp_seg].values())
            adj_wts      = [w * tier_demand_multiplier(t, month_dt) for t, w in zip(tier_options, base_wts)]
            tier         = weighted_choice(tier_options, adj_wts)
            current_plan_id = plan_id_for_tier_at(tier, created_at)

            is_self_serve = tier in ('Free', 'Plus')
            motion        = 'Self-serve' if is_self_serve else 'Sales-led'
            is_paid       = tier != 'Free'

            emp_lo, emp_hi = ICP_EMPLOYEE_RANGE[icp_seg]
            rev_lo, rev_hi = ICP_REVENUE_RANGE[icp_seg]
            employee_count = random.randint(emp_lo, emp_hi)
            annual_revenue = random.randint(rev_lo, rev_hi)

            wtp_mult  = WTP_MEAN_MULTIPLIER_BY_SEGMENT.get(icp_seg, 1.2)
            wtp_noise = max(0.5, random.gauss(1.0, WTP_NOISE_STD))
            list_price = price_map.get(current_plan_id, 35.0)
            wtp_usd_per_seat = round(list_price * wtp_mult * wtp_noise, 2)

            csm_id = None
            if not is_self_serve:
                pool = CSM_BY_SEGMENT.get(icp_seg, CSM_BY_SEGMENT['SMB'])
                csm_id = random.choice(pool)

            lifecycle_options = list(LIFECYCLE_STATE_WEIGHTS.keys())
            lifecycle_wts     = list(LIFECYCLE_STATE_WEIGHTS.values())
            lifecycle_state   = weighted_choice(lifecycle_options, lifecycle_wts)

            first_paid_at = (
                rand_business_dt(created_at, created_at + timedelta(days=14))
                if is_paid else None
            )

            _churned_at = None
            if lifecycle_state == 'Churned':
                churn_after = random.randint(60, 400)
                _churned_at = created_at + timedelta(days=churn_after)
                if _churned_at > SIM_END:
                    _churned_at = SIM_END - timedelta(days=random.randint(1, 30))

            for _ in range(20):
                name = f"{random.choice(COMPANY_ADJECTIVES)} {random.choice(COMPANY_NOUNS)}"
                if name not in company_names_used:
                    company_names_used.add(name)
                    break

            rows.append({
                'account_id':         uid(),
                'account_name':       name,
                'industry':           industry,
                'employee_count':     employee_count,
                'annual_revenue_usd': annual_revenue,
                'geo':                geo['country'],
                'region':             geo['region'],
                'segment':            icp_seg,
                'motion':             motion,
                'account_size_band':  None,   # filled in post-seat-generation, see update_account_size_band()
                'lifecycle_state':    lifecycle_state,
                'current_plan_id':    current_plan_id,
                'csm_owner_id':       csm_id,
                'am_owner_id':        random.choice(AM_OWNERS),
                'is_self_serve':      is_self_serve,
                'acquisition_channel': channel,
                'willingness_to_pay_usd_per_seat': wtp_usd_per_seat,
                'first_paid_at':      fmt(first_paid_at),
                'created_at':         fmt(created_at),
                'time_period':        month_s.strftime('%Y-%m'),
                '_churned_at':        fmt(_churned_at),
                '_tier':              tier,
                '_icp_seg':           icp_seg,
                '_is_paid':           is_paid,
            })

    return pd.DataFrame(rows)


def update_account_size_band(account_df, contract_df):
    """Real seat-count-derived band, decoupled from segment (was a 1:1 relabel
    before). Uses Contract.seat_count (purchased capacity, SMB 2-10 / Mid-market
    5-50 / Enterprise 20-200) rather than actual assigned-user Seat rows —
    the latter tops out around 15 under USERS_PER_ACCOUNT, so it could never
    reach the HTML's 50-200/200+ bands at all."""
    account_df = account_df.copy()
    seat_counts = contract_df.groupby('account_id')['seat_count'].max().rename('_seat_count').reset_index()
    account_df = account_df.merge(seat_counts, on='account_id', how='left')
    account_df['_seat_count'] = account_df['_seat_count'].fillna(0).astype(int)
    account_df['account_size_band'] = account_df['_seat_count'].apply(
        lambda n: band_from_edges(n, ACCOUNT_SIZE_BAND_EDGES, ACCOUNT_SIZE_BANDS)
    )
    account_df.drop(columns=['_seat_count'], inplace=True)
    return account_df


# ─────────────────────────── 5. Cohort (monthly) ────────────────────────────

def generate_cohort():
    rows = []
    for month_dt in MONTH_RANGE:
        month_s  = month_dt.to_pydatetime()
        period   = month_s.strftime('%Y-%m')
        for ch in CHANNELS:
            rows.append({
                'cohort_id':         f'COH-{period}-{ch[:3].upper()}',
                'cohort_period':     period,
                'cohort_start_date': fmt(month_s),
                'cohort_grain':      'monthly',
                'channel_origin':    ch,
                'plan_at_signup':    None,   # updated in update_cohort
                'segment':           None,   # updated in update_cohort
                'user_count':        0,
                'activated_count':   0,
                'activation_rate':   0.0,
                'time_period':       period,
            })
    return pd.DataFrame(rows)


def generate_cohort_weekly(user_df):
    """Parallel weekly grain — the Functional altitude's clock is weekly, and
    monthly-only cohorts couldn't be sliced that way before this."""
    u = user_df.copy()
    u['signup_at_dt'] = pd.to_datetime(u['signup_at'])
    u['week_start'] = (u['signup_at_dt'] - pd.to_timedelta(u['signup_at_dt'].dt.dayofweek, unit='D')).dt.floor('D')

    rows = []
    for (week_start, channel), grp in u.groupby(['week_start', 'channel_origin']):
        total = len(grp)
        activated = int(grp['activated_at'].notna().sum())
        rows.append({
            'cohort_id':       f'COHW-{week_start.strftime("%Y-%m-%d")}-{channel[:3].upper()}',
            'cohort_period':   week_start.strftime('%Y-%m-%d'),
            'cohort_grain':    'weekly',
            'channel_origin':  channel,
            'user_count':      total,
            'activated_count': activated,
            'activation_rate': round(activated / total, 4) if total > 0 else 0.0,
            'time_period':     week_start.strftime('%Y-%m'),
        })
    return pd.DataFrame(rows)


# ─────────────────────────── 6. User ────────────────────────────────────────

def generate_user(account_df, cohort_df):
    cohort_lookup = {
        (row['cohort_period'], row['channel_origin']): row['cohort_id']
        for _, row in cohort_df.iterrows()
    }

    rows = []
    for _, acc in account_df.iterrows():
        icp_seg     = acc['_icp_seg']
        created_at  = pd.to_datetime(acc['created_at'])
        acc_churn   = parse_dt(acc['_churned_at'])
        channel     = acc['acquisition_channel']
        lifecycle   = acc['lifecycle_state']
        motion      = acc['motion']

        lo, hi = USERS_PER_ACCOUNT.get(icp_seg, (2, 6))
        n_users = random.randint(lo, hi)

        for u_idx in range(n_users):
            signup_at = created_at + timedelta(hours=random.randint(0, 168))
            signup_at = min(signup_at, SIM_END - timedelta(days=1))

            cohort_period = signup_at.strftime('%Y-%m')
            cohort_id     = cohort_lookup.get((cohort_period, channel),
                                              cohort_lookup.get((cohort_period, 'Direct'), None))

            activated_at = None
            user_lifecycle = lifecycle
            if lifecycle in ('Active', 'Reactivated', 'Core', 'Power'):
                days_to_activate = random.randint(1, 30)
                activated_at = signup_at + timedelta(days=days_to_activate)
                if activated_at > SIM_END:
                    activated_at = None

            value_moment_at = None
            if activated_at is not None:
                vm = activated_at + timedelta(days=random.randint(0, 5))
                if vm <= SIM_END:
                    value_moment_at = vm

            if acc_churn:
                last_active = acc_churn - timedelta(hours=random.randint(1, 72))
            else:
                last_active = SIM_END - timedelta(hours=random.randint(0, 48))

            is_admin = (u_idx == 0)
            role     = 'Admin' if is_admin else random.choice(USER_ROLES[1:])
            dept     = random.choice(USER_DEPARTMENTS)

            fname = random.choice(FIRST_NAMES)
            lname = random.choice(LAST_NAMES)
            email = f"{fname.lower()}.{lname.lower()}{random.randint(1,99)}@{acc['account_name'].lower().replace(' ','')}.com"

            rows.append({
                'user_id':          uid(),
                'account_id':       acc['account_id'],
                'cohort_id':        cohort_id,
                'full_name':        f'{fname} {lname}',
                'email':            email,
                'role':             role,
                'department':       dept,
                'is_admin':         is_admin,
                'lifecycle_state':  user_lifecycle,
                'channel_origin':   channel,
                'motion':           motion,
                'iq_segment':       icp_seg,
                'signup_at':        fmt(signup_at),
                'activated_at':     fmt(activated_at),
                'value_moment_at':  fmt(value_moment_at),
                'last_active_at':   fmt(last_active),
                'time_period':      signup_at.strftime('%Y-%m'),
                '_churned_at':      fmt(acc_churn),
            })

    return pd.DataFrame(rows)


# ─────────────────────────── Update cohort counts ───────────────────────────

def update_cohort(cohort_df, user_df, account_df):
    cohort_df = cohort_df.copy()

    uc = user_df.groupby('cohort_id').size().reset_index(name='user_count')
    ac = user_df[user_df['activated_at'].notna()].groupby('cohort_id').size().reset_index(name='activated_count')

    cohort_df = cohort_df.merge(uc, on='cohort_id', how='left', suffixes=('_old', ''))
    cohort_df = cohort_df.merge(ac, on='cohort_id', how='left', suffixes=('_old', ''))

    for col in ['user_count', 'activated_count']:
        new_col = col
        old_col = col + '_old'
        if old_col in cohort_df.columns:
            cohort_df[new_col] = cohort_df[new_col].fillna(cohort_df[old_col]).fillna(0).astype(int)
            cohort_df.drop(columns=[old_col], inplace=True)
        else:
            cohort_df[new_col] = cohort_df[new_col].fillna(0).astype(int)

    cohort_df['activation_rate'] = (
        cohort_df['activated_count'] / cohort_df['user_count'].replace(0, np.nan)
    ).fillna(0).round(4)

    # Plan at signup and segment: modal values from users in each cohort
    u_acc = user_df[['cohort_id', 'account_id']].merge(
        account_df[['account_id', '_tier', '_icp_seg']], on='account_id', how='left'
    )
    plan_mode = u_acc.groupby('cohort_id')['_tier'].agg(
        lambda x: x.mode().iloc[0] if len(x) > 0 and x.notna().any() else 'Free'
    ).reset_index().rename(columns={'_tier': 'plan_at_signup_new'})
    seg_mode  = u_acc.groupby('cohort_id')['_icp_seg'].agg(
        lambda x: x.mode().iloc[0] if len(x) > 0 and x.notna().any() else 'SMB'
    ).reset_index().rename(columns={'_icp_seg': 'segment_new'})

    cohort_df = cohort_df.merge(plan_mode, on='cohort_id', how='left')
    cohort_df = cohort_df.merge(seg_mode,  on='cohort_id', how='left')
    cohort_df['plan_at_signup'] = cohort_df['plan_at_signup_new'].fillna('Free')
    cohort_df['segment']        = cohort_df['segment_new'].fillna('SMB')
    cohort_df.drop(columns=['plan_at_signup_new', 'segment_new'], inplace=True)

    return cohort_df


# ─────────────────────────── 7. Visitor ─────────────────────────────────────

def generate_visitor(campaign_df, user_df, creative_df):
    rows = []
    creative_by_campaign = creative_df.groupby('campaign_id')['creative_id'].apply(list).to_dict()

    paid_users = user_df[user_df['lifecycle_state'] != 'Churned'].sample(
        frac=0.65, random_state=42
    ).copy()

    # Converting visitors: one per paid user sample
    for _, usr in paid_users.iterrows():
        signup_at  = pd.to_datetime(usr['signup_at'])
        usr_period = usr['time_period']
        channel    = usr['channel_origin']

        campaign_id  = None
        creative_id  = None
        est_industry = None

        if channel != 'Referral':
            same_month = campaign_df[(campaign_df['time_period'] == usr_period) & (campaign_df['channel'] == channel)]
            if len(same_month) == 0:
                same_month = campaign_df[campaign_df['channel'] == channel]
            if len(same_month) == 0:
                same_month = campaign_df

            camp = same_month.sample(1, random_state=None).iloc[0]
            campaign_id = camp['campaign_id']
            est_industry = camp['industry_target']
            cids = creative_by_campaign.get(campaign_id, [])
            creative_id = random.choice(cids) if cids else None

        first_seen = max(signup_at - timedelta(days=random.randint(1, 14)), SIM_START)
        last_seen  = max(signup_at - timedelta(hours=random.randint(1, 12)), SIM_START)

        utm_source, utm_medium = CHANNEL_UTM.get(channel, ('other', 'other'))

        is_qualified = random.random() < QUALIFY_RATE
        qualified_at = fmt(signup_at + timedelta(days=random.randint(1, 5))) if is_qualified else None

        rows.append({
            'visitor_id':            uid(),
            'campaign_id':           campaign_id,
            'creative_id':           creative_id,
            'anonymous_id':          uid(),
            'channel':               channel,
            'source':                utm_source,
            'medium':                utm_medium,
            'geo':                   weighted_choice(GEOS, GEO_WEIGHTS)['country'],
            'lp_url':                random.choice(LANDING_PAGES),
            'device_type':           weighted_choice(DEVICE_TYPES, DEVICE_WEIGHTS),
            'page_views':            random.randint(2, 12),
            'session_count':         random.randint(1, 5),
            'first_seen_at':         fmt(first_seen),
            'last_seen_at':          fmt(last_seen),
            'did_signup':            True,
            'signup_at':             fmt(signup_at),
            'is_qualified':          is_qualified,
            'qualified_at':          qualified_at,
            'converted_user_id':     usr['user_id'],
            'est_account_size_band': weighted_choice(ACCOUNT_SIZE_BANDS, [0.40, 0.35, 0.20, 0.05]),
            'est_industry':          est_industry if est_industry else weighted_choice(INDUSTRIES, INDUSTRY_WEIGHTS),
            'time_period':           first_seen.strftime('%Y-%m'),
        })

    # Non-converting visitors (~3x converting), tied to real campaigns only
    n_non_convert = len(rows) * 3
    for _ in range(n_non_convert):
        camp = campaign_df.sample(1, random_state=None).iloc[0]
        ms   = pd.to_datetime(camp['start_at'])
        me   = pd.to_datetime(camp['end_at'])
        if ms >= me:
            me = ms + timedelta(days=25)
        first_seen = rand_business_dt(ms.to_pydatetime(), me.to_pydatetime())
        last_seen  = first_seen + timedelta(hours=random.randint(1, 48))

        utm_source, utm_medium = CHANNEL_UTM.get(camp['channel'], ('other', 'other'))
        cids = creative_by_campaign.get(camp['campaign_id'], [])
        creative_id = random.choice(cids) if cids else None

        rows.append({
            'visitor_id':            uid(),
            'campaign_id':           camp['campaign_id'],
            'creative_id':           creative_id,
            'anonymous_id':          uid(),
            'channel':               camp['channel'],
            'source':                utm_source,
            'medium':                utm_medium,
            'geo':                   weighted_choice(GEOS, GEO_WEIGHTS)['country'],
            'lp_url':                random.choice(LANDING_PAGES),
            'device_type':           weighted_choice(DEVICE_TYPES, DEVICE_WEIGHTS),
            'page_views':            random.randint(1, 5),
            'session_count':         random.randint(1, 2),
            'first_seen_at':         fmt(first_seen),
            'last_seen_at':          fmt(last_seen),
            'did_signup':            False,
            'signup_at':             None,
            'is_qualified':          False,
            'qualified_at':          None,
            'converted_user_id':     None,
            'est_account_size_band': weighted_choice(ACCOUNT_SIZE_BANDS, [0.40, 0.35, 0.20, 0.05]),
            'est_industry':          camp['industry_target'],
            'time_period':           first_seen.strftime('%Y-%m'),
        })

    return pd.DataFrame(rows)


# ─────────────────────────── 8. Seat ────────────────────────────────────────

def generate_seat(account_df, user_df, plan_df):
    price_map = {
        row['plan_id']: row['list_price_per_seat']
        for _, row in plan_df.iterrows()
    }
    acc_plan = account_df.set_index('account_id')['current_plan_id'].to_dict()

    rows = []
    for _, usr in user_df.iterrows():
        plan_id    = acc_plan.get(usr['account_id'], 'plan_free')
        price      = price_map.get(plan_id, 0.0)
        is_paid    = price > 0
        billing    = weighted_choice(BILLING_CYCLES, BILLING_CYCLE_WEIGHTS)
        assigned   = pd.to_datetime(usr['signup_at'])
        churned_at = fmt(parse_dt(usr['_churned_at']))

        rows.append({
            'seat_id':       uid(),
            'account_id':    usr['account_id'],
            'user_id':       usr['user_id'],
            'plan_id':       plan_id,
            'seat_status':   'active' if is_paid else 'free',
            'seat_mrr':      round(price, 2),
            'billing_cycle': billing,
            'is_paid':       is_paid,
            'activated_at':  fmt(assigned),
            'churned_at':    churned_at,
            'time_period':   assigned.strftime('%Y-%m'),
        })

    return pd.DataFrame(rows)


# ─────────────────────────── 9. Contract ────────────────────────────────────

def generate_contract(account_df, plan_df):
    price_map    = {row['plan_id']: row['list_price_per_seat'] for _, row in plan_df.iterrows()}

    paid_accounts = account_df[account_df['_is_paid'] == True].copy()

    rows = []
    for _, acc in paid_accounts.iterrows():
        plan_id    = acc['current_plan_id']
        price_psm  = price_map.get(plan_id, 35.0)
        icp_seg    = acc['_icp_seg']

        lo, hi  = DISCOUNT_BY_SEGMENT.get(icp_seg, (0, 10))
        discount = random.randint(lo, hi)

        billing = weighted_choice(BILLING_CYCLES, BILLING_CYCLE_WEIGHTS)

        s_lo, s_hi  = SEAT_RANGES_BY_SEGMENT.get(icp_seg, (2, 10))
        seats       = random.randint(s_lo, s_hi)

        net_price = price_psm * (1 - discount / 100)
        mrr       = round(net_price * seats, 2)
        arr       = round(mrr * 12, 2)

        start_at  = pd.to_datetime(acc['created_at'])
        term_days = 365 if billing == 'annual' else 30
        nominal_end_at = start_at + timedelta(days=term_days)

        renewal_at   = nominal_end_at + timedelta(days=1)
        churned_dt   = parse_dt(acc['_churned_at'])
        realized_pps = round(mrr / seats, 2) if seats > 0 else 0.0
        addon_mrr    = round(random.uniform(0, 100), 2) if icp_seg == 'Enterprise' else 0.0
        deal_band    = band_from_edges(arr, DEAL_SIZE_BAND_EDGES, DEAL_SIZE_BANDS)

        # Only mark THIS term churned if the account's churn date actually
        # falls within it -- a churn happening during a later (renewal) term
        # doesn't make this first term retroactively churned.
        status = 'active'
        end_at = nominal_end_at
        if churned_dt and churned_dt < SIM_END and churned_dt <= nominal_end_at:
            status = 'churned'
            end_at = max(start_at, churned_dt)

        rows.append({
            'contract_id':             uid(),
            'account_id':              acc['account_id'],
            'plan_id':                 plan_id,
            'status':                  status,
            'seat_count':              seats,
            'mrr':                     mrr,
            'arr':                     arr,
            'billing_cycle':           billing,
            'start_at':                fmt(start_at),
            'end_at':                  fmt(end_at),
            'renewal_at':              fmt(renewal_at),
            'discount_pct':            discount,
            'realized_price_per_seat': realized_pps,
            'addon_mrr':               addon_mrr,
            'deal_size_band':          deal_band,
            'time_period':             start_at.strftime('%Y-%m'),
        })

        # Renewal chain: keep renewing at the same cadence for as long as the
        # account remains active and we're still within the sim window.
        # Previously this only fired ONCE (a single "if", not a loop), and
        # only for annual billing -- fine for annual since one 365-day
        # renewal already covers the whole ~21-month sim window from any
        # start date, but monthly-billing contracts only ever got ONE 30-day
        # term, so they "expired" after their first month even though the
        # account itself kept paying. Both cadences now renew in a proper
        # loop, stopping at whichever comes first: the account's churn date,
        # or the end of the sim window. Each term is independently checked
        # against churned_dt, so a churn during a later renewal term no
        # longer requires (or wrongly implies) that earlier terms churned too.
        cur_end    = end_at
        cur_mrr    = mrr
        cur_status = status
        while cur_status == 'active' and pd.to_datetime(cur_end) <= pd.to_datetime(fmt(SIM_END)):
            r_start  = pd.to_datetime(cur_end) + timedelta(days=1)
            r_end    = r_start + timedelta(days=term_days)
            r_status = 'active'
            if churned_dt and churned_dt < SIM_END and churned_dt <= r_end:
                r_status = 'churned'
                r_end = max(r_start, churned_dt)
            r_mrr        = round(cur_mrr * random.uniform(1.0, 1.15), 2)
            r_arr        = round(r_mrr * 12, 2)
            r_realized   = round(r_mrr / seats, 2) if seats > 0 else 0.0
            r_deal_band  = band_from_edges(r_arr, DEAL_SIZE_BAND_EDGES, DEAL_SIZE_BANDS)
            rows.append({
                'contract_id':             uid(),
                'account_id':              acc['account_id'],
                'plan_id':                 plan_id,
                'status':                  r_status,
                'seat_count':              seats,
                'mrr':                     r_mrr,
                'arr':                     r_arr,
                'billing_cycle':           billing,
                'start_at':                fmt(r_start),
                'end_at':                  fmt(r_end),
                'renewal_at':              fmt(r_end + timedelta(days=1)),
                'discount_pct':            discount,
                'realized_price_per_seat': r_realized,
                'addon_mrr':               0.0,
                'deal_size_band':          r_deal_band,
                'time_period':             r_start.strftime('%Y-%m'),
            })
            cur_end    = r_end
            cur_mrr    = r_mrr
            cur_status = r_status

    return pd.DataFrame(rows)


def generate_contract_monthly(contract_df):
    """One row per account per calendar month it was live AT MONTH-END -- a
    genuine periodic-snapshot fact (same convention already used for
    headcount/cash/cost_transaction), so 'MRR as of period-end' can be read
    with a single flat filter instead of the query layer trying to
    reconstruct 'as of' from a lifetime-grain start_at/end_at pair. Additive
    -- `contract` stays exactly as it is, still the right source for
    deal-size/discount/individual-contract-lifecycle needs.

    Deliberately keyed on month-END coverage (start_at <= month_end AND
    end_at >= month_end), not mere overlap with the month -- an account
    whose monthly-billing contract renews mid-month (old contract ends the
    15th, renewal starts the 16th) would otherwise get two overlapping rows
    for that one month, double-counting its MRR. An account that fully
    churned before month-end correctly gets zero rows for that month."""
    start_ts = pd.to_datetime(contract_df['start_at'])
    end_ts   = pd.to_datetime(contract_df['end_at'])

    chunks = []
    for month_dt in MONTH_RANGE:
        period  = month_dt.strftime('%Y-%m')
        month_e = month_end(month_dt.to_pydatetime())

        live = contract_df[(start_ts <= month_e) & (end_ts >= month_e)][
            ['contract_id', 'account_id', 'plan_id', 'mrr', 'arr', 'seat_count']
        ].copy()
        live['month']       = month_dt.strftime('%Y-%m-%d')
        live['time_period'] = period
        chunks.append(live)

    df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    print(f"  Generated {len(df):,} contract-month snapshot rows")
    return df


def update_contract_utilisation(contract_df, seat_df):
    """seats-used vs. seats-purchased -> seat_utilisation_pct + band, per contract."""
    contract_df = contract_df.copy()
    seat_counts = seat_df.groupby('account_id').size().rename('_actual_seats').reset_index()
    contract_df = contract_df.merge(seat_counts, on='account_id', how='left')
    contract_df['_actual_seats'] = contract_df['_actual_seats'].fillna(0).astype(int)
    contract_df['seats_used'] = contract_df[['_actual_seats', 'seat_count']].min(axis=1)
    contract_df['seat_utilisation_pct'] = (
        contract_df['seats_used'] / contract_df['seat_count'].replace(0, np.nan)
    ).fillna(0).round(4).clip(upper=1.0)
    contract_df['utilisation_band'] = contract_df['seat_utilisation_pct'].apply(
        lambda p: band_from_edges(p, UTILISATION_BAND_EDGES, UTILISATION_BANDS)
    )
    contract_df.drop(columns=['_actual_seats'], inplace=True)
    return contract_df


def generate_discount_grant(contract_df):
    df = contract_df[contract_df['discount_pct'] > 0]
    rows = [{
        'grant_id':     uid(),
        'contract_id':  c['contract_id'],
        'account_id':   c['account_id'],
        'discount_pct': c['discount_pct'],
        'granted_at':   c['start_at'],
        'time_period':  c['time_period'],
    } for _, c in df.iterrows()]
    return pd.DataFrame(rows)


def generate_price_change_event():
    """Derived purely from PLAN_MASTER's SCD-2 versions — every real price change,
    materialized as a discrete event row instead of only living in static fields."""
    by_tier = {}
    for p in PLAN_MASTER:
        by_tier.setdefault(p['tier'], []).append(p)

    rows = []
    for tier, versions in by_tier.items():
        versions_sorted = sorted(versions, key=lambda p: p['effective_from'])
        for i in range(1, len(versions_sorted)):
            old, new = versions_sorted[i - 1], versions_sorted[i]
            rows.append({
                'price_change_id':   uid(),
                'plan_tier':         tier,
                'old_price_per_seat': old['list_price_per_seat'],
                'new_price_per_seat': new['list_price_per_seat'],
                'effective_at':      new['effective_from'] + ' 00:00:00',
                'time_period':       new['effective_from'][:7],
            })
    return pd.DataFrame(rows)


def generate_addon_attach(contract_df):
    df = contract_df[contract_df['addon_mrr'] > 0]
    rows = []
    for _, c in df.iterrows():
        addon = random.choice(ADDON_CATALOG)
        rows.append({
            'attach_id':   uid(),
            'contract_id': c['contract_id'],
            'account_id':  c['account_id'],
            'addon_id':    addon['addon_id'],
            'addon_name':  addon['addon_name'],
            'addon_mrr':   c['addon_mrr'],
            'attached_at': c['start_at'],
            'time_period': c['time_period'],
        })
    return pd.DataFrame(rows)


# ─────────────────────────── 10. UsageEvent ─────────────────────────────────

def generate_usage_event(user_df, account_df):
    evt_names    = EVENT_NAMES
    evt_weights  = EVENT_WEIGHTS
    evt_core_map = {e['event_name']: e['is_core_action'] for e in USAGE_EVENT_TYPES}
    evt_feat_map = {e['event_name']: e['feature_name']   for e in USAGE_EVENT_TYPES}

    CHUNK = 25_000
    chunks = []
    rows   = []
    print("  Generating usage events...")

    def flush():
        if rows:
            chunks.append(pd.DataFrame(rows))
            rows.clear()

    for _, usr in tqdm(user_df.iterrows(), total=len(user_df), desc="  users"):
        signup_at   = pd.to_datetime(usr['signup_at'])
        lifecycle   = usr['lifecycle_state']
        acc_churn   = parse_dt(usr['_churned_at'])
        onboarding_steps_for_user = (
            ONBOARDING_STEPS_SELF_SERVE if usr['motion'] == 'Self-serve' else ONBOARDING_STEPS_SALES_LED
        )

        bucket = USER_LIFECYCLE_TO_EVENT_BUCKET.get(lifecycle, 'Active')
        lo, hi = EVENTS_PER_MONTH.get(bucket, (0, 0))
        if lo == 0 and hi == 0:
            continue

        last_active = acc_churn if acc_churn else SIM_END
        last_active = min(last_active, SIM_END)

        # ── Sequential onboarding funnel ────────────────────────────────────
        # Onboarding steps are generated as a real ordered-per-user sequence,
        # gated by whether/how far this user actually progressed, instead of
        # each step being an independent weighted random draw (which produced
        # a "funnel" that was really just relative event-draw weights, with no
        # per-user dependency between steps). Anchored to activated_at, which
        # already encodes this user's real activation outcome: reaching it
        # means they completed their whole funnel; not reaching it means they
        # dropped off somewhere before the step that would represent full
        # activation.
        activated_at = parse_dt(usr['activated_at'])
        n_steps = len(onboarding_steps_for_user)
        if activated_at is not None:
            n_complete = n_steps
            window_end = min(activated_at, signup_at + timedelta(days=30), last_active)
        else:
            # Didn't activate -> dropped off somewhere in the funnel. Weighted
            # toward earlier steps so the funnel actually narrows, same shape
            # as a real drop-off curve rather than a uniform cutoff.
            weights = [n_steps - i for i in range(n_steps)]
            n_complete = random.choices(range(n_steps), weights=weights, k=1)[0]
            window_end = min(signup_at + timedelta(days=30), last_active)

        window_start = signup_at
        if n_complete > 0 and window_end > window_start:
            for i in range(n_complete):
                step_name = onboarding_steps_for_user[i]
                frac = (i + 1) / (n_steps + 1)
                jitter = timedelta(hours=random.randint(-6, 6))
                ts = window_start + (window_end - window_start) * frac + jitter
                ts = min(max(ts, window_start), window_end)
                rows.append({
                    'event_id':             uid(),
                    'user_id':              usr['user_id'],
                    'account_id':           usr['account_id'],
                    'event_name':           step_name,
                    'feature_name':         evt_feat_map[step_name],
                    'is_core_action':       evt_core_map[step_name],
                    'onboarding_step_name': step_name,
                    'session_id':           uid(),
                    'platform':             weighted_choice(['web', 'desktop', 'mobile'], [0.60, 0.30, 0.10]),
                    'occurred_at':          fmt(ts),
                    'time_period':          ts.strftime('%Y-%m'),
                })

            if len(rows) >= CHUNK:
                flush()

        cur_month = month_start(signup_at)
        while cur_month <= last_active:
            m_end = min(month_end(cur_month), last_active)

            if cur_month.month == signup_at.month and cur_month.year == signup_at.year:
                days_in_month = (m_end - signup_at).days + 1
                total_days    = (m_end - month_start(cur_month)).days + 1
                scale         = days_in_month / max(total_days, 1)
            else:
                scale = 1.0

            n_events = max(0, int(random.randint(lo, hi) * scale))

            for _ in range(n_events):
                evt_name  = random.choices(evt_names, weights=evt_weights, k=1)[0]
                is_core   = evt_core_map[evt_name]
                feat_name = evt_feat_map[evt_name]

                evt_start = max(signup_at, cur_month)
                ts = rand_business_dt(
                    evt_start.to_pydatetime() if hasattr(evt_start, 'to_pydatetime') else evt_start,
                    m_end.to_pydatetime() if hasattr(m_end, 'to_pydatetime') else m_end
                )

                # Onboarding-step tagging happens exclusively in the sequential
                # block above now -- regular monthly events are never tagged,
                # even if they happen to draw one of the same event names.
                onboarding_step = None

                rows.append({
                    'event_id':             uid(),
                    'user_id':              usr['user_id'],
                    'account_id':           usr['account_id'],
                    'event_name':           evt_name,
                    'feature_name':         feat_name,
                    'is_core_action':       is_core,
                    'onboarding_step_name': onboarding_step,
                    'session_id':           uid(),
                    'platform':             weighted_choice(['web', 'desktop', 'mobile'], [0.60, 0.30, 0.10]),
                    'occurred_at':          fmt(ts),
                    'time_period':          ts.strftime('%Y-%m'),
                })

                if len(rows) >= CHUNK:
                    flush()

            if cur_month.month == 12:
                cur_month = cur_month.replace(year=cur_month.year + 1, month=1)
            else:
                cur_month = cur_month.replace(month=cur_month.month + 1)

    flush()
    df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    print(f"  Generated {len(df):,} usage events")
    return df


# ─────────────────────────── 11. SupportTicket ──────────────────────────────

def generate_support_ticket(account_df, user_df):
    rows = []

    for _, usr in user_df.iterrows():
        signup_at   = pd.to_datetime(usr['signup_at'])
        acc_churn   = parse_dt(usr['_churned_at'])
        last_active = acc_churn if acc_churn else SIM_END

        cur_month = month_start(signup_at)
        while cur_month <= last_active:
            if random.random() < 0.04:
                m_end = min(month_end(cur_month), last_active)
                opened_at = rand_business_dt(
                    max(signup_at, cur_month).to_pydatetime() if hasattr(max(signup_at, cur_month), 'to_pydatetime') else max(signup_at, cur_month),
                    m_end.to_pydatetime() if hasattr(m_end, 'to_pydatetime') else m_end
                )

                sev      = weighted_choice(TICKET_PRIORITIES, TICKET_PRIORITY_WEIGHTS)
                rh_lo, rh_hi = RESOLUTION_HOURS_BY_PRIORITY[sev]
                res_hours = round(random.uniform(rh_lo, rh_hi), 1)

                resolved_at = opened_at + timedelta(hours=res_hours)
                if resolved_at > SIM_END:
                    resolved_at = None
                    res_hours   = None

                status = 'open' if resolved_at is None else random.choices(
                    ['resolved', 'closed'], weights=[0.7, 0.3])[0]

                csat = random.choices([1, 2, 3, 4, 5], weights=[0.05, 0.10, 0.20, 0.35, 0.30])[0] \
                       if resolved_at else None

                category = random.choice(TICKET_CATEGORIES)
                subject  = f'{category} issue — {random.choice(["dashboard", "API", "billing", "integration", "export", "login"])}'

                rows.append({
                    'ticket_id':       uid(),
                    'account_id':      usr['account_id'],
                    'user_id':         usr['user_id'],
                    'subject':         subject,
                    'category':        category,
                    'severity':        sev,
                    'status':          status,
                    'channel':         weighted_choice(TICKET_CHANNELS, TICKET_CHANNEL_WEIGHTS),
                    'opened_at':       fmt(opened_at),
                    'resolved_at':     fmt(resolved_at),
                    'resolution_hours': res_hours,
                    'csat_score':      csat,
                    'time_period':     opened_at.strftime('%Y-%m'),
                })

            if cur_month.month == 12:
                cur_month = cur_month.replace(year=cur_month.year + 1, month=1)
            else:
                cur_month = cur_month.replace(month=cur_month.month + 1)

    return pd.DataFrame(rows)


# ─────────────────────────── 11b. QBR ───────────────────────────────────────

def generate_qbr(account_df):
    """Quarterly business reviews — high-touch (Business/Enterprise) accounts
    with a CSM only. HTML's `QBR` activity, previously not modeled at all."""
    rows = []
    eligible = account_df[
        (account_df['_tier'].isin(QBR_ELIGIBLE_TIERS)) & (account_df['csm_owner_id'].notna())
    ]
    quarter_starts = pd.date_range('2025-01-01', '2026-09-01', freq='QS')

    for _, acc in eligible.iterrows():
        created = pd.to_datetime(acc['created_at'])
        churned = parse_dt(acc['_churned_at'])
        end_bound = churned if churned else SIM_END

        for q in quarter_starts:
            if q < created or q > pd.Timestamp(end_bound):
                continue
            qbr_date = rand_business_dt(q.to_pydatetime(), (q + pd.Timedelta(days=80)).to_pydatetime())
            if qbr_date > SIM_END:
                continue
            rows.append({
                'qbr_id':      uid(),
                'account_id':  acc['account_id'],
                'csm_id':      acc['csm_owner_id'],
                'qbr_date':    fmt(qbr_date),
                'time_period': qbr_date.strftime('%Y-%m'),
            })

    return pd.DataFrame(rows)


# ─────────────────────────── 12. ExpansionOpportunity ───────────────────────

def generate_expansion_opportunity(account_df, user_df, plan_df):
    rows = []

    price_map = {row['plan_id']: row['list_price_per_seat'] for _, row in plan_df.iterrows()}
    acc_csm  = account_df.set_index('account_id')['csm_owner_id'].to_dict()
    acc_self_serve = account_df.set_index('account_id')['is_self_serve'].to_dict()

    cutoff_str = (pd.Timestamp(SIM_END) - pd.Timedelta(days=60)).strftime('%Y-%m-%d %H:%M:%S')
    eligible = account_df[
        (account_df['lifecycle_state'].isin(['Active', 'Reactivated', 'Core', 'Power'])) &
        (account_df['_is_paid'] == True) &
        (account_df['created_at'] <= cutoff_str)
    ].copy().reset_index(drop=True)

    eligible = eligible.sample(frac=0.80, random_state=42)

    plan_upgrade_map = {
        'plan_free':          'plan_plus_v2',
        'plan_plus_v1':       'plan_business_v2',
        'plan_plus_v2':       'plan_business_v2',
        'plan_business_v1':   'plan_enterprise',
        'plan_business_v2':   'plan_enterprise',
        'plan_enterprise':    'plan_enterprise',
    }

    for _, acc in eligible.iterrows():
        n_opps  = random.randint(1, 3)
        created = pd.to_datetime(acc['created_at'])
        is_plg  = acc_self_serve.get(acc['account_id'], False)

        for _ in range(n_opps):
            trigger  = random.choice(EXPANSION_TYPES)
            motion   = 'Self-serve' if is_plg else weighted_choice(EXPANSION_MOTION_TYPES, EXPANSION_MOTION_WEIGHTS)
            identified_at = rand_business_dt(
                (created + timedelta(days=60)).to_pydatetime() if hasattr(created + timedelta(days=60), 'to_pydatetime') else created + timedelta(days=60),
                min(SIM_END, (created + timedelta(days=300)).to_pydatetime() if hasattr(created + timedelta(days=300), 'to_pydatetime') else created + timedelta(days=300))
            )

            curr_plan  = acc['current_plan_id']
            prop_plan  = plan_upgrade_map.get(curr_plan, curr_plan)
            curr_price = price_map.get(curr_plan, 35.0)
            prop_price = price_map.get(prop_plan, curr_price)

            curr_seats   = random.randint(2, 20)
            prop_seats   = curr_seats + random.randint(2, 15)
            seats_elig   = prop_seats - curr_seats
            exp_mrr      = round((prop_price - curr_price) * prop_seats + seats_elig * curr_price, 2)
            exp_mrr      = max(exp_mrr, 100.0)

            stage_roll = random.random()
            if stage_roll < 0.25:
                upsell_status = 'Closed Won'
                outcome       = 'Won'
                closed_at     = min(identified_at + timedelta(days=random.randint(14, 60)), SIM_END)
            elif stage_roll < 0.40:
                upsell_status = 'Closed Lost'
                outcome       = 'Lost'
                closed_at     = min(identified_at + timedelta(days=random.randint(14, 45)), SIM_END)
            else:
                upsell_status = random.choice(['Identified', 'Qualifying', 'Proposed', 'Negotiating'])
                outcome       = 'Open'
                closed_at     = None

            rows.append({
                'opp_id':                uid(),
                'account_id':            acc['account_id'],
                'owner_csm_id':          acc_csm.get(acc['account_id']),
                'trigger_type':          trigger,
                'motion_type':           motion,
                'upsell_status':         upsell_status,
                'expected_mrr_uplift':   exp_mrr,
                'seats_eligible':        seats_elig,
                'current_seats':         curr_seats,
                'proposed_seats':        prop_seats,
                'current_plan_id':       curr_plan,
                'proposed_plan_id':      prop_plan,
                'identified_at':         fmt(identified_at),
                'closed_at':             fmt(closed_at),
                'outcome':               outcome,
                'time_period':           identified_at.strftime('%Y-%m'),
            })

    return pd.DataFrame(rows)


def generate_team(account_df):
    """The HTML's `Team` entity — sub-groupings within Mid-market/Enterprise
    accounts (SMB accounts are single-team, so excluded)."""
    rows = []
    eligible = account_df[account_df['segment'].isin(['Mid-market', 'Enterprise'])]
    for _, acc in eligible.iterrows():
        n_teams = random.randint(2, 5) if acc['segment'] == 'Enterprise' else random.randint(1, 3)
        depts = random.sample(USER_DEPARTMENTS, min(n_teams, len(USER_DEPARTMENTS)))
        for dept in depts:
            rows.append({
                'team_id':     uid(),
                'account_id':  acc['account_id'],
                'team_name':   dept,
                'created_at':  acc['created_at'],
                'time_period': acc['time_period'],
            })
    return pd.DataFrame(rows)


def generate_expansion_activity(expansion_df):
    """Projects each opportunity into the HTML's discrete activities
    (hit_limit / upsell_convo / seat_add / tier_upgrade / add_on_buy) instead
    of leaving them collapsed into one categorical trigger field."""
    rows = []
    for _, opp in expansion_df.iterrows():
        if opp['trigger_type'] in ('limit_hit', 'utilization_high'):
            rows.append({
                'activity_id': uid(), 'opp_id': opp['opp_id'], 'account_id': opp['account_id'],
                'activity_type': 'hit_limit', 'occurred_at': opp['identified_at'], 'time_period': opp['time_period'],
            })

        rows.append({
            'activity_id': uid(), 'opp_id': opp['opp_id'], 'account_id': opp['account_id'],
            'activity_type': 'upsell_convo', 'occurred_at': opp['identified_at'], 'time_period': opp['time_period'],
        })

        if opp['outcome'] == 'Won' and opp['closed_at']:
            closed_period = pd.to_datetime(opp['closed_at']).strftime('%Y-%m')
            if opp['seats_eligible'] > 0:
                rows.append({
                    'activity_id': uid(), 'opp_id': opp['opp_id'], 'account_id': opp['account_id'],
                    'activity_type': 'seat_add', 'occurred_at': opp['closed_at'], 'time_period': closed_period,
                })
            if opp['proposed_plan_id'] != opp['current_plan_id']:
                rows.append({
                    'activity_id': uid(), 'opp_id': opp['opp_id'], 'account_id': opp['account_id'],
                    'activity_type': 'tier_upgrade', 'occurred_at': opp['closed_at'], 'time_period': closed_period,
                })
            if opp['trigger_type'] == 'addon_signal':
                rows.append({
                    'activity_id': uid(), 'opp_id': opp['opp_id'], 'account_id': opp['account_id'],
                    'activity_type': 'add_on_buy', 'occurred_at': opp['closed_at'], 'time_period': closed_period,
                })

    return pd.DataFrame(rows)


# ─────────────────────────── 13. HealthScoreSnapshot ────────────────────────

def generate_health_score_snapshot(account_df, usage_event_df, plan_df, support_ticket_df):
    print("  Building weekly aggregates for health scores...")

    ue = usage_event_df.copy()
    ue['occurred_at'] = pd.to_datetime(ue['occurred_at'])
    ue['week_start']  = ue['occurred_at'] - pd.to_timedelta(ue['occurred_at'].dt.dayofweek, unit='D')
    ue['week_start']  = ue['week_start'].dt.floor('D')

    weekly_agg = ue.groupby(['account_id', 'week_start']).agg(
        weekly_active_users=('user_id',       'nunique'),
        weekly_core_actions=('is_core_action', 'sum'),
        weekly_features=    ('feature_name',  'nunique'),
    ).reset_index()

    ue['year_month'] = ue['occurred_at'].dt.strftime('%Y-%m')
    monthly_mau = ue.groupby(['account_id', 'year_month'])['user_id'].nunique().reset_index()
    monthly_mau.columns = ['account_id', 'year_month', 'mau']

    plan_features_map = plan_df.groupby('plan_id')['total_features_count'].max().to_dict()
    plan_tier_map     = plan_df.groupby('plan_id')['tier'].first().to_dict()

    st = support_ticket_df.copy()
    st['opened_at']   = pd.to_datetime(st['opened_at'])
    st['resolved_at'] = pd.to_datetime(st['resolved_at'])

    all_weeks = pd.date_range('2025-01-06', '2026-09-30', freq='W-MON')

    print("  Building account×week base frame...")
    acc_week_rows = []
    for _, acc in account_df.iterrows():
        created = pd.to_datetime(acc['created_at'])
        churned = parse_dt(acc['_churned_at'])
        for w in all_weeks:
            if w < created:
                continue
            if churned is not None and w > churned:
                continue
            acc_week_rows.append({
                'account_id':      acc['account_id'],
                'week_start':      w,
                'current_plan_id': acc['current_plan_id'],
            })

    base = pd.DataFrame(acc_week_rows)
    base['week_start'] = pd.to_datetime(base['week_start'])

    base = base.merge(weekly_agg, on=['account_id', 'week_start'], how='left')
    base[['weekly_active_users', 'weekly_core_actions', 'weekly_features']] = \
        base[['weekly_active_users', 'weekly_core_actions', 'weekly_features']].fillna(0)

    base['year_month'] = base['week_start'].dt.strftime('%Y-%m')
    base = base.merge(monthly_mau, on=['account_id', 'year_month'], how='left')
    base['mau'] = base['mau'].fillna(0)

    base['total_features'] = base['current_plan_id'].map(plan_features_map).fillna(18)
    base['plan_tier']      = base['current_plan_id'].map(plan_tier_map).fillna('Business')

    base['dau']                   = base['weekly_active_users'] / 7.0
    base['dau_mau_ratio']         = (base['dau'] / base['mau'].clip(lower=1)).round(4).clip(upper=1.0)
    base['core_actions_per_user'] = (base['weekly_core_actions'] / base['weekly_active_users'].clip(lower=1)).round(4)
    base['feature_breadth']       = (base['weekly_features'] / base['total_features'].clip(lower=1)).round(4).clip(upper=1.0)

    np.random.seed(42)
    base['support_tickets_open'] = np.random.poisson(0.4, len(base)).clip(0, 10).astype(int)

    activity = (
        (base['weekly_core_actions'] / 5.0).clip(upper=1.0) * 0.70 +
        (base['weekly_active_users'] > 0).astype(float) * 0.30
    )
    breadth       = base['feature_breadth']
    participation = (base['weekly_active_users'] / base['mau'].clip(lower=1)).clip(upper=1.0)
    support_ok    = (1.0 - base['support_tickets_open'] / 5.0).clip(lower=0.0)

    base['score_raw'] = (
        activity      * 40 +
        breadth       * 20 +
        participation * 30 +
        support_ok    * 10
    )
    noise          = np.random.normal(0, 4, len(base))
    base['score']  = (base['score_raw'] + noise).clip(0, 100).round(1)

    # Green/Yellow/Red — the HTML's health-band naming (was red/amber/green).
    base['health_band'] = pd.cut(
        base['score'],
        bins=[-0.01, 49.99, 74.99, 100.01],
        labels=['Red', 'Yellow', 'Green']
    ).astype(str)

    base['snapshot_id'] = [uid() for _ in range(len(base))]
    base['week_start']  = base['week_start'].dt.strftime('%Y-%m-%d %H:%M:%S')
    base['time_period'] = base['year_month']

    result = base[[
        'snapshot_id', 'account_id', 'week_start', 'score',
        'dau_mau_ratio', 'core_actions_per_user', 'feature_breadth',
        'support_tickets_open', 'health_band', 'plan_tier', 'time_period'
    ]].copy()

    print(f"  Generated {len(result):,} health score snapshots")
    return result


# ─────────────────────────── 14. MRR movement (Revenue engine) ──────────────

def generate_mrr_movement(account_df, contract_df, expansion_df, price_change_df, discount_grant_df):
    """The cross-space MRR waterfall bridge: new/reactivate/expand/contract/
    churn/renew, tagged by which functional `space` drove it. This is the
    single addition that makes NRR/GRR/Net New MRR computable.

    space attribution:
      - new: Sales-led deals require an activation/onboarding gate before the
        contract closes, so they're attributed to Activation; self-serve deals
        convert directly off Acquisition traffic.
      - renew: Retention by default, but a renewal that lands in the same
        period as a price change for that tier (or a discount grant for that
        account) was pricing-driven, so it's attributed to Monetisation.
      - churn / reactivate: Retention. expand / contract: Expansion.
    """
    rows = []
    acc_lookup = account_df.set_index('account_id').to_dict('index')

    price_change_periods_by_tier = {}
    for _, pc in price_change_df.iterrows():
        price_change_periods_by_tier.setdefault(pc['plan_tier'], set()).add(pc['time_period'])

    discount_periods_by_account = {}
    for _, dg in discount_grant_df.iterrows():
        discount_periods_by_account.setdefault(dg['account_id'], set()).add(dg['time_period'])

    contracts_by_account = contract_df.sort_values('start_at').groupby('account_id')

    for account_id, grp in contracts_by_account:
        acc = acc_lookup.get(account_id)
        if acc is None:
            continue
        grp = grp.reset_index(drop=True)
        segment  = acc['segment']
        motion   = acc['motion']
        plan_tier = acc['_tier']

        first = grp.iloc[0]
        first_start = pd.to_datetime(first['start_at'])
        new_space = 'Activation' if motion == 'Sales-led' else 'Acquisition'
        rows.append({
            'movement_id': uid(), 'account_id': account_id, 'movement_type': 'new',
            'mrr_delta_usd': first['mrr'], 'seats_delta': int(first['seat_count']),
            'space': new_space, 'motion': motion, 'segment': segment, 'plan_tier': plan_tier,
            'occurred_at': fmt(first_start), 'time_period': first_start.strftime('%Y-%m'),
        })

        for i in range(1, len(grp)):
            prev, cur = grp.iloc[i - 1], grp.iloc[i]
            delta = round(cur['mrr'] - prev['mrr'], 2)
            r_start = pd.to_datetime(cur['start_at'])
            r_period = r_start.strftime('%Y-%m')
            pricing_driven = (
                r_period in price_change_periods_by_tier.get(plan_tier, set())
                or r_period in discount_periods_by_account.get(account_id, set())
            )
            renew_space = 'Monetisation' if pricing_driven else 'Retention'
            rows.append({
                'movement_id': uid(), 'account_id': account_id, 'movement_type': 'renew',
                'mrr_delta_usd': delta, 'seats_delta': 0,
                'space': renew_space, 'motion': motion, 'segment': segment, 'plan_tier': plan_tier,
                'occurred_at': fmt(r_start), 'time_period': r_period,
            })

        last = grp.iloc[-1]
        if last['status'] == 'churned':
            churn_dt = pd.to_datetime(last['end_at'])
            rows.append({
                'movement_id': uid(), 'account_id': account_id, 'movement_type': 'churn',
                'mrr_delta_usd': -round(last['mrr'], 2), 'seats_delta': -int(last['seat_count']),
                'space': 'Retention', 'motion': motion, 'segment': segment, 'plan_tier': plan_tier,
                'occurred_at': fmt(churn_dt), 'time_period': churn_dt.strftime('%Y-%m'),
            })

        # Reactivation timing isn't tracked precisely on Account today (only a
        # static lifecycle label) — approximated at 90-180 days after first
        # contract start. Flagged simplification, not a real signal.
        if acc['lifecycle_state'] == 'Reactivated':
            react_dt = first_start + timedelta(days=random.randint(90, 180))
            if react_dt <= SIM_END:
                rows.append({
                    'movement_id': uid(), 'account_id': account_id, 'movement_type': 'reactivate',
                    'mrr_delta_usd': round(first['mrr'] * 0.6, 2), 'seats_delta': 0,
                    'space': 'Retention', 'motion': motion, 'segment': segment, 'plan_tier': plan_tier,
                    'occurred_at': fmt(react_dt), 'time_period': react_dt.strftime('%Y-%m'),
                })

    # Expand: from Won expansion opportunities
    won = expansion_df[expansion_df['outcome'] == 'Won']
    for _, opp in won.iterrows():
        closed_dt = parse_dt(opp['closed_at'])
        if closed_dt is None:
            continue
        acc = acc_lookup.get(opp['account_id'])
        if acc is None:
            continue
        rows.append({
            'movement_id': uid(), 'account_id': opp['account_id'], 'movement_type': 'expand',
            'mrr_delta_usd': round(opp['expected_mrr_uplift'], 2), 'seats_delta': int(opp['seats_eligible']),
            'space': 'Expansion', 'motion': acc['motion'], 'segment': acc['segment'], 'plan_tier': acc['_tier'],
            'occurred_at': fmt(closed_dt), 'time_period': closed_dt.strftime('%Y-%m'),
        })

    # Contraction: no real signal exists anywhere else in the data today (no
    # downgrade/seat-reduction events are tracked). A modest synthetic sample
    # of active accounts gets a small negative movement, so GRR/NRR actually
    # exercise the Contraction term instead of trivially never firing.
    active_accounts = account_df[account_df['lifecycle_state'].isin(['Active', 'Core', 'Power'])]
    contraction_sample = active_accounts.sample(frac=0.10, random_state=7)
    contracts_by_acc_latest = contract_df.sort_values('start_at').groupby('account_id').tail(1).set_index('account_id')

    for _, acc in contraction_sample.iterrows():
        if acc['account_id'] not in contracts_by_acc_latest.index:
            continue
        latest = contracts_by_acc_latest.loc[acc['account_id']]
        created = pd.to_datetime(acc['created_at'])
        days_available = max((SIM_END - created).days, 121)
        contraction_dt = created + timedelta(days=random.randint(120, days_available))
        if contraction_dt > SIM_END:
            continue
        drop_pct = random.uniform(0.05, 0.15)
        rows.append({
            'movement_id': uid(), 'account_id': acc['account_id'], 'movement_type': 'contract',
            'mrr_delta_usd': -round(latest['mrr'] * drop_pct, 2), 'seats_delta': 0,
            'space': 'Expansion', 'motion': acc['motion'], 'segment': acc['segment'], 'plan_tier': acc['_tier'],
            'occurred_at': fmt(contraction_dt), 'time_period': contraction_dt.strftime('%Y-%m'),
        })

    return pd.DataFrame(rows)


# ─────────────────────────── 15-19. Cost & Burn / P&L ───────────────────────

def generate_vendor():
    return pd.DataFrame([dict(v) for v in VENDOR_MASTER])


def generate_headcount():
    """Simplified/formulaic — headcount grows at a fixed monthly rate per
    function; People cost = headcount x avg salary. Not vendor-invoice-level
    realism (no explicit decision was recorded on cost-modeling depth)."""
    rows = []
    counts = dict(HEADCOUNT_START)
    for month_dt in MONTH_RANGE:
        period = month_dt.strftime('%Y-%m')
        for fn in FUNCTIONS:
            headcount = counts[fn]
            salary = AVG_MONTHLY_SALARY_USD_BY_FUNCTION[fn]
            rows.append({
                'headcount_id':          f'HC-{period}-{fn.replace("&", "").replace(" ", "")}',
                'function':              fn,
                'headcount_count':       round(headcount),
                'avg_monthly_salary_usd': salary,
                'people_cost_usd':       round(headcount * salary, 2),
                'time_period':           period,
            })
            counts[fn] = counts[fn] * (1 + HEADCOUNT_MONTHLY_GROWTH[fn])
    return pd.DataFrame(rows)


def generate_cost_transaction(account_df, contract_df, vendor_df, headcount_df):
    """Cloud & infra / AI inference / Other cost lines, by vendor, by month, plus
    a People cost_line row per period/function sourced from Headcount.people_cost_usd
    (tagged to the internal-payroll placeholder vendor) so cost_transaction alone
    is a complete source for any 'Cost by cost_line' breakdown."""
    rows = []

    for month_idx, month_dt in enumerate(MONTH_RANGE):
        period = month_dt.strftime('%Y-%m')
        month_s = month_dt.to_pydatetime()
        month_e = month_end(month_s)

        active_mask = (pd.to_datetime(account_df['created_at']) <= month_e)
        churned_dates = account_df['_churned_at'].apply(parse_dt)
        active_mask &= (churned_dates.isna() | (pd.Series(churned_dates.tolist(), index=account_df.index) >= month_s))
        n_active = int(active_mask.sum())

        mrr_this_month = contract_df[
            (pd.to_datetime(contract_df['start_at']) <= month_e) &
            (pd.to_datetime(contract_df['end_at']) >= month_s)
        ]['mrr'].sum()

        cloud_total = CLOUD_COST_BASE_FIXED_USD + n_active * CLOUD_COST_PER_ACCOUNT_USD
        cloud_vendors = vendor_df[vendor_df['cost_line'] == 'Cloud & infra']
        for _, v in cloud_vendors.iterrows():
            rows.append({
                'cost_id': uid(), 'vendor_id': v['vendor_id'], 'vendor_name': v['vendor_name'],
                'cost_line': 'Cloud & infra', 'function': 'R&D',
                'amount_usd': round(cloud_total / len(cloud_vendors), 2),
                'occurred_at': fmt(month_e), 'time_period': period,
            })

        ai_rate = AI_INFERENCE_COST_PER_ACCOUNT_USD_START * ((1 + AI_INFERENCE_MONTHLY_RAMP) ** month_idx)
        ai_vendors = vendor_df[vendor_df['cost_line'] == 'AI inference']
        for _, v in ai_vendors.iterrows():
            rows.append({
                'cost_id': uid(), 'vendor_id': v['vendor_id'], 'vendor_name': v['vendor_name'],
                'cost_line': 'AI inference', 'function': 'R&D',
                'amount_usd': round(n_active * ai_rate, 2),
                'occurred_at': fmt(month_e), 'time_period': period,
            })

        other_total = OTHER_COST_BASE_FIXED_USD + mrr_this_month * OTHER_COST_PCT_OF_MRR
        other_vendors = vendor_df[vendor_df['cost_line'] == 'Other']
        for _, v in other_vendors.iterrows():
            rows.append({
                'cost_id': uid(), 'vendor_id': v['vendor_id'], 'vendor_name': v['vendor_name'],
                'cost_line': 'Other', 'function': 'G&A',
                'amount_usd': round(other_total / len(other_vendors), 2),
                'occurred_at': fmt(month_e), 'time_period': period,
            })

        people_vendor = vendor_df[vendor_df['cost_line'] == 'People'].iloc[0]
        period_headcount = headcount_df[headcount_df['time_period'] == period]
        for _, hc in period_headcount.iterrows():
            rows.append({
                'cost_id': uid(), 'vendor_id': people_vendor['vendor_id'], 'vendor_name': people_vendor['vendor_name'],
                'cost_line': 'People', 'function': hc['function'],
                'amount_usd': hc['people_cost_usd'],
                'occurred_at': fmt(month_e), 'time_period': period,
            })

    return pd.DataFrame(rows)


def generate_revenue_line(contract_df):
    """The `Revenue line` entity: Revenue = MRR (Subscription) + Services.
    Services didn't exist anywhere before — small % of MRR, by design."""
    rows = []
    for month_dt in MONTH_RANGE:
        period = month_dt.strftime('%Y-%m')
        month_s = month_dt.to_pydatetime()
        month_e = month_end(month_s)

        mrr_this_month = contract_df[
            (pd.to_datetime(contract_df['start_at']) <= month_e) &
            (pd.to_datetime(contract_df['end_at']) >= month_s)
        ]['mrr'].sum()

        rows.append({'revenue_line_id': uid(), 'revenue_type': 'Subscription',
                      'amount_usd': round(mrr_this_month, 2), 'occurred_at': fmt(month_e), 'time_period': period})
        rows.append({'revenue_line_id': uid(), 'revenue_type': 'Services',
                      'amount_usd': round(mrr_this_month * SERVICES_REVENUE_PCT_OF_MRR, 2),
                      'occurred_at': fmt(month_e), 'time_period': period})
    return pd.DataFrame(rows)


def generate_cash(cost_transaction_df, revenue_line_df):
    """The `Cash` entity: a tracked stock (opening balance + period deltas),
    not derivable purely from Revenue-minus-Cost without an anchor value.
    `cost_transaction_df` already includes the People cost_line (sourced from
    Headcount), so it alone is the complete cost figure here — don't also
    subtract Headcount separately or People gets double-counted."""
    rows = []
    cash = OPENING_CASH_USD
    for month_dt in MONTH_RANGE:
        period = month_dt.strftime('%Y-%m')
        month_e = month_end(month_dt.to_pydatetime())

        cost    = cost_transaction_df[cost_transaction_df['time_period'] == period]['amount_usd'].sum()
        revenue = revenue_line_df[revenue_line_df['time_period'] == period]['amount_usd'].sum()

        opening = cash
        net_change = round(revenue - cost, 2)
        cash = round(cash + net_change, 2)

        rows.append({
            'cash_id': uid(), 'time_period': period, 'as_of': fmt(month_e),
            'opening_cash_usd': opening, 'net_change_usd': net_change, 'cash_balance_usd': cash,
        })
    return pd.DataFrame(rows)


# ─────────────────────────── 20-21. Weekly grain (campaign) ─────────────────

def generate_campaign_weekly(campaign_df):
    """Weekly campaign performance — the monthly aggregate campaign.impressions/
    clicks/spend can't be sliced weekly on its own; this allocates the monthly
    totals evenly across the campaign's active weeks (an allocation, not
    independently observed weekly data — flagged as such)."""
    rows = []
    for _, camp in campaign_df.iterrows():
        start = pd.to_datetime(camp['start_at'])
        end   = pd.to_datetime(camp['end_at'])
        if end <= start:
            end = start + timedelta(days=7)

        weeks = pd.date_range(start.normalize(), end.normalize(), freq='W-MON')
        if len(weeks) == 0:
            weeks = pd.DatetimeIndex([start.normalize()])
        n_weeks = len(weeks)

        for w in weeks:
            rows.append({
                'campaign_id': camp['campaign_id'],
                'week_start':  fmt(w),
                'channel':     camp['channel'],
                'impressions': int(camp['impressions'] / n_weeks),
                'clicks':      int(camp['clicks'] / n_weeks),
                'conversions': max(0, int(camp['conversions'] / n_weeks)),
                'spend':       round(camp['spend'] / n_weeks, 2),
                'time_period': camp['time_period'],
            })
    return pd.DataFrame(rows)


# ─────────────────────────── Validation ─────────────────────────────────────

def validate_all(dfs):
    print("\n── Validation ──────────────────────────────────────────────────────────")
    expected_months = 21
    all_ok = True

    # Static reference/catalog tables: no time_period expected, skip that check.
    STATIC = {'vendor'}
    # Genuinely sparse-by-nature tables (event-driven, not one-row-per-month):
    # a low or uneven month count here is expected, not a data-quality issue.
    EXEMPT = {
        'expansion_opportunity', 'qbr', 'discount_grant', 'price_change_event',
        'addon_attach', 'team', 'creative', 'expansion_activity',
    }

    for name, df in dfs.items():
        if name in STATIC:
            print(f"  {name:30s}: {len(df):>8,} rows | static reference table")
            continue

        if 'time_period' not in df.columns:
            print(f"  [WARN] {name}: missing time_period column")
            all_ok = False
            continue

        n_months = df['time_period'].nunique()
        min_tp   = df['time_period'].min()
        max_tp   = df['time_period'].max()
        print(f"  {name:30s}: {len(df):>8,} rows | {n_months:>2} months | {min_tp} → {max_tp}")

        if n_months < expected_months and name not in EXEMPT:
            print(f"    [WARN] Only {n_months} months covered (expected {expected_months})")
            all_ok = False

    print()
    if all_ok:
        print("  All validations passed.")
    else:
        print("  Some warnings detected — review above.")

    # FK spot checks
    user_ids    = set(dfs['user'].user_id.tolist())
    account_ids = set(dfs['account'].account_id.tolist())

    for tbl, col, ref_set, ref_name in [
        ('user',                'account_id', account_ids, 'account'),
        ('seat',                'account_id', account_ids, 'account'),
        ('seat',                'user_id',    user_ids,    'user'),
        ('usage_event',         'account_id', account_ids, 'account'),
        ('usage_event',         'user_id',    user_ids,    'user'),
        ('support_ticket',      'account_id', account_ids, 'account'),
        ('support_ticket',      'user_id',    user_ids,    'user'),
        ('contract',            'account_id', account_ids, 'account'),
        ('mrr_movement',        'account_id', account_ids, 'account'),
        ('qbr',                 'account_id', account_ids, 'account'),
        ('team',                'account_id', account_ids, 'account'),
    ]:
        if tbl not in dfs or col not in dfs[tbl].columns:
            continue
        orphans = ~dfs[tbl][col].isin(ref_set)
        if orphans.sum() > 0:
            print(f"  [FK WARN] {tbl}.{col}: {orphans.sum()} orphan rows (missing in {ref_name})")

    print("─" * 70)


# ─────────────────────────── Save ───────────────────────────────────────────

def save_all(dfs):
    for name, df in dfs.items():
        path = OUTPUT_PATH / f"{name}.csv"
        df.to_csv(path, index=False)
        print(f"  Saved {name}.csv  ({len(df):,} rows)")


# ─────────────────────────── Main ───────────────────────────────────────────

def main():
    print("=" * 70)
    print("Tessera B2B SaaS — Data Simulation")
    print(f"Range: {SIM_START.date()} → {SIM_END.date()} | Seed: 42")
    print("=" * 70)

    print("\n[1] DimCSM")
    csm_df = generate_dim_csm()

    print("[2] Plan")
    plan_df = generate_plan()

    print("[3] Campaign")
    campaign_df = generate_campaign()

    print("[3b] Creative")
    creative_df = generate_creative(campaign_df)

    print("[4] Account")
    account_df = generate_account(plan_df, csm_df)

    print("[5] Cohort (initial)")
    cohort_df = generate_cohort()

    print("[6] User")
    user_df = generate_user(account_df, cohort_df)

    print("[6b] Updating cohort counts")
    cohort_df = update_cohort(cohort_df, user_df, account_df)

    print("[6c] Cohort (weekly)")
    cohort_weekly_df = generate_cohort_weekly(user_df)

    print("[7] Visitor")
    visitor_df = generate_visitor(campaign_df, user_df, creative_df)

    print("[8] Seat")
    seat_df = generate_seat(account_df, user_df, plan_df)

    print("[9] Contract")
    contract_df = generate_contract(account_df, plan_df)

    print("[9a] Updating account size bands")
    account_df = update_account_size_band(account_df, contract_df)

    print("[9b] Updating contract utilisation")
    contract_df = update_contract_utilisation(contract_df, seat_df)

    print("[9f] Contract monthly snapshot")
    contract_monthly_df = generate_contract_monthly(contract_df)

    print("[9c] Discount grants")
    discount_grant_df = generate_discount_grant(contract_df)

    print("[9d] Price change events")
    price_change_df = generate_price_change_event()

    print("[9e] Add-on attach")
    addon_attach_df = generate_addon_attach(contract_df)

    print("[10] UsageEvent")
    usage_event_df = generate_usage_event(user_df, account_df)

    print("[11] SupportTicket")
    support_ticket_df = generate_support_ticket(account_df, user_df)

    print("[11b] QBR")
    qbr_df = generate_qbr(account_df)

    print("[12] ExpansionOpportunity")
    expansion_df = generate_expansion_opportunity(account_df, user_df, plan_df)

    print("[12b] Team")
    team_df = generate_team(account_df)

    print("[12c] Expansion activity")
    expansion_activity_df = generate_expansion_activity(expansion_df)

    print("[13] HealthScoreSnapshot")
    health_df = generate_health_score_snapshot(account_df, usage_event_df, plan_df, support_ticket_df)

    print("[14] MRR movement")
    mrr_movement_df = generate_mrr_movement(account_df, contract_df, expansion_df, price_change_df, discount_grant_df)

    print("[15] Vendor")
    vendor_df = generate_vendor()

    print("[16] Headcount")
    headcount_df = generate_headcount()

    print("[17] Cost transaction")
    cost_transaction_df = generate_cost_transaction(account_df, contract_df, vendor_df, headcount_df)

    print("[18] Revenue line")
    revenue_line_df = generate_revenue_line(contract_df)

    print("[19] Cash")
    cash_df = generate_cash(cost_transaction_df, revenue_line_df)

    print("[20] Campaign (weekly)")
    campaign_weekly_df = generate_campaign_weekly(campaign_df)

    # Drop internal columns
    internal_cols = ['_churned_at', '_tier', '_icp_seg', '_is_paid']
    for col in internal_cols:
        if col in account_df.columns:
            account_df.drop(columns=[col], inplace=True)
        if col in user_df.columns:
            user_df.drop(columns=[col], inplace=True)

    dfs = {
        'dim_csm':               csm_df,
        'plan':                  plan_df,
        'campaign':              campaign_df,
        'creative':              creative_df,
        'account':               account_df,
        'cohort':                cohort_df,
        'cohort_weekly':         cohort_weekly_df,
        'user':                  user_df,
        'visitor':               visitor_df,
        'seat':                  seat_df,
        'contract':              contract_df,
        'contract_monthly':      contract_monthly_df,
        'discount_grant':        discount_grant_df,
        'price_change_event':    price_change_df,
        'addon_attach':          addon_attach_df,
        'usage_event':           usage_event_df,
        'support_ticket':        support_ticket_df,
        'qbr':                   qbr_df,
        'expansion_opportunity': expansion_df,
        'team':                  team_df,
        'expansion_activity':    expansion_activity_df,
        'health_score_snapshot': health_df,
        'mrr_movement':          mrr_movement_df,
        'vendor':                vendor_df,
        'headcount':             headcount_df,
        'cost_transaction':      cost_transaction_df,
        'revenue_line':          revenue_line_df,
        'cash':                  cash_df,
        'campaign_weekly':       campaign_weekly_df,
    }

    validate_all(dfs)

    print("\nSaving CSVs to ./output/ ...")
    save_all(dfs)

    print("\nDone. CSVs are ready for ClickHouse load.")
    print("  Next: python load_to_clickhouse.py")


if __name__ == '__main__':
    main()
