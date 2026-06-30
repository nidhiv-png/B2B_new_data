"""
Tessera B2B SaaS — Data Simulation
Generates 13 CSV files (Jan 2025 – Aug 2026) and saves them to ./output/
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
    CHANNELS, CHANNEL_WEIGHTS,
    GEOS, GEO_WEIGHTS,
    INDUSTRIES, INDUSTRY_WEIGHTS,
    ICP_SEGMENTS, ICP_WEIGHTS,
    ICP_EMPLOYEE_RANGE, ICP_REVENUE_RANGE,
    SEGMENT_PLAN_DISTRIBUTION, LIFECYCLE_STATE_WEIGHTS,
    USERS_PER_ACCOUNT,
    USAGE_EVENT_TYPES, EVENT_NAMES, EVENT_WEIGHTS,
    ONBOARDING_STEPS, EVENTS_PER_MONTH, USER_LIFECYCLE_TO_EVENT_BUCKET,
    TICKET_CATEGORIES, TICKET_PRIORITIES, TICKET_PRIORITY_WEIGHTS,
    TICKET_CHANNELS, TICKET_CHANNEL_WEIGHTS, RESOLUTION_HOURS_BY_PRIORITY,
    EXPANSION_TYPES, EXPANSION_STAGES, EXPANSION_MOTION_TYPES, EXPANSION_MOTION_WEIGHTS,
    BILLING_CYCLES, BILLING_CYCLE_WEIGHTS, DISCOUNT_BY_SEGMENT,
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

MONTH_RANGE = pd.date_range('2025-01-01', '2026-08-01', freq='MS')   # 20 months

# UTM channel → (source, medium) mapping
CHANNEL_UTM = {
    'paid_search':  ('google',    'cpc'),
    'content_seo':  ('google',    'organic'),
    'direct':       ('direct',    'none'),
    'product_led':  ('tessera',   'product'),
    'field_sales':  ('outbound',  'email'),
}

# Account size band by ICP segment (consistent with visitor est_account_size_band)
SEGMENT_SIZE_BAND = {'SMB': 'small', 'Mid-Market': 'medium', 'Enterprise': 'large'}

ONBOARDING_PATHS = ['standard', 'guided', 'self_serve']


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
    """Random datetime, biased toward business hours (08:00–20:00)."""
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


# ─────────────────────────── 1. DimCSM ──────────────────────────────────────

def generate_dim_csm():
    """Monthly snapshot: one row per CSM per active month (Jan 2025 – Aug 2026)."""
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
    sim_end_month = pd.Timestamp('2026-08-01')

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
    rows = []
    cid = 1
    for month_dt in MONTH_RANGE:
        month_s = month_dt.to_pydatetime()
        month_e = month_end(month_s)
        for _ in range(4):
            channel  = weighted_choice(CHANNELS, CHANNEL_WEIGHTS)
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
                'campaign_name':       f'{channel.replace("_"," ").title()} {industry} {month_s.strftime("%b%Y")}',
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


# ─────────────────────────── 4. Account ─────────────────────────────────────

def generate_account(plan_df, csm_df):
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

            tier_options   = list(SEGMENT_PLAN_DISTRIBUTION[icp_seg].keys())
            tier_wts       = list(SEGMENT_PLAN_DISTRIBUTION[icp_seg].values())
            tier           = weighted_choice(tier_options, tier_wts)
            current_plan_id = PLAN_CURRENT[tier]

            is_self_serve = tier in ('Free', 'Plus')
            is_paid       = tier != 'Free'

            emp_lo, emp_hi = ICP_EMPLOYEE_RANGE[icp_seg]
            rev_lo, rev_hi = ICP_REVENUE_RANGE[icp_seg]
            employee_count = random.randint(emp_lo, emp_hi)
            annual_revenue = random.randint(rev_lo, rev_hi)
            account_size_band = SEGMENT_SIZE_BAND[icp_seg]

            csm_id = None
            if not is_self_serve:
                pool = CSM_BY_SEGMENT.get(icp_seg, CSM_BY_SEGMENT['SMB'])
                csm_id = random.choice(pool)

            lifecycle_options = list(LIFECYCLE_STATE_WEIGHTS.keys())
            lifecycle_wts     = list(LIFECYCLE_STATE_WEIGHTS.values())
            lifecycle_state   = weighted_choice(lifecycle_options, lifecycle_wts)

            created_at  = rand_business_dt(month_s, month_e)
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
                'account_size_band':  account_size_band,
                'lifecycle_state':    lifecycle_state,
                'current_plan_id':    current_plan_id,
                'csm_owner_id':       csm_id,
                'am_owner_id':        random.choice(AM_OWNERS),
                'is_self_serve':      is_self_serve,
                'acquisition_channel': channel,
                'first_paid_at':      fmt(first_paid_at),
                'created_at':         fmt(created_at),
                'time_period':        month_s.strftime('%Y-%m'),
                '_churned_at':        fmt(_churned_at),
                '_tier':              tier,
                '_icp_seg':           icp_seg,
                '_is_paid':           is_paid,
            })

    return pd.DataFrame(rows)


# ─────────────────────────── 5. Cohort ──────────────────────────────────────

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

        lo, hi = USERS_PER_ACCOUNT.get(icp_seg, (2, 6))
        n_users = random.randint(lo, hi)

        for u_idx in range(n_users):
            signup_at = created_at + timedelta(hours=random.randint(0, 168))
            signup_at = min(signup_at, SIM_END - timedelta(days=1))

            cohort_period = signup_at.strftime('%Y-%m')
            cohort_id     = cohort_lookup.get((cohort_period, channel),
                                              cohort_lookup.get((cohort_period, 'direct'), None))

            activated_at = None
            user_lifecycle = lifecycle
            if lifecycle in ('Active', 'Reactivated', 'Core', 'Power'):
                days_to_activate = random.randint(1, 30)
                activated_at = signup_at + timedelta(days=days_to_activate)
                if activated_at > SIM_END:
                    activated_at = None

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
                'onboarding_path':  random.choice(ONBOARDING_PATHS),
                'iq_segment':       icp_seg,
                'signup_at':        fmt(signup_at),
                'activated_at':     fmt(activated_at),
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

def generate_visitor(campaign_df, user_df):
    rows = []
    est_size_map = {'SMB': 'small', 'Mid-Market': 'medium', 'Enterprise': 'large'}

    paid_users = user_df[user_df['lifecycle_state'] != 'Churned'].sample(
        frac=0.65, random_state=42
    ).copy()

    # Converting visitors: one per paid user sample
    for _, usr in paid_users.iterrows():
        signup_at  = pd.to_datetime(usr['signup_at'])
        usr_period = usr['time_period']

        same_month = campaign_df[campaign_df['time_period'] == usr_period]
        if len(same_month) == 0:
            same_month = campaign_df

        camp = same_month.sample(1, random_state=None).iloc[0]

        first_seen = max(signup_at - timedelta(days=random.randint(1, 14)), SIM_START)
        last_seen  = max(signup_at - timedelta(hours=random.randint(1, 12)), SIM_START)

        utm_source, utm_medium = CHANNEL_UTM.get(camp['channel'], ('other', 'other'))

        rows.append({
            'visitor_id':            uid(),
            'campaign_id':           camp['campaign_id'],
            'anonymous_id':          uid(),
            'channel':               camp['channel'],
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
            'converted_user_id':     usr['user_id'],
            'est_account_size_band': est_size_map.get(camp['icp_segment_target'], 'small'),
            'est_industry':          camp['industry_target'],
            'time_period':           first_seen.strftime('%Y-%m'),
        })

    # Non-converting visitors (~3× converting)
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

        rows.append({
            'visitor_id':            uid(),
            'campaign_id':           camp['campaign_id'],
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
            'converted_user_id':     None,
            'est_account_size_band': est_size_map.get(camp['icp_segment_target'], 'small'),
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
    max_seat_map = {row['plan_id']: row['seat_limit']          for _, row in plan_df.iterrows()}

    paid_accounts = account_df[account_df['_is_paid'] == True].copy()

    rows = []
    for _, acc in paid_accounts.iterrows():
        plan_id    = acc['current_plan_id']
        price_psm  = price_map.get(plan_id, 35.0)
        icp_seg    = acc['_icp_seg']

        lo, hi  = DISCOUNT_BY_SEGMENT.get(icp_seg, (0, 10))
        discount = random.randint(lo, hi)

        billing = weighted_choice(BILLING_CYCLES, BILLING_CYCLE_WEIGHTS)

        seat_ranges = {'SMB': (2, 10), 'Mid-Market': (5, 50), 'Enterprise': (20, 200)}
        s_lo, s_hi  = seat_ranges.get(icp_seg, (2, 10))
        seats       = random.randint(s_lo, s_hi)

        net_price = price_psm * (1 - discount / 100)
        mrr       = round(net_price * seats, 2)
        arr       = round(mrr * 12, 2)

        start_at  = pd.to_datetime(acc['created_at'])
        if billing == 'annual':
            end_at    = start_at + timedelta(days=365)
        else:
            end_at    = start_at + timedelta(days=30)

        renewal_at   = end_at + timedelta(days=1)
        churned_dt   = parse_dt(acc['_churned_at'])
        realized_pps = round(mrr / seats, 2) if seats > 0 else 0.0
        addon_mrr    = round(random.uniform(0, 100), 2) if icp_seg == 'Enterprise' else 0.0

        status = 'active'
        if churned_dt and churned_dt < SIM_END:
            status = 'churned'
            end_at = min(end_at, churned_dt)

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
            'time_period':             start_at.strftime('%Y-%m'),
        })

        # Renewal contract if within sim window and account is active
        if billing == 'annual' and status == 'active' and pd.to_datetime(end_at) <= pd.to_datetime(fmt(SIM_END)):
            r_start      = pd.to_datetime(end_at) + timedelta(days=1)
            r_end        = r_start + timedelta(days=365)
            r_mrr        = round(mrr * random.uniform(1.0, 1.15), 2)
            r_arr        = round(r_mrr * 12, 2)
            r_realized   = round(r_mrr / seats, 2) if seats > 0 else 0.0
            rows.append({
                'contract_id':             uid(),
                'account_id':              acc['account_id'],
                'plan_id':                 plan_id,
                'status':                  'active',
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
                'time_period':             r_start.strftime('%Y-%m'),
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

        bucket = USER_LIFECYCLE_TO_EVENT_BUCKET.get(lifecycle, 'Active')
        lo, hi = EVENTS_PER_MONTH.get(bucket, (0, 0))
        if lo == 0 and hi == 0:
            continue

        last_active = acc_churn if acc_churn else SIM_END
        last_active = min(last_active, SIM_END)

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

            onboarding_eligible = (signup_at + timedelta(days=30)) > cur_month

            for _ in range(n_events):
                evt_name  = random.choices(evt_names, weights=evt_weights, k=1)[0]
                is_core   = evt_core_map[evt_name]
                feat_name = evt_feat_map[evt_name]

                evt_start = max(signup_at, cur_month)
                ts = rand_business_dt(
                    evt_start.to_pydatetime() if hasattr(evt_start, 'to_pydatetime') else evt_start,
                    m_end.to_pydatetime() if hasattr(m_end, 'to_pydatetime') else m_end
                )

                onboarding_step = None
                if onboarding_eligible and evt_name in ONBOARDING_STEPS:
                    onboarding_step = evt_name

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


# ─────────────────────────── 12. ExpansionOpportunity ───────────────────────

def generate_expansion_opportunity(account_df, user_df):
    rows = []

    acc_csm  = account_df.set_index('account_id')['csm_owner_id'].to_dict()
    acc_plan = account_df.set_index('account_id')['current_plan_id'].to_dict()
    acc_self_serve = account_df.set_index('account_id')['is_self_serve'].to_dict()

    cutoff_str = (pd.Timestamp(SIM_END) - pd.Timedelta(days=60)).strftime('%Y-%m-%d %H:%M:%S')
    eligible = account_df[
        (account_df['lifecycle_state'].isin(['Active', 'Reactivated'])) &
        (account_df['_is_paid'] == True) &
        (account_df['created_at'] <= cutoff_str)
    ].copy().reset_index(drop=True)

    eligible = eligible.sample(frac=0.80, random_state=42)

    plan_upgrade_map = {
        'plan_free':       ('plan_plus_v2', 15.0),
        'plan_plus_v2':    ('plan_business', 35.0),
        'plan_plus_v1':    ('plan_business', 35.0),
        'plan_business':   ('plan_enterprise', 75.0),
        'plan_enterprise': ('plan_enterprise', 75.0),
    }

    for _, acc in eligible.iterrows():
        n_opps  = random.randint(1, 3)
        created = pd.to_datetime(acc['created_at'])
        is_plg  = acc_self_serve.get(acc['account_id'], False)

        for _ in range(n_opps):
            trigger  = random.choice(EXPANSION_TYPES)
            motion   = 'plg_inapp' if is_plg else weighted_choice(EXPANSION_MOTION_TYPES, EXPANSION_MOTION_WEIGHTS)
            identified_at = rand_business_dt(
                (created + timedelta(days=60)).to_pydatetime() if hasattr(created + timedelta(days=60), 'to_pydatetime') else created + timedelta(days=60),
                min(SIM_END, (created + timedelta(days=300)).to_pydatetime() if hasattr(created + timedelta(days=300), 'to_pydatetime') else created + timedelta(days=300))
            )

            curr_plan = acc['current_plan_id']
            prop_plan, prop_price = plan_upgrade_map.get(curr_plan, (curr_plan, 35.0))

            curr_seats   = random.randint(2, 20)
            prop_seats   = curr_seats + random.randint(2, 15)
            seats_elig   = prop_seats - curr_seats
            exp_mrr      = round((prop_price - 35.0) * prop_seats + seats_elig * 35.0, 2)
            exp_mrr      = max(exp_mrr, 100.0)

            stage_roll = random.random()
            if stage_roll < 0.25:
                upsell_status = 'Closed Won'
                outcome       = 'Won'
                closed_at     = identified_at + timedelta(days=random.randint(14, 60))
            elif stage_roll < 0.40:
                upsell_status = 'Closed Lost'
                outcome       = 'Lost'
                closed_at     = identified_at + timedelta(days=random.randint(14, 45))
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

    all_weeks = pd.date_range('2025-01-06', '2026-08-25', freq='W-MON')

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

    base['health_band'] = pd.cut(
        base['score'],
        bins=[-0.01, 49.99, 74.99, 100.01],
        labels=['red', 'amber', 'green']
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


# ─────────────────────────── Validation ─────────────────────────────────────

def validate_all(dfs):
    print("\n── Validation ──────────────────────────────────────────────────────────")
    expected_months = 20
    all_ok = True

    for name, df in dfs.items():
        if 'time_period' not in df.columns:
            print(f"  [WARN] {name}: missing time_period column")
            all_ok = False
            continue

        n_months = df['time_period'].nunique()
        min_tp   = df['time_period'].min()
        max_tp   = df['time_period'].max()
        print(f"  {name:30s}: {len(df):>8,} rows | {n_months:>2} months | {min_tp} → {max_tp}")

        EXEMPT = {'expansion_opportunity'}
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
        ('user',           'account_id',  account_ids, 'account'),
        ('seat',           'account_id',  account_ids, 'account'),
        ('seat',           'user_id',     user_ids,    'user'),
        ('usage_event',    'account_id',  account_ids, 'account'),
        ('usage_event',    'user_id',     user_ids,    'user'),
        ('support_ticket', 'account_id',  account_ids, 'account'),
        ('support_ticket', 'user_id',     user_ids,    'user'),
        ('contract',       'account_id',  account_ids, 'account'),
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

    print("\n[1/13] DimCSM")
    csm_df = generate_dim_csm()

    print("[2/13] Plan")
    plan_df = generate_plan()

    print("[3/13] Campaign")
    campaign_df = generate_campaign()

    print("[4/13] Account")
    account_df = generate_account(plan_df, csm_df)

    print("[5/13] Cohort (initial)")
    cohort_df = generate_cohort()

    print("[6/13] User")
    user_df = generate_user(account_df, cohort_df)

    print("[6b]   Updating cohort counts")
    cohort_df = update_cohort(cohort_df, user_df, account_df)

    print("[7/13] Visitor")
    visitor_df = generate_visitor(campaign_df, user_df)

    print("[8/13] Seat")
    seat_df = generate_seat(account_df, user_df, plan_df)

    print("[9/13] Contract")
    contract_df = generate_contract(account_df, plan_df)

    print("[10/13] UsageEvent")
    usage_event_df = generate_usage_event(user_df, account_df)

    print("[11/13] SupportTicket")
    support_ticket_df = generate_support_ticket(account_df, user_df)

    print("[12/13] ExpansionOpportunity")
    expansion_df = generate_expansion_opportunity(account_df, user_df)

    print("[13/13] HealthScoreSnapshot")
    health_df = generate_health_score_snapshot(account_df, usage_event_df, plan_df, support_ticket_df)

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
        'account':               account_df,
        'cohort':                cohort_df,
        'user':                  user_df,
        'visitor':               visitor_df,
        'seat':                  seat_df,
        'contract':              contract_df,
        'usage_event':           usage_event_df,
        'support_ticket':        support_ticket_df,
        'expansion_opportunity': expansion_df,
        'health_score_snapshot': health_df,
    }

    validate_all(dfs)

    print("\nSaving CSVs to ./output/ ...")
    save_all(dfs)

    print("\nDone. CSVs are ready for ClickHouse load.")
    print("  Next: python load_to_clickhouse.py")


if __name__ == '__main__':
    main()
