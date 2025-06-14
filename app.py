
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, session, make_response, flash
from database import get_all_packages, init_db, update_packed, update_image_id, update_tracking_number, get_shows, Session, Package, ScanSession
from csv_decoder import import_csv
from collections import defaultdict
import os
from werkzeug.utils import secure_filename
from uuid import uuid4
from datetime import datetime, timedelta
from PIL import Image
from names import PACKER_NAMES
import base64
from io import BytesIO
import barcode
from barcode.writer import ImageWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import inch
from reportlab.graphics.barcode import code128
from reportlab.lib.units import mm
import time

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.secret_key = 'mT@&5$!xq2Z8^frW3Eo1TpGnUvL#X93y'

LABEL_SIZES = {
    'Small (1.5 x 0.75)': ('1.5', '0.75'),
    'Standard (2 x 1)': ('2', '1'),
    'Large (3 x 1.5)': ('3', '1.5')
}
scan_sessions = {}

@app.route('/set_active_packers', methods=['POST'])
def set_active_packers():
    selected = request.form.getlist('active_packers')
    session['active_packers'] = selected

    # Redirect based on where the form was submitted from
    return redirect(request.referrer or url_for('index'))

from collections import defaultdict

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST' and 'csv_file' in request.files:
        file = request.files['csv_file']
        show_date = request.form.get('show_date', '')
        show_label = request.form.get('show_label', '')
        if file and file.filename.endswith('.csv'):
            filename = secure_filename(file.filename)
            filepath = os.path.join('instance', filename)
            file.save(filepath)
            import_csv(filepath, show_date=show_date, show_label=show_label)
            return redirect(url_for('index'))

    query = request.args.get('search', '').strip().lower()
    show_value = request.args.get('show', '')
    selected_show = show_value
    selected_date, selected_label = '', ''

    if '|' in show_value:
        selected_date, selected_label = show_value.split('|', 1)

    all_packages = get_all_packages()
    total_orders = len(all_packages)
    total_packed = len([p for p in all_packages if p.packed])
    total_unpacked = total_orders - total_packed

        # Group by tracking_number or fallback
    filtered_packages = []
    for pkg in all_packages:
        if query and query not in (pkg.username.lower() + pkg.product_name.lower()):
            continue
        if selected_date and selected_label:
            if pkg.show_date != selected_date or pkg.show_label != selected_label:
                continue
        filtered_packages.append(pkg)

    # Group by tracking number or fallback key
    grouped_packages = defaultdict(list)
    for pkg in filtered_packages:
        key = pkg.tracking_number.strip() if pkg.tracking_number else f"missing-{pkg.username.lower()}"
        grouped_packages[key].append(pkg)

    # Convert to regular dict sorted by username
    grouped_packages = dict(sorted(grouped_packages.items(), key=lambda kv: kv[1][0].username.lower()))

    user_packers = {}
    for pkg in all_packages:
        if pkg.username not in user_packers and pkg.packers:
            user_packers[pkg.username] = pkg.packers.split(',')

    return render_template(
        'dashboard.html',
        grouped_packages=grouped_packages,
        total_orders=total_orders,
        total_packed=total_packed,
        total_unpacked=total_unpacked,
        user_packers=user_packers,
        packer_names=PACKER_NAMES,
        query=query,
        shows=get_shows(),
        selected_show=selected_show,
        active_packers=session.get('active_packers', [])
    )

from database import Base, engine

@app.route('/admin/reset_db', methods=['POST'])
def reset_db_route():
    # Optional: Add basic protection
    secret = request.form.get('secret')
    if secret != 'letmein':  # Change this to something secure
        return "Unauthorized", 403

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return "✅ Database has been wiped and reset.", 200

@app.route('/add_tracking_group', methods=['POST'])
def add_tracking_group():
    username = request.form.get('username')
    tracking_number = request.form.get('tracking_number', '').strip()
    if username and tracking_number:
        for pkg in get_all_packages():
            if pkg.username == username and not pkg.tracking_number:
                update_tracking_number(pkg.order_number, tracking_number)
    return redirect(url_for('index'))

@app.route('/toggle_packed/<order_number>', methods=['POST'])
def toggle_packed(order_number):
    packages = get_all_packages()
    for pkg in packages:
        if pkg.order_number == order_number:
            update_packed(order_number, not pkg.packed)
            break
    return redirect(url_for('index'))


@app.route('/upload_image/<order_number>', methods=['POST'])
def upload(order_number):
    image_data = request.form.get('image')  # base64 image from hidden input

    if image_data and image_data.startswith('data:image'):
        try:
            header, encoded = image_data.split(',', 1)
            image_bytes = base64.b64decode(encoded)
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            image.thumbnail((1600, 1600))

            date_str = datetime.now().strftime('%Y%m%d')
            suffix = uuid4().hex[:6]
            filename = f"IMG_{order_number}_{date_str}_{suffix}.jpg"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))

            image.save(filepath, format="JPEG", optimize=True, quality=75)

            update_image_id(order_number, filename)  # ← Your existing DB call
            return redirect(request.referrer or url_for('scan'))
        except Exception as e:
            print(f"Image decode/save failed: {e}")
            return "Invalid image data", 400
    return "No image received", 400

@app.route('/scan', methods=['GET'])
def scan():
    tracking_query = request.args.get('tracking', '').strip()
    search_username = request.args.get('search_username', '').strip().lower()
    show_value = request.args.get('show', '')
    selected_show = show_value
    selected_date, selected_label = '', ''
    if '|' in show_value:
        selected_date, selected_label = show_value.split('|', 1)

    all_packages = get_all_packages()
    selected_orders = []
    matched_order_numbers = []
    show_modal = False

    # Track recent orders
    recent_ids = session.get('recent_orders', [])

    # 📦 TRACKING SCAN
    if tracking_query and len(tracking_query) >= 6:
        last6 = tracking_query[-6:]
        session_db = Session()
        for pkg in all_packages:
            if pkg.tracking_number and pkg.tracking_number.endswith(last6):
                if not selected_date or (pkg.show_date == selected_date and pkg.show_label == selected_label):
                    selected_orders.append(pkg)

# Get previous scanned tracking
        last_tracking = session.get('last_tracking')
        show_modal = (
                    last_tracking == tracking_query and
                    any(not pkg.packed for pkg in selected_orders)
                )

                # Update session state
        session['last_tracking'] = tracking_query
        session['modal_tracking'] = tracking_query if show_modal else ''
        matched_order_numbers = [pkg.order_number for pkg in selected_orders]

    # 🔍 USERNAME SEARCH
    elif search_username:
        for pkg in all_packages:
            if pkg.username.lower() == search_username:
                if not selected_date or (pkg.show_date == selected_date and pkg.show_label == selected_label):
                    selected_orders.append(pkg)
                    matched_order_numbers.append(pkg.order_number)

    # 🕘 UPDATE RECENT ORDERS IN SESSION
    for order_num in matched_order_numbers:
        if order_num not in recent_ids:
            recent_ids.insert(0, order_num)
    session['recent_orders'] = recent_ids[:3]

    # 🔄 GET RECENT ORDER OBJECTS
    recent_orders = [pkg for pkg in all_packages if pkg.order_number in session['recent_orders']]

    return render_template("scan.html",
                           shows=get_shows(),
                           selected_show=selected_show,
                           selected_orders=selected_orders,
                           recent_orders=recent_orders,
                           packer_names=PACKER_NAMES,
                           show_modal=show_modal)


@app.route('/details')
def details():
    tracking_query = request.args.get('tracking', '').strip()
    package = None
    if tracking_query and len(tracking_query) >= 6:
        last6 = tracking_query[-6:]
        for pkg in get_all_packages():
            if pkg.tracking_number and pkg.tracking_number.endswith(last6):
                package = pkg
                break
    return render_template('details.html', package=package)

app.route('/scan/mark/<order_number>', methods=['POST'])
def scan_mark(order_number):
    session_db = Session()
    pkg = session_db.query(Package).filter_by(order_number=order_number).first()
    if pkg:
        pkg.packed = True
        if session.get('active_packers'):
            initials = [
                ''.join(part[0] for part in name.strip().split())
                for name in session['active_packers']
            ]
            pkg.packers = ' + '.join(initials)
        session_db.commit()
    session_db.close()
    return redirect(url_for('scan'))

@app.route('/static/images/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/toggle_packed', methods=['POST'])
def api_toggle_packed():
    data = request.get_json()
    order_number = data.get('order_number')
    packed = data.get('packed')

    session_db = Session()
    pkg = session_db.query(Package).filter_by(order_number=order_number).first()
    if pkg:
        pkg.packed = packed
        if packed:
            initials = [
                ''.join(part[0] for part in name.strip().split())
                for name in session.get('active_packers', [])
            ]
            initials_str = ' + '.join(initials)
            pkg.packers = initials_str
        else:
            pkg.packers = ""
        session_db.commit()
    session_db.close()
    return '', 204


@app.route('/admin', methods=['GET'])
def admin_panel():
    tracking_suffix = request.args.get('tracking_suffix', '').strip()
    edit_order = None

    if tracking_suffix:
        session = Session()
        for pkg in session.query(Package).all():
            if pkg.tracking_number and pkg.tracking_number.endswith(tracking_suffix):
                edit_order = pkg
                break
        session.close()

    return render_template('admin.html', edit_order=edit_order)


@app.route('/admin/create', methods=['POST'])
def admin_create():
    session = Session()
    new_pkg = Package(
        username=request.form.get('username'),
        order_number=request.form.get('order_number'),
        product_name=request.form.get('product_name'),
        timestamp=request.form.get('timestamp'),
        tracking_number=request.form.get('tracking_number'),
        show_date=request.form.get('show_date'),
        show_label=request.form.get('show_label'),
        bundled=bool(request.form.get('bundled')),
        cancelled=bool(request.form.get('cancelled')),
        packed=bool(request.form.get('packed')),
    )
    session.add(new_pkg)
    session.commit()
    session.close()
    return redirect(url_for('admin_panel'))


@app.route('/admin/edit/<order_number>', methods=['POST'])
def admin_edit(order_number):
    session = Session()
    pkg = session.query(Package).filter_by(order_number=order_number).first()
    if pkg:
        pkg.username = request.form.get('username')
        pkg.product_name = request.form.get('product_name')
        pkg.timestamp = request.form.get('timestamp')
        pkg.tracking_number = request.form.get('tracking_number')
        pkg.show_date = request.form.get('show_date')
        pkg.show_label = request.form.get('show_label')
        pkg.bundled = bool(request.form.get('bundled'))
        pkg.cancelled = bool(request.form.get('cancelled'))
        pkg.packed = bool(request.form.get('packed'))
        session.commit()
    session.close()
    return redirect(url_for('admin_panel'))

@app.route('/api/scan/toggle_packed', methods=['POST'])
def api_toggle_scan_packed():
    data = request.get_json()
    order_number = data.get('order_number')
    new_status = data.get('packed')
    if order_number is not None and new_status is not None:
        update_packed(order_number, new_status)
        return '', 204
    return 'Bad Request', 400

@app.route('/set_packers', methods=['POST'])
def set_packers():
    username = request.form.get('username')
    packers = request.form.getlist('packers')
    session = Session()
    updated = False

    for pkg in session.query(Package).filter_by(username=username).all():
        pkg.packers = ','.join(packers)
        updated = True

    if updated:
        session.commit()
    session.close()

    return redirect(url_for('index'))

@app.route('/label', methods=['GET', 'POST'])
def label():
    label_sizes = LABEL_SIZES

    if request.method == 'POST':
        id_number = request.form.get('id_number', '').strip()
        name = request.form.get('name', '').strip()
        item_name = request.form.get('item_name', '').strip()
        label_size = request.form.get('label_size', 'Standard (2 x 1)')
        hide_company = 'hide_company' in request.form
        hide_date = 'hide_date' in request.form

        today_str = datetime.now().strftime('%Y-%m-%d')
        width_in, height_in = map(float, label_sizes[label_size])

        # Ensure label output directory exists
        pdf_folder = os.path.join('static', 'labels')
        os.makedirs(pdf_folder, exist_ok=True)

        pdf_filename = f"{id_number}_{uuid4().hex}.pdf"
        pdf_path = os.path.join(pdf_folder, pdf_filename)
        pdf_url = f"/static/labels/{pdf_filename}"

        # Start PDF generation
        c = canvas.Canvas(pdf_path, pagesize=(width_in * inch, height_in * inch))
        label_width = width_in * inch
        label_height = height_in * inch
        y_cursor = label_height - 8

        # Company Name
        if not hide_company:
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(label_width / 2, y_cursor, "Tyco Connections")
            y_cursor -= 8

        # Username (above line)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(label_width / 2, y_cursor, name)
        y_cursor -= 8

        # Divider line
        c.setLineWidth(0.5)
        c.line(4, y_cursor, label_width - 4, y_cursor)
        y_cursor -= 10

        # Top Row: Date | Item Name | ID#
        c.setFont("Helvetica", 6)
        if not hide_date:
            c.drawString(4, y_cursor, today_str)
        c.drawCentredString(label_width / 2, y_cursor, item_name[:20])
        c.drawRightString(label_width - 4, y_cursor, f"#{id_number}")
        y_cursor -= 32

        # Barcode
        barcode_string = f"{item_name} | {id_number} | {name}"
        barcode_obj = code128.Code128(barcode_string, barHeight=10 * mm, barWidth=0.28)
        barcode_width = barcode_obj.width
        barcode_x = (label_width - barcode_width) / 2
        barcode_y = max(y_cursor - 10, 4)
        barcode_obj.drawOn(c, barcode_x, barcode_y)

        c.showPage()
        c.save()

        return render_template(
            'label.html',
            pdf_url=pdf_url,
            label_sizes=label_sizes,
            selected_label=label_size,
            hide_company=hide_company,
            hide_date=hide_date
        )

    return render_template(
        'label.html',
        label_sizes=label_sizes,
        selected_label='Standard (2 x 1)'
    )


@app.route('/confirm_pack', methods=['POST'])
def confirm_pack():
    tracking_number = request.form.get('tracking_number', '').strip()
    last6 = tracking_number[-6:]
    session_db = Session()
    updated = 0

    for pkg in session_db.query(Package).all():
        if pkg.tracking_number and pkg.tracking_number.endswith(last6):
            if not pkg.packed:
                pkg.packed = True
                initials = [
                    ''.join(part[0] for part in name.strip().split())
                    for name in session.get('active_packers', [])
                ]
                pkg.packers = ' + '.join(initials)
                updated += 1

    session_db.commit()
    session_db.close()
    flash(f"{updated} order(s) marked as packed.")
    return redirect(url_for('scan'))

@app.route('/update_tracking', methods=['POST'])
def update_tracking():
    data = request.get_json()
    order_id = data.get('order_id')
    tracking_number = data.get('tracking_number')
    if order_id and tracking_number:
        update_tracking_number(order_id, tracking_number)
        return jsonify({'success': True})
    return jsonify({'success': False}), 400
@app.route('/scan-pair', methods=['GET', 'POST'])
def scan_pair():
    db_session = Session()

    # POST first to safely capture input
    if request.method == 'POST':
        data = request.form.get('scan_input', '').strip()
        if not data:
            flash("⚠️ Empty scan input")
            return redirect(url_for('scan_pair'))

        now = time.time()
        date = datetime.now()
        current_date = f"{date.month}/{date.day}/{date.year}"

        # USPS scan logic
        if data.isdigit() and len(data) > 20:
            # Check for existing open session with this label
            active_session = db_session.query(ScanSession).filter_by(finalized=False).order_by(ScanSession.created_at.desc()).first()
            active_usps = active_session.tracking_number if active_session else None
            scanned_items = active_session.scanned_items.split(',') if active_session and active_session.scanned_items else []

            if active_session and active_session.tracking_number == data:
                if active_session.timestamp and (datetime.now() - active_session.timestamp).total_seconds() > 180:
                    active_session.finalized = True
                    db_session.commit()
                    flash("⏱️ USPS session expired after 3 minutes of inactivity.")
                    return redirect(url_for('scan_pair'))

                # Save items to DB
                saved_count = 0
                initials = session.get('active_packers', [])
                for item in scanned_items:
                    try:
                        parts = item.split('|')
                        product_name, item_id = parts[0].strip(), parts[1].strip()
                        username = parts[-1].strip()  # Last part is username
                    except ValueError:
                        flash(f"⚠️ Skipped malformed item: {item}")
                        continue

                    if db_session.query(Package).filter_by(order_number=item_id, tracking_number=data).first():
                        flash(f"⚠️ Skipped duplicate: {item}")
                        continue

                    pkg = Package(
                        username=username,
                        product_name=product_name,
                        order_number=item_id,
                        timestamp=str(datetime.now()),
                        tracking_number=data,
                        bundled=False,
                        cancelled=False,
                        packed=True,
                        show_date=current_date,
                        show_label='',
                        image_ids='',
                        packers=' + '.join(initials)
                    )
                    db_session.add(pkg)
                    saved_count += 1

                active_session.finalized = True
                db_session.commit()
                flash(f"✅ Saved {saved_count} item(s) to USPS: {data}")
            else:
                # Finalize all lingering open sessions
                for s in db_session.query(ScanSession).filter_by(finalized=False).all():
                    s.finalized = True
                db_session.commit()

                # Check again to avoid inserting duplicate tracking
                reuse = db_session.query(ScanSession).filter_by(tracking_number=data, finalized=False).first()
                if reuse:
                    flash(f"📦 Resuming existing USPS session: {data}")
                else:
                    new_session = ScanSession(
                        tracking_number=data,
                        scanned_items="",
                        finalized=False,
                        timestamp=datetime.now(),
                        created_at=datetime.now()
                    )
                    db_session.add(new_session)
                    db_session.commit()
                    flash(f"📬 New USPS package started: {data}")

        else:
            # Item scan
            active_session = db_session.query(ScanSession).filter_by(finalized=False).order_by(ScanSession.created_at.desc()).first()
            if not active_session:
                flash("❗ Please scan a USPS label first.")
                return redirect(url_for('scan_pair'))

            scanned_items = active_session.scanned_items.split(',') if active_session.scanned_items else []

            if data.count('|') != 2:
                flash("❗ Invalid item format. Use: product | ID# | username")
                return redirect(url_for('scan_pair'))

            if data in scanned_items:
                flash(f"⚠️ Duplicate item scan: {data}")
                return redirect(url_for('scan_pair'))

            # Extract and normalize new username
            try:
                parts = data.split('|')
                new_username = parts[-1].strip().lower().replace(' ', '')

                if scanned_items:
                    try:
                        base_parts = scanned_items[0].split('|')
                        base_username = base_parts[-1].strip().lower().replace(' ', '')
                    except ValueError:
                        flash("❗ Username check failed: first scanned item is malformed.")
                        return redirect(url_for('scan_pair'))

                    if new_username != base_username:
                        flash(f"❌ Username mismatch: '{parts[-1].strip()}' does not match base '{base_parts[-1].strip()}'")
                        return redirect(url_for('scan_pair'))
            except Exception:
                flash("❗ Could not parse item username.")
                return redirect(url_for('scan_pair'))

            # Save scan
            scanned_items.append(data)
            active_session.scanned_items = ','.join(scanned_items)
            active_session.timestamp = datetime.now()
            db_session.commit()
            flash(f"✅ Added item: {data}")

        return redirect(url_for('scan_pair'))

    # GET request
    active_session = db_session.query(ScanSession).filter_by(finalized=False).order_by(ScanSession.created_at.desc()).first()
    active_usps = active_session.tracking_number if active_session else None
    scanned_items = active_session.scanned_items.split(',') if active_session and active_session.scanned_items else []
    existing_items = []

    if active_usps:
        existing_items = db_session.query(Package).filter_by(tracking_number=active_usps).all()

    return render_template(
        'scan_pair.html',
        active_usps=active_usps,
        scanned_items=scanned_items,
        existing_items=existing_items,
        packer_names=PACKER_NAMES,
        active_packers=session.get('active_packers', [])  
    )



init_db()
if __name__ == '__main__':

    app.run(debug=True, port=5000, host="0.0.0.0")
