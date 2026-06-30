"""
Master reference data for Tessera B2B SaaS simulation.
All hardcoded constants consumed by simulation.py.
"""

from datetime import datetime

# ─────────────────────────── Simulation range ───────────────────────────────

SIM_START = datetime(2025, 1, 1)
SIM_END   = datetime(2026, 8, 31, 23, 59, 59)

TOTAL_ACCOUNTS  = 600
TARGET_USERS    = 3000
TARGET_EVENTS   = 300_000

# ─────────────────────────── Plan master (SCD-2 for Plus) ───────────────────

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
        'plan_id': 'plan_business',
        'plan_name': 'Business',
        'tier': 'Business',
        'list_price_per_seat': 35.0,
        'billing_period': 'annual',
        'seat_limit': 200,
        'total_features_count': 40,
        'ai_addon_available': True,
        'is_self_serve': False,
        'effective_from': '2025-01-01',
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
    'Business':   'plan_business',
    'Enterprise': 'plan_enterprise',
}

# ─────────────────────────── CSM master ─────────────────────────────────────

DIM_CSM_MASTER = [
    {'csm_id': 'CSM-001', 'csm_name': 'Sarah Chen',      'csm_email': 'sarah.chen@tessera.io',       'team': 'SMB',        'capacity_accounts': 60, 'segment_focus': 'SMB',        'active_from': '2023-01-01', 'active_to': None},
    {'csm_id': 'CSM-002', 'csm_name': 'James Miller',    'csm_email': 'james.miller@tessera.io',     'team': 'SMB',        'capacity_accounts': 60, 'segment_focus': 'SMB',        'active_from': '2023-01-01', 'active_to': None},
    {'csm_id': 'CSM-003', 'csm_name': 'Priya Sharma',    'csm_email': 'priya.sharma@tessera.io',     'team': 'SMB',        'capacity_accounts': 60, 'segment_focus': 'SMB',        'active_from': '2023-06-01', 'active_to': None},
    {'csm_id': 'CSM-004', 'csm_name': 'Tom Nguyen',      'csm_email': 'tom.nguyen@tessera.io',       'team': 'SMB',        'capacity_accounts': 60, 'segment_focus': 'SMB',        'active_from': '2024-01-15', 'active_to': None},
    {'csm_id': 'CSM-005', 'csm_name': 'Elena Rodriguez', 'csm_email': 'elena.rodriguez@tessera.io',  'team': 'MidMarket',  'capacity_accounts': 30, 'segment_focus': 'Mid-Market', 'active_from': '2023-01-01', 'active_to': None},
    {'csm_id': 'CSM-006', 'csm_name': 'David Park',      'csm_email': 'david.park@tessera.io',       'team': 'MidMarket',  'capacity_accounts': 30, 'segment_focus': 'Mid-Market', 'active_from': '2023-04-01', 'active_to': None},
    {'csm_id': 'CSM-007', 'csm_name': 'Laura Thompson',  'csm_email': 'laura.thompson@tessera.io',   'team': 'MidMarket',  'capacity_accounts': 30, 'segment_focus': 'Mid-Market', 'active_from': '2023-09-01', 'active_to': None},
    {'csm_id': 'CSM-008', 'csm_name': 'Marcus Johnson',  'csm_email': 'marcus.johnson@tessera.io',   'team': 'MidMarket',  'capacity_accounts': 30, 'segment_focus': 'Mid-Market', 'active_from': '2024-03-01', 'active_to': None},
    {'csm_id': 'CSM-009', 'csm_name': 'Aisha Williams',  'csm_email': 'aisha.williams@tessera.io',   'team': 'Enterprise', 'capacity_accounts': 15, 'segment_focus': 'Enterprise', 'active_from': '2023-01-01', 'active_to': None},
    {'csm_id': 'CSM-010', 'csm_name': "Ryan O'Brien",    'csm_email': 'ryan.obrien@tessera.io',       'team': 'Enterprise', 'capacity_accounts': 15, 'segment_focus': 'Enterprise', 'active_from': '2023-01-01', 'active_to': None},
    {'csm_id': 'CSM-011', 'csm_name': 'Nina Patel',      'csm_email': 'nina.patel@tessera.io',       'team': 'Enterprise', 'capacity_accounts': 15, 'segment_focus': 'Enterprise', 'active_from': '2023-07-01', 'active_to': None},
    {'csm_id': 'CSM-012', 'csm_name': 'Carlos Mendez',   'csm_email': 'carlos.mendez@tessera.io',    'team': 'Enterprise', 'capacity_accounts': 15, 'segment_focus': 'Enterprise', 'active_from': '2024-01-01', 'active_to': None},
]

# CSM by segment for assignment
CSM_BY_SEGMENT = {
    'SMB':        ['CSM-001', 'CSM-002', 'CSM-003', 'CSM-004'],
    'Mid-Market': ['CSM-005', 'CSM-006', 'CSM-007', 'CSM-008'],
    'Enterprise': ['CSM-009', 'CSM-010', 'CSM-011', 'CSM-012'],
}

# ─────────────────────────── Channels ───────────────────────────────────────

CHANNELS = ['paid_search', 'content_seo', 'direct', 'product_led', 'field_sales']

CHANNEL_WEIGHTS = [0.25, 0.20, 0.20, 0.20, 0.15]

# ─────────────────────────── Geography ──────────────────────────────────────

GEOS = [
    {'country': 'United States', 'region': 'North America'},
    {'country': 'United Kingdom', 'region': 'Europe'},
    {'country': 'Canada',         'region': 'North America'},
    {'country': 'Germany',        'region': 'Europe'},
    {'country': 'Australia',      'region': 'APAC'},
    {'country': 'India',          'region': 'APAC'},
    {'country': 'France',         'region': 'Europe'},
    {'country': 'Netherlands',    'region': 'Europe'},
    {'country': 'Singapore',      'region': 'APAC'},
    {'country': 'Brazil',         'region': 'LATAM'},
]

GEO_WEIGHTS = [0.35, 0.15, 0.10, 0.08, 0.07, 0.07, 0.06, 0.05, 0.04, 0.03]

# ─────────────────────────── Industries ─────────────────────────────────────

INDUSTRIES = [
    'SaaS', 'FinTech', 'HealthTech', 'E-Commerce', 'MarTech',
    'EdTech', 'LegalTech', 'HRTech', 'Manufacturing', 'Professional Services',
]

INDUSTRY_WEIGHTS = [0.25, 0.15, 0.12, 0.10, 0.10, 0.08, 0.07, 0.06, 0.04, 0.03]

# ─────────────────────────── ICP segments ───────────────────────────────────

# employee_count ranges and segment assignment
ICP_SEGMENTS = ['SMB', 'Mid-Market', 'Enterprise']
ICP_WEIGHTS  = [0.50, 0.35, 0.15]

ICP_EMPLOYEE_RANGE = {
    'SMB':        (10,   200),
    'Mid-Market': (200,  1000),
    'Enterprise': (1000, 15000),
}

ICP_REVENUE_RANGE = {
    'SMB':        (500_000,  10_000_000),
    'Mid-Market': (10_000_000, 100_000_000),
    'Enterprise': (100_000_000, 2_000_000_000),
}

# Plan tier distribution per segment
SEGMENT_PLAN_DISTRIBUTION = {
    'SMB':        {'Free': 0.30, 'Plus': 0.45, 'Business': 0.25, 'Enterprise': 0.00},
    'Mid-Market': {'Free': 0.10, 'Plus': 0.30, 'Business': 0.50, 'Enterprise': 0.10},
    'Enterprise': {'Free': 0.00, 'Plus': 0.05, 'Business': 0.35, 'Enterprise': 0.60},
}

# Lifecycle state distribution
LIFECYCLE_STATE_WEIGHTS = {
    'Active':       0.55,
    'Churned':      0.20,
    'Reactivated':  0.05,
    'Trial':        0.10,
    'Suspended':    0.05,
    'Qualified':    0.05,
}

# Users per account range by segment
USERS_PER_ACCOUNT = {
    'SMB':        (2, 4),
    'Mid-Market': (3, 8),
    'Enterprise': (6, 15),
}

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
]

EVENT_NAMES  = [e['event_name']  for e in USAGE_EVENT_TYPES]
EVENT_WEIGHTS = [e['weight']     for e in USAGE_EVENT_TYPES]

ONBOARDING_STEPS = [
    'dashboard_viewed',
    'team_member_invited',
    'integration_connected',
    'workflow_created',
    'data_imported',
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

# Lifecycle state → event rate bucket mapping for users
USER_LIFECYCLE_TO_EVENT_BUCKET = {
    'Active':      'Active',
    'Churned':     'Churned',
    'Reactivated': 'Reactivated',
    'Trial':       'Trial',
    'Suspended':   'Suspended',
    'Qualified':   'Qualified',
}

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

# ─────────────────────────── Expansion opportunities ────────────────────────

EXPANSION_TRIGGER_TYPES = ['limit_hit', 'utilization_high', 'addon_signal', 'team_growth', 'tier_upgrade']
EXPANSION_TYPES         = EXPANSION_TRIGGER_TYPES   # alias kept for backward compat
EXPANSION_MOTION_TYPES  = ['plg_inapp', 'sales_assist']
EXPANSION_MOTION_WEIGHTS = [0.55, 0.45]
EXPANSION_STAGES = ['Identified', 'Qualifying', 'Proposed', 'Negotiating', 'Closed Won', 'Closed Lost']
EXPANSION_OUTCOMES = ['Won', 'Lost', 'Open']

# ─────────────────────────── Contracts ──────────────────────────────────────

BILLING_CYCLES = ['annual', 'monthly']
BILLING_CYCLE_WEIGHTS = [0.70, 0.30]

# Discount ranges by segment
DISCOUNT_BY_SEGMENT = {
    'SMB':        (0,  5),
    'Mid-Market': (5,  15),
    'Enterprise': (10, 25),
}

# ─────────────────────────── Visitor / UTM ──────────────────────────────────

LANDING_PAGES = [
    '/home', '/pricing', '/features', '/blog/saas-analytics',
    '/case-studies', '/integrations', '/demo', '/free-trial',
]

DEVICE_TYPES = ['desktop', 'mobile', 'tablet']
DEVICE_WEIGHTS = [0.62, 0.30, 0.08]

# ─────────────────────────── Account creation spread ────────────────────────

# Weights for monthly new account creation (Jan 2025 – Aug 2026, 20 months)
# Higher in early months, tapering off slightly
ACCOUNT_MONTHLY_WEIGHTS = [
    0.065, 0.060, 0.055, 0.055, 0.050, 0.050,  # Jan-Jun 2025
    0.055, 0.055, 0.055, 0.055, 0.055, 0.055,  # Jul-Dec 2025
    0.045, 0.045, 0.045, 0.040, 0.040, 0.040,  # Jan-Jun 2026
    0.040, 0.035,                               # Jul-Aug 2026
]

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
