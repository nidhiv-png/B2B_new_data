"""
Tessera B2B SaaS — Load CSVs to ClickHouse
Connects to b2b_new, creates tables (if not exists), loads all 13 CSVs.
"""

import sys
from pathlib import Path

import pandas as pd
import clickhouse_connect

# ─────────────────────────── Config ─────────────────────────────────────────

CH_HOST     = '3.108.206.137'
CH_PORT     = 8123
CH_USER     = 'default'
CH_PASSWORD = 'default'
CH_DATABASE = 'b2b_new'

DDL_PATH    = Path(__file__).parent / 'schema' / 'clickhouse_ddl.sql'
OUTPUT_PATH = Path(__file__).parent / 'output'

# Table load order (respects FK dependency)
TABLE_ORDER = [
    'dim_csm',
    'plan',
    'vendor',
    'campaign',
    'creative',
    'account',
    'cohort',
    'cohort_weekly',
    'user',
    'visitor',
    'seat',
    'contract',
    'discount_grant',
    'price_change_event',
    'addon_attach',
    'usage_event',
    'support_ticket',
    'qbr',
    'expansion_opportunity',
    'team',
    'expansion_activity',
    'health_score_snapshot',
    'mrr_movement',
    'headcount',
    'cost_transaction',
    'revenue_line',
    'cash',
    'campaign_weekly',
]

# Columns that should be treated as Nullable (empty string / NaN → None)
NULLABLE_COLS = {
    'dim_csm':               ['active_to'],
    'plan':                  ['effective_to'],
    'vendor':                [],
    'account':               ['csm_owner_id', 'first_paid_at'],
    'cohort':                [],
    'cohort_weekly':         [],
    'user':                  ['cohort_id', 'activated_at', 'value_moment_at'],
    'visitor':               ['campaign_id', 'creative_id', 'signup_at', 'qualified_at', 'converted_user_id'],
    'seat':                  ['churned_at'],
    'contract':              [],
    'discount_grant':        [],
    'price_change_event':    [],
    'addon_attach':          [],
    'usage_event':           ['onboarding_step_name'],
    'support_ticket':        ['resolved_at', 'resolution_hours', 'csat_score'],
    'qbr':                   [],
    'expansion_opportunity': ['owner_csm_id', 'closed_at'],
    'team':                  [],
    'expansion_activity':    [],
    'health_score_snapshot': [],
    'mrr_movement':          [],
    'headcount':             [],
    'cost_transaction':      [],
    'revenue_line':          [],
    'cash':                  [],
    'campaign':              [],
    'creative':              [],
    'campaign_weekly':       [],
}

# Boolean columns stored as 0/1 in ClickHouse
BOOL_COLS = {
    'plan':    ['is_self_serve', 'ai_addon_available'],
    'account': ['is_self_serve'],
    'user':    ['is_admin'],
    'visitor': ['did_signup', 'is_qualified'],
    'seat':    ['is_paid'],
    'usage_event': ['is_core_action'],
}

# DateTime columns: must be parsed from string to datetime before insert
DATETIME_COLS = {
    'campaign':               ['start_at', 'end_at'],
    'creative':               ['created_at'],
    'account':                ['first_paid_at', 'created_at'],
    'cohort':                 ['cohort_start_date'],
    'user':                   ['signup_at', 'activated_at', 'value_moment_at', 'last_active_at'],
    'visitor':                ['first_seen_at', 'last_seen_at', 'signup_at', 'qualified_at'],
    'seat':                   ['activated_at', 'churned_at'],
    'contract':               ['start_at', 'end_at', 'renewal_at'],
    'discount_grant':         ['granted_at'],
    'price_change_event':     ['effective_at'],
    'addon_attach':           ['attached_at'],
    'usage_event':            ['occurred_at'],
    'support_ticket':         ['opened_at', 'resolved_at'],
    'qbr':                    ['qbr_date'],
    'expansion_opportunity':  ['identified_at', 'closed_at'],
    'team':                   ['created_at'],
    'expansion_activity':     ['occurred_at'],
    'health_score_snapshot':  ['week_start'],
    'mrr_movement':           ['occurred_at'],
    'cost_transaction':       ['occurred_at'],
    'revenue_line':           ['occurred_at'],
    'cash':                   ['as_of'],
    'campaign_weekly':        ['week_start'],
}

# pandas' default NA-string sniffing treats the literal string "NA" (used here
# as the region code for North America, per the HTML's own dimension naming)
# as a null marker. Without this override, every "NA" region would silently
# turn into a blank/None on the round-trip through read_csv.
_NA_VALUES_EXCLUDING_LITERAL_NA = [
    '', '#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan',
    '1.#IND', '1.#QNAN', '<NA>', 'N/A', 'NULL', 'NaN', 'None', 'n/a', 'nan', 'null',
]

# ─────────────────────────── Helpers ────────────────────────────────────────

def get_client_no_db():
    return clickhouse_connect.get_client(
        host=CH_HOST,
        port=CH_PORT,
        username=CH_USER,
        password=CH_PASSWORD,
    )

def get_client():
    return clickhouse_connect.get_client(
        host=CH_HOST,
        port=CH_PORT,
        username=CH_USER,
        password=CH_PASSWORD,
        database=CH_DATABASE,
    )

def run_ddl(client, ddl_path: Path):
    sql = ddl_path.read_text()
    statements = [s.strip() for s in sql.split(';') if s.strip()]
    for stmt in statements:
        if stmt:
            client.command(stmt)

def coerce_df(table: str, df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Parse DateTime columns: CSV strings → Python datetime (clickhouse-connect requires objects)
    for col in DATETIME_COLS.get(table, []):
        if col in df.columns:
            parsed = pd.to_datetime(df[col], errors='coerce')
            # Convert to Python datetime; NaT becomes None for nullable columns
            df[col] = [v.to_pydatetime() if pd.notna(v) else None for v in parsed]

    # Replace NaN with None for nullable columns
    nullable = NULLABLE_COLS.get(table, [])
    for col in nullable:
        if col in df.columns:
            df[col] = df[col].where(df[col].notna(), other=None)

    # Booleans → int
    bool_cols = BOOL_COLS.get(table, [])
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(int)

    return df

def load_table(client, table: str, csv_path: Path) -> int:
    df = pd.read_csv(csv_path, keep_default_na=False, na_values=_NA_VALUES_EXCLUDING_LITERAL_NA)
    df = coerce_df(table, df)

    # Truncate existing data before reload
    client.command(f'TRUNCATE TABLE IF EXISTS {CH_DATABASE}.{table}')

    # Insert
    client.insert_df(f'{CH_DATABASE}.{table}', df)
    return len(df)

# ─────────────────────────── Main ───────────────────────────────────────────

def main():
    print('=' * 60)
    print('Tessera B2B SaaS — ClickHouse Loader')
    print('=' * 60)

    # Step 1: Create database
    print(f'\n[1] Creating database {CH_DATABASE} if not exists...')
    try:
        client_root = get_client_no_db()
        client_root.command(f'CREATE DATABASE IF NOT EXISTS {CH_DATABASE}')
        print(f'    Database {CH_DATABASE} ready.')
    except Exception as e:
        print(f'    ERROR creating database: {e}')
        sys.exit(1)

    # Step 2: Run DDL
    print(f'\n[2] Running DDL from {DDL_PATH.name}...')
    try:
        client = get_client()
        run_ddl(client, DDL_PATH)
        print('    All tables created (IF NOT EXISTS).')
    except Exception as e:
        print(f'    ERROR running DDL: {e}')
        sys.exit(1)

    # Step 3: Load each CSV
    print(f'\n[3] Loading CSVs from ./output/ ...')
    print(f'    {"Table":<30} {"Rows":>10}')
    print(f'    {"-"*30} {"-"*10}')

    total_rows = 0
    errors = []

    for table in TABLE_ORDER:
        csv_path = OUTPUT_PATH / f'{table}.csv'
        if not csv_path.exists():
            print(f'    {"  [SKIP] " + table:<30} CSV not found')
            errors.append(table)
            continue
        try:
            n = load_table(client, table, csv_path)
            total_rows += n
            print(f'    {table:<30} {n:>10,}')
        except Exception as e:
            print(f'    {"  [ERROR] " + table:<30} {e}')
            errors.append(table)

    print(f'    {"─"*30} {"─"*10}')
    print(f'    {"TOTAL":<30} {total_rows:>10,}')

    # Step 4: Validate row counts
    print(f'\n[4] Validating row counts in ClickHouse...')
    print(f'    {"Table":<30} {"CSV":>10} {"ClickHouse":>12} {"Match":>6}')
    print(f'    {"-"*30} {"-"*10} {"-"*12} {"-"*6}')

    all_match = True
    for table in TABLE_ORDER:
        csv_path = OUTPUT_PATH / f'{table}.csv'
        if not csv_path.exists():
            continue
        try:
            csv_rows = len(pd.read_csv(csv_path))
            ch_rows  = client.command(f'SELECT count() FROM {CH_DATABASE}.{table}')
            match    = 'OK' if csv_rows == ch_rows else 'MISMATCH'
            if match == 'MISMATCH':
                all_match = False
            print(f'    {table:<30} {csv_rows:>10,} {ch_rows:>12,} {match:>6}')
        except Exception as e:
            print(f'    {table:<30} ERROR: {e}')
            all_match = False

    print()
    if all_match and not errors:
        print('  All tables loaded and verified successfully.')
        print(f'  Database: {CH_DATABASE}  |  Host: {CH_HOST}')
    else:
        if errors:
            print(f'  Tables with errors: {errors}')
        if not all_match:
            print('  Row count mismatches detected — check logs above.')

    print('\nDone.')


if __name__ == '__main__':
    main()
