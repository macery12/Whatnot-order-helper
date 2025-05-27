import csv
import re
from database import insert_package, init_db

# --- Normalize and validate CSV rows ---
def parse_csv_file(filepath, show_date="", show_label=""):
    def clean(val):
        return str(val).strip() if val else ""

    def extract_last_6(val):
        val = clean(val)
        return val[-6:] if len(val) >= 6 else val

    def extract_id_number(product_name):
        match = re.search(r"#(\\d+)", product_name)
        return match.group(1) if match else ""

    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            order_number = clean(row.get("order numeric id"))
            if not order_number:
                continue

            product_name = clean(row.get("product name"))
            username = clean(row.get("buyer"))
            timestamp = clean(row.get("placed at"))
            bundled = clean(row.get("bundled")).lower() == "true"
            cancelled = bool(clean(row.get("cancelled or failed")))
            tracking = clean(row.get("tracking"))
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
                "image_ids": "",  # match your DB model
                "identifier": identifier
            }

# --- Import into database with validation ---
def import_csv(filepath, show_date="", show_label=""):
    init_db()
    count = 0
    for row in parse_csv_file(filepath, show_date, show_label):
        try:
            if insert_package(row):
                count += 1
        except Exception as e:
            print(f"⚠️ Skipped row with order #{row.get('order_number')}: {e}")
    return count
