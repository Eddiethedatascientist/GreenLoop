
import sqlite3
import os
import logging

import psycopg
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)


def sync_all():
    """
    Push local SQLite data to Supabase.
    Local SQLite remains the primary database.
    """

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        logging.warning("Cloud sync skipped: DATABASE_URL not found.")
        return False

    try:
        local_conn = sqlite3.connect("recycling.db")
        local_conn.row_factory = sqlite3.Row

        persons = local_conn.execute(
            "SELECT * FROM Person"
        ).fetchall()

        waste_types = local_conn.execute(
            "SELECT * FROM waste_type"
        ).fetchall()

        events = local_conn.execute(
            "SELECT * FROM sorting_event"
        ).fetchall()

        items = local_conn.execute(
            "SELECT * FROM event_item"
        ).fetchall()

        local_conn.close()

        with psycopg.connect(database_url, connect_timeout=10) as cloud:
            with cloud.cursor() as cur:

                # 1. Sync participants
                cur.executemany("""
                    INSERT INTO person
                        (person_id, name, total_point)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (person_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        total_point = EXCLUDED.total_point
                """, [
                    (p["person_id"], p["name"], p["total_point"])
                    for p in persons
                ])

                # 2. Sync waste types
                cur.executemany("""
                    INSERT INTO waste_type
                        (waste_id, waste_name, waste_point)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (waste_id) DO UPDATE SET
                        waste_name = EXCLUDED.waste_name,
                        waste_point = EXCLUDED.waste_point
                """, [
                    (w["waste_id"], w["waste_name"], w["waste_point"])
                    for w in waste_types
                ])

                # 3. Sync sorting sessions
                cur.executemany("""
                    INSERT INTO sorting_event
                        (event_id, person_id, time_start, time_end)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (event_id) DO UPDATE SET
                        person_id = EXCLUDED.person_id,
                        time_start = EXCLUDED.time_start,
                        time_end = EXCLUDED.time_end
                """, [
                    (e["event_id"], e["person_id"],
                     e["time_start"], e["time_end"])
                    for e in events
                ])

                # 4. Sync individual sorting records
                cur.executemany("""
                    INSERT INTO event_item
                        (item_id, event_id, waste_id, quantity, time)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (item_id) DO UPDATE SET
                        event_id = EXCLUDED.event_id,
                        waste_id = EXCLUDED.waste_id,
                        quantity = EXCLUDED.quantity,
                        time = EXCLUDED.time
                """, [
                    (i["item_id"], i["event_id"],
                     i["waste_id"], i["quantity"], i["time"])
                    for i in items
                ])

            cloud.commit()

        logging.info("GreenLoop cloud sync successful.")
        return True

    except Exception as e:
        logging.warning("GreenLoop cloud sync failed: %s", e)
        return False
