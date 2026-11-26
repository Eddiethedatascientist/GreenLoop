import os

import psycopg
import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # reads .env when running locally; ignored on Streamlit Cloud

# Period formats for TO_CHAR (PostgreSQL). Constants only, never user input.
PERIOD_FORMATS = {
    "daily": "YYYY-MM-DD",
    "weekly": "IYYY-IW",
    "monthly": "YYYY-MM",
}


def get_connection():
    """Connect to the Supabase PostgreSQL database."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL is missing: set it in .env (local) "
            "or in Streamlit Secrets (deployed)."
        )
    # prepare_threshold=None: required for the Supabase transaction pooler
    # (pgbouncer), harmless for the session pooler.
    return psycopg.connect(database_url, prepare_threshold=None, connect_timeout=10)


@st.cache_data(ttl=10, show_spinner=False)
def fetch_all(query, params=None):
    """Execute a query and return all rows. Results are cached for 10 s so the
    dashboard does not open a new DB connection on every rerun."""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()


# ---------------------------------------------------------------------------
# Leaderboard / overview
# ---------------------------------------------------------------------------

def ranking_database():
    """Rows: (name, sessions, items, green points), best player first."""
    return fetch_all("""
        SELECT
            p.name,
            COUNT(DISTINCT se.event_id)::int,
            COALESCE(SUM(ei.quantity), 0)::int,
            COALESCE(p.total_point, 0)::int
        FROM person p
        LEFT JOIN sorting_event se ON p.person_id = se.person_id
        LEFT JOIN event_item ei ON se.event_id = ei.event_id
        GROUP BY p.person_id, p.name, p.total_point
        ORDER BY p.total_point DESC NULLS LAST;
    """)


def get_waste_decomposition():
    """Rows: (waste_name, total quantity)."""
    return fetch_all("""
        SELECT w.waste_name, SUM(e.quantity)::int
        FROM waste_type w
        JOIN event_item e ON w.waste_id = e.waste_id
        GROUP BY w.waste_name
        ORDER BY 2 DESC;
    """)


def get_best_material():
    """Name of the most sorted material, or None if there is no data."""
    summary = get_waste_decomposition()
    if not summary:
        return None
    return max(summary, key=lambda row: row[1] or 0)[0]


def get_activity_data():
    """Returns (daily, weekly, monthly); each is a list of (period, quantity).

    GROUP BY 1 / ORDER BY 1 refers to the first SELECT column, so the grouped
    expression can never differ from the selected one (that mismatch caused
    the GroupingError).
    """
    results = []
    for fmt in PERIOD_FORMATS.values():
        results.append(fetch_all(f"""
            SELECT TO_CHAR(e.time::timestamp, '{fmt}'), SUM(e.quantity)::int
            FROM event_item e
            GROUP BY 1
            ORDER BY 1;
        """))
    return tuple(results)


def get_activity_per_material():
    """Returns (daily, weekly, monthly); each is a list of
    (period, waste_name, quantity)."""
    results = []
    for fmt in PERIOD_FORMATS.values():
        results.append(fetch_all(f"""
            SELECT
                TO_CHAR(e.time::timestamp, '{fmt}'),
                w.waste_name,
                SUM(e.quantity)::int
            FROM event_item e
            JOIN waste_type w ON e.waste_id = w.waste_id
            GROUP BY 1, 2
            ORDER BY 1, 2;
        """))
    return tuple(results)


def get_recent_sorting():
    """Rows: (name, time_start, time_end), newest first (last 100 sessions)."""
    return fetch_all("""
        SELECT p.name, se.time_start, se.time_end
        FROM person p
        JOIN sorting_event se ON p.person_id = se.person_id
        ORDER BY se.time_start DESC
        LIMIT 100;
    """)


# ---------------------------------------------------------------------------
# Personal analytics
# ---------------------------------------------------------------------------

def search_participants(keyword):
    """Case-insensitive partial name search. Rows: (person_id, name, points)."""
    return fetch_all("""
        SELECT person_id, name, COALESCE(total_point, 0)::int
        FROM person
        WHERE name ILIKE %s
        ORDER BY name;
    """, (f"%{keyword}%",))


def get_person_summary(person_id):
    """Returns (sessions, items, breakdown) where breakdown is a list of
    (waste_name, quantity) sorted from most to least sorted."""
    stats = fetch_all("""
        SELECT
            COUNT(DISTINCT se.event_id)::int,
            COALESCE(SUM(ei.quantity), 0)::int
        FROM sorting_event se
        LEFT JOIN event_item ei ON se.event_id = ei.event_id
        WHERE se.person_id = %s;
    """, (person_id,))

    breakdown = fetch_all("""
        SELECT w.waste_name, SUM(ei.quantity)::int
        FROM sorting_event se
        JOIN event_item ei ON se.event_id = ei.event_id
        JOIN waste_type w ON ei.waste_id = w.waste_id
        WHERE se.person_id = %s
        GROUP BY w.waste_name
        ORDER BY 2 DESC;
    """, (person_id,))

    sessions, items = stats[0]  # an aggregate without GROUP BY always returns 1 row
    return sessions, items, breakdown


def get_personal_details(person_id):
    """Returns (daily, weekly, monthly) for one participant;
    each is a list of (period, quantity)."""
    results = []
    for fmt in PERIOD_FORMATS.values():
        results.append(fetch_all(f"""
            SELECT TO_CHAR(ei.time::timestamp, '{fmt}'), SUM(ei.quantity)::int
            FROM sorting_event se
            JOIN event_item ei ON se.event_id = ei.event_id
            WHERE se.person_id = %s
            GROUP BY 1
            ORDER BY 1;
        """, (person_id,)))
    return tuple(results)


def get_personal_histories(person_id):
    """Rows: (time_start, time_end, waste_name, quantity), newest first."""
    return fetch_all("""
        SELECT se.time_start, se.time_end, w.waste_name, ei.quantity
        FROM sorting_event se
        JOIN event_item ei ON se.event_id = ei.event_id
        JOIN waste_type w ON ei.waste_id = w.waste_id
        WHERE se.person_id = %s
        ORDER BY se.time_start DESC;
    """, (person_id,))
