import sqlite3
import os
import json
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "family_letters.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            gender TEXT DEFAULT '',
            birth_year TEXT DEFAULT '',
            death_year TEXT DEFAULT '',
            alias_name TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS letters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT DEFAULT '',
            sender_id INTEGER,
            receiver_id INTEGER,
            send_date TEXT DEFAULT '',
            receive_date TEXT DEFAULT '',
            send_location TEXT DEFAULT '',
            receive_location TEXT DEFAULT '',
            content TEXT DEFAULT '',
            raw_ocr_text TEXT DEFAULT '',
            is_private INTEGER DEFAULT 0,
            restoration_status TEXT DEFAULT '良好',
            category TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (sender_id) REFERENCES people(id),
            FOREIGN KEY (receiver_id) REFERENCES people(id)
        );

        CREATE TABLE IF NOT EXISTS envelopes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            letter_id INTEGER NOT NULL,
            item_type TEXT DEFAULT '信封',
            image_path TEXT DEFAULT '',
            description TEXT DEFAULT '',
            FOREIGN KEY (letter_id) REFERENCES letters(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            letter_id INTEGER,
            file_path TEXT NOT NULL,
            description TEXT DEFAULT '',
            is_primary INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (letter_id) REFERENCES letters(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person1_id INTEGER NOT NULL,
            person2_id INTEGER NOT NULL,
            relation_type TEXT NOT NULL,
            notes TEXT DEFAULT '',
            FOREIGN KEY (person1_id) REFERENCES people(id) ON DELETE CASCADE,
            FOREIGN KEY (person2_id) REFERENCES people(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS borrow_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            letter_id INTEGER NOT NULL,
            borrower_name TEXT NOT NULL,
            borrow_date TEXT DEFAULT '',
            expected_return_date TEXT DEFAULT '',
            return_date TEXT DEFAULT '',
            status TEXT DEFAULT '借出',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (letter_id) REFERENCES letters(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS albums (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            cover_path TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS album_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            album_id INTEGER NOT NULL,
            letter_id INTEGER,
            photo_id INTEGER,
            caption TEXT DEFAULT '',
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE,
            FOREIGN KEY (letter_id) REFERENCES letters(id) ON DELETE SET NULL,
            FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            backup_date TEXT DEFAULT (datetime('now','localtime')),
            description TEXT DEFAULT '',
            file_size TEXT DEFAULT ''
        );
    """)
    conn.commit()
    conn.close()


def execute_query(sql, params=()):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute(sql, params)
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()


def execute_query_returning(sql, params=()):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute(sql, params)
        rows = c.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def execute_update(sql, params=()):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute(sql, params)
        conn.commit()
        return c.rowcount
    finally:
        conn.close()


def get_statistics():
    conn = get_connection()
    c = conn.cursor()
    stats = {}
    c.execute("SELECT COUNT(*) FROM letters")
    stats['total_letters'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM people")
    stats['total_people'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM letters WHERE is_private = 1")
    stats['private_letters'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM borrow_records WHERE status = '借出'")
    stats['borrowed_out'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM letters WHERE restoration_status = '需修复'")
    stats['need_repair'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM albums")
    stats['total_albums'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM photos")
    stats['total_photos'] = c.fetchone()[0]
    c.execute("""
        SELECT send_date FROM letters
        WHERE send_date != '' AND send_date IS NOT NULL
        ORDER BY send_date DESC LIMIT 1
    """)
    row = c.fetchone()
    stats['latest_letter_date'] = row[0] if row else ''
    conn.close()
    return stats


def get_timeline_data():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT substr(send_date, 1, 4) as year, COUNT(*) as cnt
        FROM letters
        WHERE send_date != '' AND send_date IS NOT NULL
        GROUP BY year
        ORDER BY year
    """)
    data = [dict(row) for row in c.fetchall()]
    conn.close()
    return data


def search_letters(keyword):
    conn = get_connection()
    c = conn.cursor()
    like = f"%{keyword}%"
    c.execute("""
        SELECT l.*, p1.name as sender_name, p2.name as receiver_name
        FROM letters l
        LEFT JOIN people p1 ON l.sender_id = p1.id
        LEFT JOIN people p2 ON l.receiver_id = p2.id
        WHERE l.title LIKE ? OR l.content LIKE ? OR l.send_location LIKE ?
           OR l.receive_location LIKE ? OR l.notes LIKE ?
           OR p1.name LIKE ? OR p2.name LIKE ?
        ORDER BY l.send_date DESC
    """, (like, like, like, like, like, like, like))
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results
