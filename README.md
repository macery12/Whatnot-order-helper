Here’s an updated version of your `README.md` that reflects the full scope of your Whatnot project and clearly labels it as a work in progress (WIP):

---

```markdown
# Whatnot Order Helper 📦 *(Work In Progress)*

**A powerful local tool for Whatnot sellers to manage, track, and document order packing — with advanced scanning, labeling, photo uploads, and user tracking.**

This WIP Flask-based web application is designed to simplify the packaging workflow during live sales by connecting scanned USPS tracking numbers to Whatnot CSV-exported orders. It also supports photo documentation, user tracking, and streamlined label printing — all aimed at reducing packing errors and disputes.

---

## 🔧 Core Features (Stable)

- **📥 CSV Import Tool**: Processes Whatnot-exported CSVs to load and organize live sale orders.
- **✅ Packing Tracker**: Toggle "Packed" status per order with real-time visual updates.
- **📸 Image Uploads**: Upload multiple photo proofs for each order — stored and linked to item records.
- **📊 Dashboard View**: Color-coded interface to highlight missing tracking, packing status, and per-user counts.
- **📦 Scan Mode**: Use a barcode scanner to instantly pull up, update, and document orders using USPS tracking numbers.
- **📋 Admin Page**: Manually add or edit orders by tracking number or order number for debugging or adjustments.

---

## 🧪 Experimental & WIP Features

- **👤 User Tracking System**: Set and persist active packers; auto-log who packed each order.
- **📷 Scan Camera Integration**: Trigger camera preview/recording on barcode scan to document packing live.
- **🖨️ Label Maker**: Generate 2x1" labels using scanned item name + ID + username and print via browser.
- **📦 Live Scan Flow**: Smart workflow for scanning USPS labels:
  - First scan = fetch and display package
  - Second scan = mark as packed + associate images + set packer
- **🍪 Persistent UI Cookies**: Store label size, packer, and layout preferences in cookies for session continuity.
- **📦 Support for Multiple Orders per Tracking #**: Detect and display grouped packages per scanned label.

---

## 📂 Project Structure

```

├── app.py                   # Main Flask app
├── csv_decoder.py           # Parses Whatnot CSVs and integrates with DB
├── database.py              # SQLAlchemy models + DB session setup
├── static/
│   └── images/              # Order photo uploads
│   └── css/                 # Styles (dashboard, scan, labelmaker, etc.)
├── templates/               # Jinja2 HTML templates
├── instance/                # Volume-mounted SQLite/Postgres data folder
├── requirements.txt         # Python dependencies
├── Dockerfile               # Docker build config
├── docker-compose.yml       # Compose setup for Flask + Postgres

````

---

## 🚀 Getting Started

### Manual Setup (Local Python)

```bash
git clone https://github.com/macery12/Whatnot-order-helper.git
cd Whatnot-order-helper
pip install -r requirements.txt
python app.py
````

Then open your browser at:

```
http://localhost:5000
```

---

### Docker Deployment

```bash
docker-compose up -d
```

Make sure to configure `names.py` and environment vars in `docker-compose.yml` for database URL and options.

---

## 🧠 App Usage Flow

1. Upload a Whatnot CSV to load orders.
2. (Optional) Add tracking numbers manually or auto-fill from scan.
3. Click a username section to view their orders.
4. Use scan page to:

   * Scan USPS label → pull up item
   * Second scan → mark as packed, save images, log packer
5. Use label maker to generate 2x1" stickers for each item.

---

## 📌 Roadmap Highlights

Planned and actively developed features:

* 🔐 Login support
* 📦 Scan-then-pack session tracking
* 🧾 Label format editor
* 📂 Multi-photo batch upload
* 🧮 Stats/analytics per packer
* 🧹 Database reset/test utilities

See `whatnot_app_roadmap.txt` for full details.

---

## ⚠️ Disclaimer

This is a **Work In Progress** and may not function reliably in production environments yet. Expect breaking changes and bugs until version 1.0.

---

## 📝 License

MIT License — free for personal or commercial use. See `LICENSE`.

---

## 🙋 Support & Contributions

Suggestions, bug reports, and pull requests are encouraged! Start a discussion or fork and contribute on GitHub.

```

