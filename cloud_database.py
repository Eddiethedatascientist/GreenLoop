
import os
import psycopg
import streamlit as st

from dotenv import load_dotenv


load_dotenv()


def get_connection():
    """Connect to the Supabase PostgreSQL database."""

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        try:
            database_url = st.secrets["DATABASE_URL"]
        except Exception:
            database_url = None

    if not database_url:
        raise ValueError(
            "DATABASE_URL is missing. "
            "Configure it in Streamlit Secrets or your local .env file."
        )

    return psycopg.connect(database_url)


def fetch_all(query, params=None):
    """Execute a query and return all retrieved records."""

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()


def get_person_summary(person_id):
    """Retrieve points, sorting sessions, and sorted items for one person."""

    rows = fetch_all("""
        SELECT
            COALESCE(p.total_point, 0),
            COUNT(DISTINCT se.event_id),
            COALESCE(SUM(ei.quantity), 0)
        FROM person p
        LEFT JOIN sorting_event se
            ON p.person_id = se.person_id
        LEFT JOIN event_item ei
            ON se.event_id = ei.event_id
        WHERE p.person_id = %s
        GROUP BY p.person_id, p.total_point;
    """, (person_id,))

    return rows[0] if rows else (0, 0, 0)


def ranking_database():
    """Retrieve participants ranked by their total points."""

    return fetch_all("""
        SELECT
            p.name,
            COUNT(DISTINCT se.event_id),
            COALESCE(SUM(ei.quantity), 0),
            COALESCE(p.total_point, 0)
        FROM person p
        LEFT JOIN sorting_event se
            ON p.person_id = se.person_id
        LEFT JOIN event_item ei
            ON se.event_id = ei.event_id
        GROUP BY p.person_id, p.name, p.total_point
        ORDER BY p.total_point DESC;
    """)


def get_waste_decomposition():
    """Retrieve total sorted quantity for each waste type."""

    return fetch_all("""
        SELECT
            w.waste_name,
            COALESCE(SUM(e.quantity), 0)
        FROM waste_type w
        JOIN event_item e
            ON w.waste_id = e.waste_id
        GROUP BY w.waste_name
        ORDER BY SUM(e.quantity) DESC;
    """)


def get_best_material():
    """Return the waste type with the highest sorting quantity."""

    summary = get_waste_decomposition()

    if not summary:
        return None

    return max(
        summary,
        key=lambda x: x[1] or 0
    )[0]


def get_activity_data():
    """Retrieve daily, weekly, and monthly sorting activity."""

    daily = fetch_all("""
        SELECT
            TO_CHAR(time::timestamp, 'YYYY-MM-DD'),
            SUM(quantity)
        FROM event_item
        GROUP BY time::timestamp::date
        ORDER BY time::timestamp::date;
    """)

    weekly = fetch_all("""
        SELECT
            TO_CHAR(time::timestamp, 'IYYY-IW'),
            SUM(quantity)
        FROM event_item
        GROUP BY TO_CHAR(time::timestamp, 'IYYY-IW')
        ORDER BY TO_CHAR(time::timestamp, 'IYYY-IW');
    """)

    monthly = fetch_all("""
        SELECT
            TO_CHAR(time::timestamp, 'YYYY-MM'),
            SUM(quantity)
        FROM event_item
        GROUP BY TO_CHAR(time::timestamp, 'YYYY-MM')
        ORDER BY TO_CHAR(time::timestamp, 'YYYY-MM');
    """)

    return daily, weekly, monthly


def get_activity_per_material():
    """Retrieve sorting trends for each material over time."""

    daily = fetch_all("""
        SELECT
            TO_CHAR(e.time::timestamp, 'YYYY-MM-DD'),
            w.waste_name,
            SUM(e.quantity)
        FROM event_item e
        JOIN waste_type w
            ON e.waste_id = w.waste_id
        GROUP BY
            e.time::timestamp::date,
            w.waste_name
        ORDER BY
            e.time::timestamp::date;
    """)

    weekly = fetch_all("""
        SELECT
            TO_CHAR(e.time::timestamp, 'IYYY-IW'),
            w.waste_name,
            SUM(e.quantity)
        FROM event_item e
        JOIN waste_type w
            ON e.waste_id = w.waste_id
        GROUP BY
            TO_CHAR(e.time::timestamp, 'IYYY-IW'),
            w.waste_name
        ORDER BY
            TO_CHAR(e.time::timestamp, 'IYYY-IW');
    """)

    monthly = fetch_all("""
        SELECT
            TO_CHAR(e.time::timestamp, 'YYYY-MM'),
            w.waste_name,
            SUM(e.quantity)
        FROM event_item e
        JOIN waste_type w
            ON e.waste_id = w.waste_id
        GROUP BY
            TO_CHAR(e.time::timestamp, 'YYYY-MM'),
            w.waste_name
        ORDER BY
            TO_CHAR(e.time::timestamp, 'YYYY-MM');
    """)

    return daily, weekly, monthly


def get_recent_sorting():
    """Retrieve the latest sorting sessions."""

    return fetch_all("""
        SELECT
            p.name,
            se.time_start,
            se.time_end
        FROM person p
        JOIN sorting_event se
            ON p.person_id = se.person_id
        ORDER BY se.time_start DESC
        LIMIT 10;
    """)


def get_user_details():
    """Retrieve participant profiles, activity, and material statistics."""

    name_list = fetch_all("""
        SELECT
            person_id,
            name,
            total_point
        FROM person;
    """)

    data = fetch_all("""
        SELECT
            p.person_id,
            p.name,
            COUNT(DISTINCT se.event_id),
            COALESCE(SUM(ei.quantity), 0)
        FROM person p
        LEFT JOIN sorting_event se
            ON p.person_id = se.person_id
        LEFT JOIN event_item ei
            ON se.event_id = ei.event_id
        GROUP BY
            p.person_id,
            p.name
        ORDER BY p.person_id ASC;
    """)

    data_decomposition = fetch_all("""
        SELECT
            p.name,
            w.waste_name,
            COALESCE(SUM(ei.quantity), 0)
        FROM person p
        LEFT JOIN sorting_event se
            ON p.person_id = se.person_id
        LEFT JOIN event_item ei
            ON se.event_id = ei.event_id
        LEFT JOIN waste_type w
            ON ei.waste_id = w.waste_id
        WHERE w.waste_name IS NOT NULL
        GROUP BY
            p.name,
            w.waste_name
        ORDER BY SUM(ei.quantity);
    """)

    return name_list, data, data_decomposition


def get_personal_details(person_id):
    """Retrieve daily, weekly, and monthly activity for one participant."""

    daily = fetch_all("""
        SELECT
            TO_CHAR(ei.time::timestamp, 'YYYY-MM-DD'),
            SUM(ei.quantity)
        FROM person p
        JOIN sorting_event se
            ON p.person_id = se.person_id
        JOIN event_item ei
            ON se.event_id = ei.event_id
        WHERE p.person_id = %s
        GROUP BY ei.time::timestamp::date
        ORDER BY ei.time::timestamp::date;
    """, (person_id,))

    weekly = fetch_all("""
        SELECT
            TO_CHAR(ei.time::timestamp, 'IYYY-IW'),
            SUM(ei.quantity)
        FROM person p
        JOIN sorting_event se
            ON p.person_id = se.person_id
        JOIN event_item ei
            ON se.event_id = ei.event_id
        WHERE p.person_id = %s
        GROUP BY TO_CHAR(ei.time::timestamp, 'IYYY-IW')
        ORDER BY TO_CHAR(ei.time::timestamp, 'IYYY-IW');
    """, (person_id,))

    monthly = fetch_all("""
        SELECT
            TO_CHAR(ei.time::timestamp, 'YYYY-MM'),
            SUM(ei.quantity)
        FROM person p
        JOIN sorting_event se
            ON p.person_id = se.person_id
        JOIN event_item ei
            ON se.event_id = ei.event_id
        WHERE p.person_id = %s
        GROUP BY TO_CHAR(ei.time::timestamp, 'YYYY-MM')
        ORDER BY TO_CHAR(ei.time::timestamp, 'YYYY-MM');
    """, (person_id,))

    return daily, weekly, monthly


def get_personal_histories(person_id):
    """Retrieve sorting history for a specific participant."""

    return fetch_all("""
        SELECT
            se.time_start,
            se.time_end,
            w.waste_name,
            ei.quantity
        FROM person p
        JOIN sorting_event se
            ON p.person_id = se.person_id
        JOIN event_item ei
            ON se.event_id = ei.event_id
        JOIN waste_type w
            ON ei.waste_id = w.waste_id
        WHERE p.person_id = %s
        ORDER BY se.time_start DESC;
    """, (person_id,))


def get_all_participants():
    """Retrieve all participant IDs, names, and total points."""

    return fetch_all("""
        SELECT
            person_id,
            name,
            total_point
        FROM person
        ORDER BY person_id;
    """)
