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

-- ─────────────────────────── 3. campaign ────────────────────────────────────
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

-- ─────────────────────────── 4. account ─────────────────────────────────────
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
    account_size_band    String,
    lifecycle_state      String,
    current_plan_id      String,
    csm_owner_id         Nullable(String),
    am_owner_id          String,
    is_self_serve        UInt8,
    acquisition_channel  String,
    first_paid_at        Nullable(DateTime),
    created_at           DateTime,
    time_period          String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id);

-- ─────────────────────────── 5. cohort ──────────────────────────────────────
DROP TABLE IF EXISTS b2b_new.cohort;
CREATE TABLE b2b_new.cohort (
    cohort_id           String,
    cohort_period       String,
    cohort_start_date   DateTime,
    cohort_grain        String,
    channel_origin      String,
    plan_at_signup      String,
    segment             String,
    user_count          UInt32,
    activated_count     UInt32,
    activation_rate     Float64,
    time_period         String
) ENGINE = MergeTree()
ORDER BY (time_period, cohort_id);

-- ─────────────────────────── 6. user ────────────────────────────────────────
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
    onboarding_path  String,
    iq_segment       String,
    signup_at        DateTime,
    activated_at     Nullable(DateTime),
    last_active_at   DateTime,
    time_period      String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id, user_id);

-- ─────────────────────────── 7. visitor ─────────────────────────────────────
DROP TABLE IF EXISTS b2b_new.visitor;
CREATE TABLE b2b_new.visitor (
    visitor_id              String,
    campaign_id             String,
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
    converted_user_id       Nullable(String),
    est_account_size_band   String,
    est_industry            String,
    time_period             String
) ENGINE = MergeTree()
ORDER BY (time_period, visitor_id);

-- ─────────────────────────── 8. seat ────────────────────────────────────────
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

-- ─────────────────────────── 9. contract ────────────────────────────────────
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
    time_period              String
) ENGINE = MergeTree()
ORDER BY (time_period, account_id, contract_id);

-- ─────────────────────────── 10. usage_event ────────────────────────────────
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

-- ─────────────────────────── 11. support_ticket ─────────────────────────────
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

-- ─────────────────────────── 12. expansion_opportunity ──────────────────────
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

-- ─────────────────────────── 13. health_score_snapshot ──────────────────────
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
