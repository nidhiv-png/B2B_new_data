-- ============================================================
-- Tessera B2B SaaS — ClickHouse DDL
-- Database: b2b_new  |  Engine: MergeTree
-- DROP + CREATE ensures schema is always in sync with simulation
-- ============================================================

CREATE DATABASE IF NOT EXISTS b2b_new;

-- ─────────────────────────── 1. dim_csm ─────────────────────────────────────
DROP TABLE IF EXISTS b2b_new.dim_csm;
CREATE TABLE b2b_new.dim_csm (
    csm_id              String,
    csm_name            String,
    csm_email           String,
    team                String,
    capacity_accounts   UInt16,
    segment_focus       String,
    active_from         String,
    active_to           Nullable(String),
    time_period         String
) ENGINE = MergeTree()
ORDER BY (time_period, csm_id);

-- ─────────────────────────── 2. plan ────────────────────────────────────────
DROP TABLE IF EXISTS b2b_new.plan;
CREATE TABLE b2b_new.plan (
    plan_id               String,
    plan_name             String,
    tier                  String,
    list_price_per_seat   Float64,
    billing_period        String,
    seat_limit            UInt32,
    total_features_count  UInt16,
    ai_addon_available    UInt8,
    is_self_serve         UInt8,
    effective_from        String,
    effective_to          Nullable(String),
    time_period           String
) ENGINE = MergeTree()
ORDER BY (time_period, plan_id);

-- ─────────────────────────── 3. vendor (static catalog) ─────────────────────
DROP TABLE IF EXISTS b2b_new.vendor;
CREATE TABLE b2b_new.vendor (
    vendor_id    String,
    vendor_name  String,
    cost_line    String
) ENGINE = MergeTree()
ORDER BY (vendor_id);

-- ─────────────────────────── 4. campaign ────────────────────────────────────
DROP TABLE IF EXISTS b2b_new.campaign;
CREATE TABLE b2b_new.campaign (
    campaign_id         String,
    campaign_name       String,
    channel             String,
    geo_target          String,
    icp_segment_target  String,
    industry_target     String,
    start_at            DateTime,
    end_at              DateTime,
    budget_usd          Float64,
    impressions         UInt32,
    clicks              UInt32,
    conversions         UInt32,
    spend               Float64,
    cpc                 Float64,
    ctr                 Float64,
    time_period         String
) ENGINE = MergeTree()
ORDER BY (time_period, campaign_id);

-- ─────────────────────────── 5. creative ────────────────────────────────────
DROP TABLE IF EXISTS b2b_new.creative;
CREATE TABLE b2b_new.creative (
    creative_id     String,
    campaign_id     String,
    creative_name   String,
    format          String,
    created_at      DateTime,
    time_period     String
) ENGINE = MergeTree()
ORDER BY (time_period, campaign_id, creative_id);

-- ─────────────────────────── 6. account ─────────────────────────────────────
DROP TABLE IF EXISTS b2b_new.account;
CREATE TABLE b2b_new.account (
    account_id           String,
    account_name         String,
    industry             String,
    employee_count       UInt32,
    annual_revenue_usd   UInt64,
    geo                  String,
    region               String,
    segment              String,
    motion               String,
    account_size_band    String,
    lifecycle_state      String,
    current_plan_id      String,
    csm_owner_id         Nullable(String),
    am_owner_id          String,
    is_self_serve        UInt8,
    acquisition_channel  String,
    willingness_to_pay_usd_per_seat Float64,
    first_paid_at        Nullable(DateTime),
    created_at           DateTime,
    time_period          String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id);

-- ─────────────────────────── 7. cohort (monthly) ────────────────────────────
DROP TABLE IF EXISTS b2b_new.cohort;
CREATE TABLE b2b_new.cohort (
    cohort_id           String,
    cohort_period       String,
    cohort_start_date   DateTime,
    cohort_grain        String,
    channel_origin      String,
    plan_at_signup      String,
    segment             String,
    activation_rate     Float64,
    time_period         String,
    user_count          UInt32,
    activated_count     UInt32
) ENGINE = MergeTree()
ORDER BY (time_period, cohort_id);

-- ─────────────────────────── 8. cohort_weekly ───────────────────────────────
DROP TABLE IF EXISTS b2b_new.cohort_weekly;
CREATE TABLE b2b_new.cohort_weekly (
    cohort_id           String,
    cohort_period       String,
    cohort_grain        String,
    channel_origin      String,
    user_count          UInt32,
    activated_count     UInt32,
    activation_rate     Float64,
    time_period         String
) ENGINE = MergeTree()
ORDER BY (time_period, cohort_id);

-- ─────────────────────────── 9. user ────────────────────────────────────────
DROP TABLE IF EXISTS b2b_new.user;
CREATE TABLE b2b_new.user (
    user_id          String,
    account_id       String,
    cohort_id        Nullable(String),
    full_name        String,
    email            String,
    role             String,
    department       String,
    is_admin         UInt8,
    lifecycle_state  String,
    channel_origin   String,
    motion           String,
    iq_segment       String,
    signup_at        DateTime,
    activated_at     Nullable(DateTime),
    value_moment_at  Nullable(DateTime),
    last_active_at   DateTime,
    time_period      String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id, user_id);

-- ─────────────────────────── 10. visitor ────────────────────────────────────
DROP TABLE IF EXISTS b2b_new.visitor;
CREATE TABLE b2b_new.visitor (
    visitor_id              String,
    campaign_id             Nullable(String),
    creative_id             Nullable(String),
    anonymous_id            String,
    channel                 String,
    source                  String,
    medium                  String,
    geo                     String,
    lp_url                  String,
    device_type             String,
    page_views              UInt16,
    session_count           UInt16,
    first_seen_at           DateTime,
    last_seen_at            DateTime,
    did_signup              UInt8,
    signup_at               Nullable(DateTime),
    is_qualified            UInt8,
    qualified_at            Nullable(DateTime),
    converted_user_id       Nullable(String),
    est_account_size_band   String,
    est_industry            String,
    time_period             String
) ENGINE = MergeTree()
ORDER BY (time_period, visitor_id);

-- ─────────────────────────── 11. seat ───────────────────────────────────────
DROP TABLE IF EXISTS b2b_new.seat;
CREATE TABLE b2b_new.seat (
    seat_id         String,
    account_id      String,
    user_id         String,
    plan_id         String,
    seat_status     String,
    seat_mrr        Float64,
    billing_cycle   String,
    is_paid         UInt8,
    activated_at    DateTime,
    churned_at      Nullable(DateTime),
    time_period     String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id, seat_id);

-- ─────────────────────────── 12. contract ───────────────────────────────────
DROP TABLE IF EXISTS b2b_new.contract;
CREATE TABLE b2b_new.contract (
    contract_id              String,
    account_id               String,
    plan_id                  String,
    status                   String,
    seat_count               UInt32,
    mrr                      Float64,
    arr                      Float64,
    billing_cycle            String,
    start_at                 DateTime,
    end_at                   DateTime,
    renewal_at               DateTime,
    discount_pct             UInt8,
    realized_price_per_seat  Float64,
    addon_mrr                Float64,
    deal_size_band           String,
    time_period              String,
    seats_used               UInt32,
    seat_utilisation_pct     Float64,
    utilisation_band         String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id, contract_id);

-- ─────────────────────────── 13. discount_grant ─────────────────────────────
DROP TABLE IF EXISTS b2b_new.discount_grant;
CREATE TABLE b2b_new.discount_grant (
    grant_id      String,
    contract_id   String,
    account_id    String,
    discount_pct  UInt8,
    granted_at    DateTime,
    time_period   String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id, grant_id);

-- ─────────────────────────── 14. price_change_event ─────────────────────────
DROP TABLE IF EXISTS b2b_new.price_change_event;
CREATE TABLE b2b_new.price_change_event (
    price_change_id     String,
    plan_tier            String,
    old_price_per_seat   Float64,
    new_price_per_seat   Float64,
    effective_at         DateTime,
    time_period          String
) ENGINE = MergeTree()
ORDER BY (time_period, plan_tier);

-- ─────────────────────────── 15. addon_attach ───────────────────────────────
DROP TABLE IF EXISTS b2b_new.addon_attach;
CREATE TABLE b2b_new.addon_attach (
    attach_id     String,
    contract_id   String,
    account_id    String,
    addon_id      String,
    addon_name    String,
    addon_mrr     Float64,
    attached_at   DateTime,
    time_period   String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id, attach_id);

-- ─────────────────────────── 16. usage_event ────────────────────────────────
DROP TABLE IF EXISTS b2b_new.usage_event;
CREATE TABLE b2b_new.usage_event (
    event_id              String,
    user_id               String,
    account_id            String,
    event_name            String,
    feature_name          String,
    is_core_action        UInt8,
    onboarding_step_name  Nullable(String),
    session_id            String,
    platform              String,
    occurred_at           DateTime,
    time_period           String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id, occurred_at, event_id);

-- ─────────────────────────── 17. support_ticket ─────────────────────────────
DROP TABLE IF EXISTS b2b_new.support_ticket;
CREATE TABLE b2b_new.support_ticket (
    ticket_id           String,
    account_id          String,
    user_id             String,
    subject             String,
    category            String,
    severity            String,
    status              String,
    channel             String,
    opened_at           DateTime,
    resolved_at         Nullable(DateTime),
    resolution_hours    Nullable(Float64),
    csat_score          Nullable(UInt8),
    time_period         String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id, opened_at, ticket_id);

-- ─────────────────────────── 18. qbr ────────────────────────────────────────
DROP TABLE IF EXISTS b2b_new.qbr;
CREATE TABLE b2b_new.qbr (
    qbr_id        String,
    account_id    String,
    csm_id        String,
    qbr_date      DateTime,
    time_period   String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id, qbr_id);

-- ─────────────────────────── 19. expansion_opportunity ──────────────────────
DROP TABLE IF EXISTS b2b_new.expansion_opportunity;
CREATE TABLE b2b_new.expansion_opportunity (
    opp_id               String,
    account_id           String,
    owner_csm_id         Nullable(String),
    trigger_type         String,
    motion_type          String,
    upsell_status        String,
    expected_mrr_uplift  Float64,
    seats_eligible       UInt32,
    current_seats        UInt32,
    proposed_seats       UInt32,
    current_plan_id      String,
    proposed_plan_id     String,
    identified_at        DateTime,
    closed_at            Nullable(DateTime),
    outcome              String,
    time_period          String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id, opp_id);

-- ─────────────────────────── 20. team ───────────────────────────────────────
DROP TABLE IF EXISTS b2b_new.team;
CREATE TABLE b2b_new.team (
    team_id       String,
    account_id    String,
    team_name     String,
    created_at    DateTime,
    time_period   String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id, team_id);

-- ─────────────────────────── 21. expansion_activity ─────────────────────────
DROP TABLE IF EXISTS b2b_new.expansion_activity;
CREATE TABLE b2b_new.expansion_activity (
    activity_id     String,
    opp_id          String,
    account_id      String,
    activity_type   String,
    occurred_at     DateTime,
    time_period     String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id, activity_id);

-- ─────────────────────────── 22. health_score_snapshot ──────────────────────
DROP TABLE IF EXISTS b2b_new.health_score_snapshot;
CREATE TABLE b2b_new.health_score_snapshot (
    snapshot_id             String,
    account_id              String,
    week_start              DateTime,
    score                   Float64,
    dau_mau_ratio           Float64,
    core_actions_per_user   Float64,
    feature_breadth         Float64,
    support_tickets_open    UInt8,
    health_band             String,
    plan_tier               String,
    time_period             String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id, week_start);

-- ─────────────────────────── 23. mrr_movement (Revenue engine) ──────────────
DROP TABLE IF EXISTS b2b_new.mrr_movement;
CREATE TABLE b2b_new.mrr_movement (
    movement_id     String,
    account_id      String,
    movement_type   String,
    mrr_delta_usd   Float64,
    seats_delta     Int32,
    space           String,
    motion          String,
    segment         String,
    plan_tier       String,
    occurred_at     DateTime,
    time_period     String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id, movement_id);

-- ─────────────────────────── 24. headcount (Cost & Burn) ────────────────────
DROP TABLE IF EXISTS b2b_new.headcount;
CREATE TABLE b2b_new.headcount (
    headcount_id            String,
    function                String,
    headcount_count         UInt16,
    avg_monthly_salary_usd  UInt32,
    people_cost_usd         Float64,
    time_period             String
) ENGINE = MergeTree()
ORDER BY (time_period, function);

-- ─────────────────────────── 25. cost_transaction (Cost & Burn) ─────────────
DROP TABLE IF EXISTS b2b_new.cost_transaction;
CREATE TABLE b2b_new.cost_transaction (
    cost_id        String,
    vendor_id      String,
    vendor_name    String,
    cost_line      String,
    function       String,
    amount_usd     Float64,
    occurred_at    DateTime,
    time_period    String
) ENGINE = MergeTree()
ORDER BY (time_period, vendor_id, cost_id);

-- ─────────────────────────── 26. revenue_line (P&L) ─────────────────────────
DROP TABLE IF EXISTS b2b_new.revenue_line;
CREATE TABLE b2b_new.revenue_line (
    revenue_line_id   String,
    revenue_type      String,
    amount_usd        Float64,
    occurred_at       DateTime,
    time_period       String
) ENGINE = MergeTree()
ORDER BY (time_period, revenue_type);

-- ─────────────────────────── 27. cash (P&L) ──────────────────────────────────
DROP TABLE IF EXISTS b2b_new.cash;
CREATE TABLE b2b_new.cash (
    cash_id            String,
    time_period        String,
    as_of              DateTime,
    opening_cash_usd   Float64,
    net_change_usd     Float64,
    cash_balance_usd   Float64
) ENGINE = MergeTree()
ORDER BY (time_period);

-- ─────────────────────────── 28. campaign_weekly ────────────────────────────
DROP TABLE IF EXISTS b2b_new.campaign_weekly;
CREATE TABLE b2b_new.campaign_weekly (
    campaign_id   String,
    week_start    DateTime,
    channel       String,
    impressions   UInt32,
    clicks        UInt32,
    conversions   UInt32,
    spend         Float64,
    time_period   String
) ENGINE = MergeTree()
ORDER BY (time_period, campaign_id, week_start);
