import csv
import re
from datetime import datetime
from database import insert_package, init_db

def clean(val):
    return str(val).strip() if val else ""

def extract_last_6(val):
    val = clean(val)
    return val[-6:] if len(val) >= 6 else val

def extract_id_number(product_name):
    """Extract ID from product name like #123, ID#123, etc."""
    match = re.search(r"(?:ID#?|#)\s*(\d+)", product_name, re.IGNORECASE)
    return match.group(1) if match else ""

def normalize_timestamp(timestamp):
    """Ensure timestamp is in ISO 8601 format"""
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.isoformat()
    except Exception:
        return ""

def parse_csv_file(filepath, show_date="", show_label=""):
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            try:
                order_number = clean(row.get("order numeric id"))
                if not order_number:
                    raise ValueError("Missing order ID")

                product_name = clean(row.get("product name"))
                username = clean(row.get("buyer"))
                timestamp = normalize_timestamp(clean(row.get("placed at")))
                bundled = clean(row.get("bundled")).lower() == "true"
                cancelled = bool(clean(row.get("cancelled or failed")))
                tracking = clean(row.get("tracking"))
                label_url = clean(row.get("label only"))
                identifier = extract_id_number(product_name)

                yield {
                    "username": username,
                    "order_number": order_number,
                    "product_name": product_name,
                    "timestamp": timestamp,
                    "bundled": bundled,
                    "cancelled": cancelled,
                    "packed": False,
                    "tracking_number": tracking,
                    "show_date": show_date,
                    "show_label": show_label,
                    "image_ids": "",  # Reserved for image upload support
                    "identifier": identifier,
                    "label_url": label_url
                }

            except Exception as e:
                print(f"⚠️ Skipping row {i}: {e}")

def import_csv(filepath, show_date="", show_label=""):
    init_db()
    count = 0
    for row in parse_csv_file(filepath, show_date, show_label):
        try:
            if insert_package(row):
                count += 1
        except Exception as e:
            print(f"⚠️ Could not insert order #{row.get('order_number')}: {e}")
    return count
