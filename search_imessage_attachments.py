#!/usr/bin/env python3
"""Search the iMessage database for attachments with optional filters."""

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone


# iMessage stores timestamps as seconds since 2001-01-01 (Mac absolute time)
APPLE_EPOCH_OFFSET = 978307200


def apple_time_to_unix(apple_ts):
    """Convert Apple absolute time (nanoseconds) to a Unix timestamp."""
    # Newer macOS stores timestamps in nanoseconds
    if apple_ts > 1e12:
        apple_ts /= 1e9
    return apple_ts + APPLE_EPOCH_OFFSET


def parse_date(date_str):
    """Parse a date string (YYYY-MM-DD) into a Unix timestamp."""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return dt.timestamp()


def build_query(args):
    sql = """
        SELECT
            a.filename,
            a.mime_type,
            a.transfer_name,
            m.date,
            h.id AS contact
        FROM attachment a
        JOIN message_attachment_join maj ON maj.attachment_id = a.ROWID
        JOIN message m ON m.ROWID = maj.message_id
        LEFT JOIN handle h ON h.ROWID = m.handle_id
        WHERE a.filename IS NOT NULL
    """
    params = []

    if args.type:
        placeholders = ",".join("?" * len(args.type))
        type_conditions = []
        for t in args.type:
            MIME_CATEGORIES = {"image", "video", "audio", "application", "text"}
            if t.lower() in MIME_CATEGORIES or "/" in t:
                # treat as MIME type prefix (e.g. "image", "video", "image/jpeg")
                type_conditions.append("a.mime_type LIKE ?")
                params.append(f"{t}%")
            else:
                # treat as file extension (e.g. "pdf", "jpg")
                type_conditions.append("LOWER(a.filename) LIKE ?")
                params.append(f"%.{t.lstrip('.').lower()}")
        sql += f" AND ({' OR '.join(type_conditions)})"

    if args.after:
        after_apple = parse_date(args.after) - APPLE_EPOCH_OFFSET
        sql += " AND (CASE WHEN m.date > 1000000000000 THEN m.date / 1000000000.0 ELSE m.date END) >= ?"
        params.append(after_apple)

    if args.before:
        before_apple = parse_date(args.before) - APPLE_EPOCH_OFFSET
        sql += " AND (CASE WHEN m.date > 1000000000000 THEN m.date / 1000000000.0 ELSE m.date END) <= ?"
        params.append(before_apple)

    if args.contact:
        sql += " AND h.id LIKE ?"
        params.append(f"%{args.contact}%")

    if args.filename:
        sql += " AND LOWER(a.transfer_name) LIKE ?"
        params.append(f"%{args.filename.lower()}%")

    sql += " ORDER BY m.date DESC"
    return sql, params


def resolve_path(filename):
    """Expand the ~ in iMessage attachment paths to the actual home directory."""
    return os.path.expanduser(filename)


def main():
    parser = argparse.ArgumentParser(
        description="Search iMessage attachments in chat.db"
    )
    parser.add_argument(
        "--db",
        default=os.path.expanduser("~/Library/Messages/chat.db"),
        help="Path to chat.db (default: ~/Library/Messages/chat.db)",
    )
    parser.add_argument(
        "--type",
        nargs="+",
        metavar="EXT_OR_MIME",
        help="Filter by file extension (e.g. pdf jpg) or MIME type prefix (e.g. image video)",
    )
    parser.add_argument(
        "--after",
        metavar="YYYY-MM-DD",
        help="Only include attachments from messages sent on or after this date",
    )
    parser.add_argument(
        "--before",
        metavar="YYYY-MM-DD",
        help="Only include attachments from messages sent on or before this date",
    )
    parser.add_argument(
        "--contact",
        metavar="PHONE_OR_EMAIL",
        help="Filter by sender phone number or email (partial match)",
    )
    parser.add_argument(
        "--filename",
        metavar="KEYWORD",
        help="Filter by keyword in the attachment filename (case-insensitive)",
    )
    parser.add_argument(
        "--missing",
        action="store_true",
        help="Also show attachments whose files no longer exist on disk",
    )
    args = parser.parse_args()

    if not os.path.exists(args.db):
        sys.exit(f"Error: database not found at {args.db}")

    try:
        conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    except sqlite3.OperationalError as e:
        sys.exit(
            f"Error opening database: {e}\n"
            "Tip: grant Full Disk Access to Terminal in System Settings > Privacy & Security."
        )

    sql, params = build_query(args)

    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:
        sys.exit(f"Query failed: {e}")
    finally:
        conn.close()

    found = 0
    for filename, mime_type, transfer_name, date_raw, contact in rows:
        path = resolve_path(filename)
        if not args.missing and not os.path.exists(path):
            continue
        print(path)
        found += 1

    print(f"\n{found} attachment(s) found.", file=sys.stderr)


if __name__ == "__main__":
    main()
