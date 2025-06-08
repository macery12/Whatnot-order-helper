# Whatnot Order Helper 📦

**A streamlined local tool for Whatnot sellers to manage, track, and document packaging of live-sale orders.**

This Flask-based web app helps packaging teams match Whatnot orders to physical boxes, track packing progress, and optionally upload photos of each packed order for recordkeeping — a lifesaver in case of missing items or packing disputes.

---

## 🔧 Features

- **CSV Import Tool**: Parse and process Whatnot-exported CSVs to load show orders.
- **Packing Tracker**: Toggle order status as "Packed" or "Unpacked" to stay organized.
- **Image Uploads**: Attach photo records to each order to prove what was packed.
- **Dashboard View**: Clean, color-coded interface for quickly identifying packing progress.
- **Scan Mode**: Supports barcode scanning to quickly pull up and update order status.
- **User Tracking (WIP)**: Planned user system to log who packed what order.

---

## 📂 Project Structure

```
├── app.py                   # Main Flask app
├── csv_decoder.py           # Handles parsing of Whatnot CSV files
├── database.py              # SQLAlchemy models and DB setup
├── static/                  # CSS, images, and JavaScript files
├── templates/               # Jinja2 HTML templates
├── instance/                # Contains the SQLite database (volume-mounted)
├── requirements.txt         # Python dependencies
├── Dockerfile               # Docker build config
├── docker-compose.yml       # Easy deployment setup
└── whatnot_app_roadmap.txt  # Planned features and notes
```

---

## 🚀 Getting Started

### Manual Setup (Local Python)

1. Clone the repo:
   ```bash
   git clone https://github.com/macery12/Whatnot-order-helper.git
   cd Whatnot-order-helper
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:
   ```bash
   python app.py
   ```

4. Open your browser at:
   ```
   http://localhost:5000
   ```

---

### Docker Deployment

If you'd rather run it in a containerized environment:

```yaml
services:
  web:
    image: ghcr.io/macery12/whatnot-order-helper:latest
    container_name: whatnot-flask-app
    ports:
      - 5000:5000
    volumes:
      - /{FOLDER-NAME-HERE)/names.py:/app/names.py #employee names listing
    restart: always
    depends_on: []
    environment:
      - DATABASE_URL=
  postgress:
    image: postgres:15
    container_name: whatnot-postgres
    restart: always
    environment:
      POSTGRES_USER: 
      POSTGRES_PASSWORD: 
      POSTGRES_DB: 
    volumes:
      - whatnot_pgdata:/var/lib/postgresql/data
    ports:
      - 5432:5432
volumes:
  whatnot_pgdata: null
networks: {}

```

Then run:

```bash
docker-compose up -d
```

And access via:

```
http://localhost:5000
```

---

## 🧠 How It Works

- Upload a CSV export from Whatnot
- The app reads:
  - Username
  - Order Number
  - Product Name
  - Timestamp
  - Cancelled/Bundled status
- You can toggle "Packed" status per order and upload image proof
- Future updates will add per-user packing records and login support

---

## 📌 Roadmap

Check `whatnot_app_roadmap.txt` for planned features including:

- User login system
- Bulk photo uploads
- Scan-to-pack flow improvements
- Admin override tools

---

## 📝 License

MIT License – free to use and modify. See `LICENSE`.

---

## 🙋 Support & Contributions

Bug reports, feature requests, and pull requests are welcome! Start by creating an issue or fork and submit a PR.
