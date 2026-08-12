"""
Master reference data for Tessera B2B SaaS simulation.
All hardcoded constants consumed by simulation.py.
"""

from datetime import datetime

# ─────────────────────────── Simulation range ───────────────────────────────
# Extended one month (through September 2026) so every table covers 21 months,
# not 20 — September follows the same generation pattern as every other month.

SIM_START = datetime(2025, 1, 1)
SIM_END   = datetime(2026, 9, 30, 23, 59, 59)

TOTAL_ACCOUNTS  = 600
TARGET_USERS    = 3000
TARGET_EVENTS   = 300_000

# ─────────────────────────── Plan master (SCD-2 for Plus AND Business) ──────
# Two tiers now carry a price-change history (not just Plus) so Monetisation's
# elasticity/price-realisation metrics have more than one data point to work from.

PLAN_MASTER = [
    {
        'plan_id': 'plan_free',
        'plan_name': 'Free',
        'tier': 'Free',
        'list_price_per_seat': 0.0,
        'billing_period': 'monthly',
        'seat_limit': 3,
        'total_features_count': 8,
        'ai_addon_available': False,
        'is_self_serve': True,
        'effective_from': '2025-01-01',
        'effective_to': None,
    },
    {
        'plan_id': 'plan_plus_v1',
        'plan_name': 'Plus',
        'tier': 'Plus',
        'list_price_per_seat': 12.0,
        'billing_period': 'monthly',
        'seat_limit': 25,
        'total_features_count': 18,
        'ai_addon_available': False,
        'is_self_serve': True,
        'effective_from': '2025-01-01',
        'effective_to': '2025-06-30',
    },
    {
        'plan_id': 'plan_plus_v2',
        'plan_name': 'Plus',
        'tier': 'Plus',
        'list_price_per_seat': 15.0,
        'billing_period': 'monthly',
        'seat_limit': 25,
        'total_features_count': 20,
        'ai_addon_available': False,
        'is_self_serve': True,
        'effective_from': '2025-07-01',
        'effective_to': None,
    },
    {
        'plan_id': 'plan_business_v1',
        'plan_name': 'Business',
        'tier': 'Business',
        'list_price_per_seat': 35.0,
        'billing_period': 'annual',
        'seat_limit': 200,
        'total_features_count': 40,
        'ai_addon_available': True,
        'is_self_serve': False,
        'effective_from': '2025-01-01',
        'effective_to': '2025-09-30',
    },
    {
        'plan_id': 'plan_business_v2',
        'plan_name': 'Business',
        'tier': 'Business',
        'list_price_per_seat': 40.0,
        'billing_period': 'annual',
        'seat_limit': 200,
        'total_features_count': 42,
        'ai_addon_available': True,
        'is_self_serve': False,
        'effective_from': '2025-10-01',
        'effective_to': None,
    },
    {
        'plan_id': 'plan_enterprise',
        'plan_name': 'Enterprise',
        'tier': 'Enterprise',
        'list_price_per_seat': 75.0,
        'billing_period': 'annual',
        'seat_limit': 9999,
        'total_features_count': 60,
        'ai_addon_available': True,
        'is_self_serve': False,
        'effective_from': '2025-01-01',
        'effective_to': None,
    },
]

# Current active plan_id for each tier (used in account assignment)
PLAN_CURRENT = {
    'Free':       'plan_free',
    'Plus':       'plan_plus_v2',
    'Business':   'plan_business_v2',
    'Enterprise': 'plan_enterprise',
}

# ─────────────────────────── CSM master ─────────────────────────────────────

DIM_CSM_MASTER = [
    {'csm_id': 'CSM-001', 'csm_name': 'Sarah Chen',      'csm_email': 'sarah.chen@tessera.io',       'team': 'SMB',        'capacity_accounts': 60, 'segment_focus': 'SMB',        'active_from': '2023-01-01', 'active_to': None},
    {'csm_id': 'CSM-002', 'csm_name': 'James Miller',    'csm_email': 'james.miller@tessera.io',     'team': 'SMB',        'capacity_accounts': 60, 'segment_focus': 'SMB',        'active_from': '2023-01-01', 'active_to': None},
    {'csm_id': 'CSM-003', 'csm_name': 'Priya Sharma',    'csm_email': 'priya.sharma@tessera.io',     'team': 'SMB',        'capacity_accounts': 60, 'segment_focus': 'SMB',        'active_from': '2023-06-01', 'active_to': None},
    {'csm_id': 'CSM-004', 'csm_name': 'Tom Nguyen',      'csm_email': 'tom.nguyen@tessera.io',       'team': 'SMB',        'capacity_accounts': 60, 'segment_focus': 'SMB',        'active_from': '2024-01-15', 'active_to': None},
    {'csm_id': 'CSM-005', 'csm_name': 'Elena Rodriguez', 'csm_email': 'elena.rodriguez@tessera.io',  'team': 'MidMarket',  'capacity_accounts': 30, 'segment_focus': 'Mid-market', 'active_from': '2023-01-01', 'active_to': None},
    {'csm_id': 'CSM-006', 'csm_name': 'David Park',      'csm_email': 'david.park@tessera.io',       'team': 'MidMarket',  'capacity_accounts': 30, 'segment_focus': 'Mid-market', 'active_from': '2023-04-01', 'active_to': None},
    {'csm_id': 'CSM-007', 'csm_name': 'Laura Thompson',  'csm_email': 'laura.thompson@tessera.io',   'team': 'MidMarket',  'capacity_accounts': 30, 'segment_focus': 'Mid-market', 'active_from': '2023-09-01', 'active_to': None},
    {'csm_id': 'CSM-008', 'csm_name': 'Marcus Johnson',  'csm_email': 'marcus.johnson@tessera.io',   'team': 'MidMarket',  'capacity_accounts': 30, 'segment_focus': 'Mid-market', 'active_from': '2024-03-01', 'active_to': None},
    {'csm_id': 'CSM-009', 'csm_name': 'Aisha Williams',  'csm_email': 'aisha.williams@tessera.io',   'team': 'Enterprise', 'capacity_accounts': 15, 'segment_focus': 'Enterprise', 'active_from': '2023-01-01', 'active_to': None},
    {'csm_id': 'CSM-010', 'csm_name': "Ryan O'Brien",    'csm_email': 'ryan.obrien@tessera.io',       'team': 'Enterprise', 'capacity_accounts': 15, 'segment_focus': 'Enterprise', 'active_from': '2023-01-01', 'active_to': None},
    {'csm_id': 'CSM-011', 'csm_name': 'Nina Patel',      'csm_email': 'nina.patel@tessera.io',       'team': 'Enterprise', 'capacity_accounts': 15, 'segment_focus': 'Enterprise', 'active_from': '2023-07-01', 'active_to': None},
    {'csm_id': 'CSM-012', 'csm_name': 'Carlos Mendez',   'csm_email': 'carlos.mendez@tessera.io',    'team': 'Enterprise', 'capacity_accounts': 15, 'segment_focus': 'Enterprise', 'active_from': '2024-01-01', 'active_to': None},
]

# CSM by segment for assignment
CSM_BY_SEGMENT = {
    'SMB':        ['CSM-001', 'CSM-002', 'CSM-003', 'CSM-004'],
    'Mid-market': ['CSM-005', 'CSM-006', 'CSM-007', 'CSM-008'],
    'Enterprise': ['CSM-009', 'CSM-010', 'CSM-011', 'CSM-012'],
}

# ─────────────────────────── Channels ───────────────────────────────────────
# Renamed to the HTML's dimension dictionary values (Paid/Organic/Referral/Direct).
# `product_led` and `field_sales` (the old values) are not channel values in the
# HTML's taxonomy — they're represented via the `motion` dimension instead
# (see MOTION_TYPES below) and folded into Direct for channel-attribution purposes.
# CAMPAIGN_CHANNELS excludes Referral: referrals are word-of-mouth, not
# campaign-driven, so no Campaign row should ever claim a Referral channel.

CHANNELS = ['Paid', 'Organic', 'Referral', 'Direct']
CHANNEL_WEIGHTS = [0.30, 0.25, 0.15, 0.30]

CAMPAIGN_CHANNELS = ['Paid', 'Organic', 'Direct']
CAMPAIGN_CHANNEL_WEIGHTS = [0.40, 0.30, 0.30]

# UTM channel -> (source, medium) mapping
CHANNEL_UTM = {
    'Paid':     ('google',   'cpc'),
    'Organic':  ('google',   'organic'),
    'Direct':   ('direct',   'none'),
    'Referral': ('referral', 'referral'),
}

# ─────────────────────────── Motion (self-serve vs sales-led) ───────────────
# Unified across Acquisition/Activation/Monetisation/Expansion/Revenue engine.
# Stored as the HTML's literal display strings, not internal codes.

MOTION_TYPES = ['Self-serve', 'Sales-led']

# ─────────────────────────── Geography ──────────────────────────────────────
# Region labels renamed to the HTML's dimension dictionary (NA/EMEA/APAC/LATAM).
# Country coverage is unchanged — this is a label rename, not a geographic
# expansion (the "EMEA" label still only covers the same Europe countries).

GEOS = [
    {'country': 'United States', 'region': 'NA'},
    {'country': 'United Kingdom', 'region': 'EMEA'},
    {'country': 'Canada',         'region': 'NA'},
    {'country': 'Germany',        'region': 'EMEA'},
    {'country': 'Australia',      'region': 'APAC'},
    {'country': 'India',          'region': 'APAC'},
    {'country': 'France',         'region': 'EMEA'},
    {'country': 'Netherlands',    'region': 'EMEA'},
    {'country': 'Singapore',      'region': 'APAC'},
    {'country': 'Brazil',         'region': 'LATAM'},
]

GEO_WEIGHTS = [0.35, 0.15, 0.10, 0.08, 0.07, 0.07, 0.06, 0.05, 0.04, 0.03]

# ─────────────────────────── Industries ─────────────────────────────────────
# Replaced outright with the HTML's 5-value taxonomy (was 10 granular verticals).
# Weights aren't specified by the HTML — this distribution is a plan-flagged
# assumption, skewed toward SaaS/Tech consistent with the prior data's skew.

INDUSTRIES = ['SaaS / Tech', 'Financial svcs', 'Healthcare', 'Retail', 'Other']
INDUSTRY_WEIGHTS = [0.35, 0.20, 0.15, 0.15, 0.15]

# ─────────────────────────── ICP segments ───────────────────────────────────

# employee_count ranges and segment assignment
ICP_SEGMENTS = ['SMB', 'Mid-market', 'Enterprise']
ICP_WEIGHTS  = [0.50, 0.35, 0.15]

ICP_EMPLOYEE_RANGE = {
    'SMB':        (10,   200),
    'Mid-market': (200,  1000),
    'Enterprise': (1000, 15000),
}

ICP_REVENUE_RANGE = {
    'SMB':        (500_000,  10_000_000),
    'Mid-market': (10_000_000, 100_000_000),
    'Enterprise': (100_000_000, 2_000_000_000),
}

# Plan tier distribution per segment
SEGMENT_PLAN_DISTRIBUTION = {
    'SMB':        {'Free': 0.30, 'Plus': 0.45, 'Business': 0.25, 'Enterprise': 0.00},
    'Mid-market': {'Free': 0.10, 'Plus': 0.30, 'Business': 0.50, 'Enterprise': 0.10},
    'Enterprise': {'Free': 0.00, 'Plus': 0.05, 'Business': 0.35, 'Enterprise': 0.60},
}

# Lifecycle state distribution. 'Active' is split into Active/Core/Power (the
# HTML's "Core/Power user" tiering) so the existing EVENTS_PER_MONTH Core/Power
# buckets (below) are actually reachable — previously they were dead config.
LIFECYCLE_STATE_WEIGHTS = {
    'Active':       0.30,
    'Core':         0.15,
    'Power':        0.10,
    'Churned':      0.20,
    'Reactivated':  0.05,
    'Trial':        0.10,
    'Suspended':    0.05,
    'Qualified':    0.05,
}

# Users per account range by segment
USERS_PER_ACCOUNT = {
    'SMB':        (2, 4),
    'Mid-market': (3, 8),
    'Enterprise': (6, 15),
}

# ─────────────────────────── Account size / deal size / utilisation bands ───
# Real, independent bands (not 1:1 relabels of segment). Bucket edges are the
# HTML's own "illustrative" numbers, used only to decide where one banding
# category ends and the next begins — raw dimension values, not metrics.

ACCOUNT_SIZE_BAND_EDGES = [10, 50, 200]   # <10 seats, 10-50, 50-200, 200+
ACCOUNT_SIZE_BANDS      = ['<10 seats', '10–50', '50–200', '200+']

DEAL_SIZE_BAND_EDGES = [5_000, 25_000, 100_000]   # <$5k, $5-25k, $25-100k, $100k+ ACV
DEAL_SIZE_BANDS      = ['<$5k', '$5–25k', '$25–100k', '$100k+ ACV']

UTILISATION_BAND_EDGES = [0.5, 0.8, 1.0]   # <50%, 50-80%, 80-100%, at limit
UTILISATION_BANDS      = ['<50%', '50–80%', '80–100%', 'at limit']

# ─────────────────────────── Usage event types ──────────────────────────────

USAGE_EVENT_TYPES = [
    {'event_name': 'dashboard_viewed',      'feature_name': 'Dashboard',        'is_core_action': True,  'weight': 12},
    {'event_name': 'report_created',        'feature_name': 'Reporting',        'is_core_action': True,  'weight': 10},
    {'event_name': 'data_export',           'feature_name': 'Data Export',      'is_core_action': True,  'weight': 8},
    {'event_name': 'integration_connected', 'feature_name': 'Integrations',     'is_core_action': True,  'weight': 6},
    {'event_name': 'team_member_invited',   'feature_name': 'Team Management',  'is_core_action': True,  'weight': 5},
    {'event_name': 'workflow_created',      'feature_name': 'Workflows',        'is_core_action': True,  'weight': 7},
    {'event_name': 'api_called',            'feature_name': 'API',              'is_core_action': True,  'weight': 9},
    {'event_name': 'settings_updated',      'feature_name': 'Settings',         'is_core_action': False, 'weight': 4},
    {'event_name': 'notification_viewed',   'feature_name': 'Notifications',    'is_core_action': False, 'weight': 5},
    {'event_name': 'profile_updated',       'feature_name': 'Profile',          'is_core_action': False, 'weight': 3},
    {'event_name': 'search_performed',      'feature_name': 'Search',           'is_core_action': False, 'weight': 6},
    {'event_name': 'comment_added',         'feature_name': 'Collaboration',    'is_core_action': False, 'weight': 4},
    {'event_name': 'filter_applied',        'feature_name': 'Dashboard',        'is_core_action': False, 'weight': 5},
    {'event_name': 'alert_configured',      'feature_name': 'Alerts',           'is_core_action': True,  'weight': 4},
    {'event_name': 'permission_set',        'feature_name': 'Team Management',  'is_core_action': False, 'weight': 3},
    {'event_name': 'data_imported',         'feature_name': 'Data Import',      'is_core_action': True,  'weight': 6},
    {'event_name': 'template_used',         'feature_name': 'Templates',        'is_core_action': False, 'weight': 5},
    {'event_name': 'chart_created',         'feature_name': 'Reporting',        'is_core_action': False, 'weight': 6},
    {'event_name': 'pipeline_run',          'feature_name': 'Pipelines',        'is_core_action': True,  'weight': 7},
    {'event_name': 'log_viewed',            'feature_name': 'Audit Log',        'is_core_action': False, 'weight': 3},
    # Sales-led onboarding milestones (HTML: kickoff call -> workspace setup ->
    # data migration -> admin & permissions -> team rollout -> value moment).
    # Low weight: these are onboarding-specific, but reuse the same weighted
    # event-draw pool as everything else rather than a separate code path.
    {'event_name': 'kickoff_call',          'feature_name': 'Onboarding',       'is_core_action': True,  'weight': 2},
    {'event_name': 'workspace_setup',       'feature_name': 'Settings',         'is_core_action': True,  'weight': 2},
    {'event_name': 'data_migration',        'feature_name': 'Data Import',      'is_core_action': True,  'weight': 2},
    {'event_name': 'admin_permissions_set', 'feature_name': 'Team Management',  'is_core_action': True,  'weight': 2},
    {'event_name': 'team_rollout',          'feature_name': 'Team Management',  'is_core_action': True,  'weight': 2},
]

EVENT_NAMES  = [e['event_name']  for e in USAGE_EVENT_TYPES]
EVENT_WEIGHTS = [e['weight']     for e in USAGE_EVENT_TYPES]

# Onboarding step sequences, forked by motion (HTML: the self-serve PLG path
# and the sales-led CS-guided path are structurally different funnels, not one
# shared list). Both funnels culminate in a Value-moment, tracked separately
# as user.value_moment_at rather than as one more step name.
ONBOARDING_STEPS_SELF_SERVE = [
    'dashboard_viewed',        # setup
    'integration_connected',   # connect data
    'workflow_created',        # first object
    'team_member_invited',     # invite team
]

ONBOARDING_STEPS_SALES_LED = [
    'kickoff_call',
    'workspace_setup',
    'data_migration',
    'admin_permissions_set',
    'team_rollout',
]

# Events per month by lifecycle state: (min, max)
EVENTS_PER_MONTH = {
    'New':          (1, 4),
    'Qualified':    (2, 5),
    'Trial':        (3, 7),
    'Activated':    (4, 9),
    'Active':       (5, 11),
    'Core':         (8, 16),
    'Power':        (12, 22),
    'Reactivated':  (3, 8),
    'Suspended':    (0, 1),
    'Churned':      (0, 0),
}

# Lifecycle state -> event rate bucket mapping for users
USER_LIFECYCLE_TO_EVENT_BUCKET = {
    'Active':      'Active',
    'Core':        'Core',
    'Power':       'Power',
    'Churned':     'Churned',
    'Reactivated': 'Reactivated',
    'Trial':       'Trial',
    'Suspended':   'Suspended',
    'Qualified':   'Qualified',
}

# ─────────────────────────── Acquisition — qualify ───────────────────────────
# HTML's "qualify" step: fraction of signups that become qualified within a
# few days. Flat rate for simplicity (not channel-specific).

QUALIFY_RATE = 0.70

# ─────────────────────────── Support tickets ────────────────────────────────

TICKET_CATEGORIES = ['Bug', 'Feature Request', 'How-To', 'Billing', 'Performance', 'Integration']
TICKET_PRIORITIES = ['Low', 'Medium', 'High', 'Critical']
TICKET_PRIORITY_WEIGHTS = [0.35, 0.40, 0.18, 0.07]
TICKET_CHANNELS  = ['email', 'in_app', 'slack', 'phone']
TICKET_CHANNEL_WEIGHTS = [0.40, 0.35, 0.15, 0.10]

RESOLUTION_HOURS_BY_PRIORITY = {
    'Low':      (24, 120),
    'Medium':   (4,  48),
    'High':     (1,  12),
    'Critical': (0,   4),
}

# ─────────────────────────── QBR (Retention) ────────────────────────────────
# Quarterly business reviews — high-touch (non-self-serve) accounts only.

QBR_ELIGIBLE_TIERS = ['Business', 'Enterprise']

# ─────────────────────────── Expansion opportunities ────────────────────────

EXPANSION_TRIGGER_TYPES = ['limit_hit', 'utilization_high', 'addon_signal', 'team_growth', 'tier_upgrade']
EXPANSION_TYPES         = EXPANSION_TRIGGER_TYPES   # alias kept for backward compat
EXPANSION_MOTION_TYPES  = ['Self-serve', 'Sales-led']
EXPANSION_MOTION_WEIGHTS = [0.55, 0.45]
EXPANSION_STAGES = ['Identified', 'Qualifying', 'Proposed', 'Negotiating', 'Closed Won', 'Closed Lost']
EXPANSION_OUTCOMES = ['Won', 'Lost', 'Open']

# ─────────────────────────── Contracts ──────────────────────────────────────

BILLING_CYCLES = ['annual', 'monthly']
BILLING_CYCLE_WEIGHTS = [0.70, 0.30]

# Discount ranges by segment
DISCOUNT_BY_SEGMENT = {
    'SMB':        (0,  5),
    'Mid-market': (5,  15),
    'Enterprise': (10, 25),
}

# ─────────────────────────── Add-on catalog ─────────────────────────────────

ADDON_CATALOG = [
    {'addon_id': 'ADDON-01', 'addon_name': 'Advanced Analytics', 'monthly_price_usd': 40.0},
    {'addon_id': 'ADDON-02', 'addon_name': 'AI Assist',          'monthly_price_usd': 60.0},
    {'addon_id': 'ADDON-03', 'addon_name': 'Priority Support',   'monthly_price_usd': 25.0},
    {'addon_id': 'ADDON-04', 'addon_name': 'SSO / SCIM',         'monthly_price_usd': 30.0},
]

# ─────────────────────────── Monetisation — elasticity / WTP ────────────────
# No real-world signal exists for these in a simulation — they're computable
# only because we define the price-response relationship ourselves. Negative
# coefficients: more price-sensitive segments have larger-magnitude elasticity.

ELASTICITY_BY_SEGMENT = {
    'SMB':        -1.2,
    'Mid-market': -0.9,
    'Enterprise': -0.6,
}

WTP_MEAN_MULTIPLIER_BY_SEGMENT = {   # WTP as a multiplier of list price per seat
    'SMB':        1.15,
    'Mid-market': 1.30,
    'Enterprise': 1.50,
}
WTP_NOISE_STD = 0.20

# ─────────────────────────── Cost & Burn ────────────────────────────────────

COST_LINES = ['Cloud & infra', 'AI inference', 'People', 'Other']
FUNCTIONS  = ['R&D', 'S&M', 'G&A', 'CS']

VENDOR_MASTER = [
    {'vendor_id': 'VEN-001', 'vendor_name': 'AWS',        'cost_line': 'Cloud & infra'},
    {'vendor_id': 'VEN-002', 'vendor_name': 'Anthropic API', 'cost_line': 'AI inference'},
    {'vendor_id': 'VEN-003', 'vendor_name': 'Snowflake',  'cost_line': 'Cloud & infra'},
    {'vendor_id': 'VEN-004', 'vendor_name': 'Datadog',    'cost_line': 'Cloud & infra'},
    {'vendor_id': 'VEN-005', 'vendor_name': 'Stripe',     'cost_line': 'Other'},
    {'vendor_id': 'VEN-006', 'vendor_name': 'Segment',    'cost_line': 'Other'},
    # Payroll isn't vendor-invoiced, but cost_transaction needs a 'People' row
    # per period/function so cost_line has all 4 COST_LINES values in one table
    # instead of People being reachable only via the separate Headcount entity.
    {'vendor_id': 'VEN-007', 'vendor_name': 'Internal Payroll', 'cost_line': 'People'},
]

# Headcount by function, starting count (Jan 2025) and simple monthly growth
# rate. Simplified/formulaic cost model, not vendor-invoice-level realism.
# Calibrated against this sim's own revenue scale (~600 accounts, ARPU ~$45)
# so Net Profit/Runway trend like a plausible early-stage SaaS burn, not an
# arbitrary number disconnected from the rest of the generated data.
HEADCOUNT_START = {'R&D': 14, 'S&M': 10, 'G&A': 6, 'CS': 6}
HEADCOUNT_MONTHLY_GROWTH = {'R&D': 0.015, 'S&M': 0.020, 'G&A': 0.010, 'CS': 0.018}
AVG_MONTHLY_SALARY_USD_BY_FUNCTION = {'R&D': 12_000, 'S&M': 9_000, 'G&A': 8_000, 'CS': 7_000}

# Unit costs used to derive Cloud & infra / AI inference / Other cost lines.
# Formulaic by design: cost-to-serve scales with active-account volume, AI
# inference cost ramps over time to reflect growing AI-feature adoption.
CLOUD_COST_PER_ACCOUNT_USD = 6.0
CLOUD_COST_BASE_FIXED_USD  = 3_000.0
AI_INFERENCE_COST_PER_ACCOUNT_USD_START = 1.5
AI_INFERENCE_MONTHLY_RAMP  = 0.03   # AI cost per account grows ~3%/month
OTHER_COST_BASE_FIXED_USD  = 1_000.0
OTHER_COST_PCT_OF_MRR      = 0.02   # payments processing etc.

# ─────────────────────────── P&L — services revenue & cash ──────────────────

SERVICES_REVENUE_PCT_OF_MRR = 0.03   # one-time/services revenue as a small % of that month's MRR
OPENING_CASH_USD = 5_000_000.0       # starting cash position (e.g. a seed/Series A raise), needed for Runway

# ─────────────────────────── Visitor / UTM ──────────────────────────────────

LANDING_PAGES = [
    '/home', '/pricing', '/features', '/blog/saas-analytics',
    '/case-studies', '/integrations', '/demo', '/free-trial',
]

DEVICE_TYPES = ['desktop', 'mobile', 'tablet']
DEVICE_WEIGHTS = [0.62, 0.30, 0.08]

# ─────────────────────────── Account creation spread ────────────────────────

# Weights for monthly new account creation (Jan 2025 - Sep 2026, 21 months).
# Continues the existing taper by one more month rather than special-casing
# September as a partial/stub month. Renormalized below so weights sum to
# exactly 1.0 regardless of rounding in the raw list.
_RAW_ACCOUNT_MONTHLY_WEIGHTS = [
    0.065, 0.060, 0.055, 0.055, 0.050, 0.050,  # Jan-Jun 2025
    0.055, 0.055, 0.055, 0.055, 0.055, 0.055,  # Jul-Dec 2025
    0.045, 0.045, 0.045, 0.040, 0.040, 0.040,  # Jan-Jun 2026
    0.040, 0.035, 0.030,                        # Jul-Sep 2026
]
_total_w = sum(_RAW_ACCOUNT_MONTHLY_WEIGHTS)
ACCOUNT_MONTHLY_WEIGHTS = [w / _total_w for w in _RAW_ACCOUNT_MONTHLY_WEIGHTS]

# AM owner IDs (internal, not a FK table)
AM_OWNERS = [
    'AM-001', 'AM-002', 'AM-003', 'AM-004', 'AM-005',
    'AM-006', 'AM-007', 'AM-008',
]

# ─────────────────────────── User roles / departments ───────────────────────

USER_ROLES = [
    'Admin', 'Analyst', 'Developer', 'Manager',
    'Viewer', 'Executive', 'Operations',
]

USER_DEPARTMENTS = [
    'Engineering', 'Product', 'Data & Analytics', 'Operations',
    'Finance', 'Marketing', 'Sales', 'Executive',
]

# First names and last names for realistic user generation
FIRST_NAMES = [
    'James', 'Maria', 'David', 'Sarah', 'Michael', 'Jennifer', 'Robert', 'Emily',
    'William', 'Jessica', 'John', 'Ashley', 'Daniel', 'Amanda', 'Kevin', 'Stephanie',
    'Ryan', 'Nicole', 'Brandon', 'Lauren', 'Tyler', 'Rachel', 'Justin', 'Megan',
    'Eric', 'Kayla', 'Nathan', 'Brittany', 'Adam', 'Christina', 'Andrew', 'Diana',
    'Jordan', 'Grace', 'Alex', 'Priya', 'Carlos', 'Yuki', 'Mohamed', 'Aisha',
    'Wei', 'Fatima', 'Arjun', 'Elena', 'Lucas', 'Sofia', 'Raj', 'Nadia',
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
    'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
    'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson',
    'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson',
    'Walker', 'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen',
    'Hill', 'Flores', 'Green', 'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera',
    'Campbell', 'Mitchell', 'Carter', 'Roberts', 'Patel', 'Kim', 'Chen', 'Singh',
]

COMPANY_ADJECTIVES = [
    'Global', 'Dynamic', 'Smart', 'Fast', 'Bright', 'Clear', 'Bold', 'Agile',
    'Prime', 'Peak', 'Core', 'Edge', 'Next', 'Digital', 'Cloud', 'Open',
    'Rapid', 'Secure', 'Unified', 'Vertex', 'Apex', 'Nexus', 'Prism', 'Signal',
]

COMPANY_NOUNS = [
    'Solutions', 'Systems', 'Tech', 'Labs', 'Analytics', 'Ventures', 'Group',
    'Works', 'Platform', 'Studio', 'Partners', 'Consulting', 'Data', 'AI',
    'Cloud', 'Networks', 'Software', 'Dynamics', 'Innovations', 'Services',
    'Hub', 'Collective', 'Digital', 'Insights', 'Connect',
]
