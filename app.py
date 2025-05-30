
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, session, make_response, flash
from database import get_all_packages, init_db, update_packed, update_image_id, update_tracking_number, get_shows, Session, Package
from csv_decoder import import_csv
from collections import defaultdict
import os
from werkzeug.utils import secure_filename
from uuid import uuid4
from datetime import datetime
from PIL import Image
from names import PACKER_NAMES
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.secret_key = 'mT@&5$!xq2Z8^frW3Eo1TpGnUvL#X93y'

LABEL_SIZES = {
    'Small (1.5 x 0.75)': ('1.5', '0.75'),
    'Standard (2 x 1)': ('2', '1'),
    'Large (3 x 1.5)': ('3', '1.5')
}


@app.route('/set_active_packers', methods=['POST'])
def set_active_packers():
    selected = request.form.getlist('active_packers')
    session['active_packers'] = selected

    # Redirect based on where the form was submitted from
    return redirect(request.referrer or url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    init_db()
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

    filtered = []
    grouped = defaultdict(list)
    status_by_user = {}

    for pkg in all_packages:
        if query and query not in (pkg.username.lower() + pkg.product_name.lower()):
            continue
        if selected_date and selected_label:
            if pkg.show_date != selected_date or pkg.show_label != selected_label:
                continue
        grouped[pkg.username].append(pkg)

    # Determine user status colors
    for username, orders in grouped.items():
        has_missing_tracking = any(not p.tracking_number for p in orders)
        if has_missing_tracking:
            status = 'missing-tracking'
        else:
            all_packed = all(p.packed for p in orders)
            if all_packed:
                status = 'packed'
            else:
                status = 'needs-packing'
        status_by_user[username] = status
    user_packers = {}
    for pkg in all_packages:
        if pkg.username not in user_packers and pkg.packers:
            user_packers[pkg.username] = pkg.packers.split(',')

    return render_template(
        'dashboard.html',
        data=grouped,
        status_by_user=status_by_user,
        query=query,
        shows=get_shows(),
        selected_show=selected_show,
        total_orders=total_orders,
        total_packed=total_packed,
        total_unpacked=total_unpacked,
        user_packers=user_packers,
        packer_names=PACKER_NAMES
    )

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
def upload_image(order_number):
    file = request.files['image']
    if file:
        date_str = datetime.now().strftime('%Y%m%d')
        suffix = uuid4().hex[:6]
        filename = f"IMG_{order_number}_{date_str}_{suffix}.jpg"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))

        try:
            from PIL import Image
            image = Image.open(file.stream)
            image = image.convert("RGB")
            image.thumbnail((1600, 1600))
            image.save(filepath, format="JPEG", optimize=True, quality=75)
            update_image_id(order_number, filename)
        except Exception as e:
            print("Image compression error:", e)

    return redirect(request.referrer or url_for('scan'))

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
    label_data = None

    selected_label = request.cookies.get('label_size', 'Standard (2 x 1)')
    hide_company = request.cookies.get('hide_company', 'false') == 'true'
    hide_date = request.cookies.get('hide_date', 'false') == 'true'
    width, height = LABEL_SIZES.get(selected_label, ('2', '1'))

    if request.method == 'POST':
        id_number = request.form.get('id_number')
        name = request.form.get('name')
        selected_label = request.form.get('label_size', selected_label)
        hide_company = 'hide_company' in request.form
        hide_date = 'hide_date' in request.form
        width, height = LABEL_SIZES.get(selected_label, ('2', '1'))
        today = datetime.today().strftime('%m/%d/%Y')

        label_data = {
            'id': id_number,
            'name': name,
            'date': today,
            'hide_company': hide_company,
            'hide_date': hide_date,
            'width': width,
            'height': height
        }

        response = make_response(render_template('label.html', label=label_data,
                                                 label_sizes=LABEL_SIZES,
                                                 selected_label=selected_label,
                                                 hide_company=hide_company,
                                                 hide_date=hide_date))
        response.set_cookie('label_size', selected_label)
        response.set_cookie('hide_company', str(hide_company).lower())
        response.set_cookie('hide_date', str(hide_date).lower())
        return response

    return render_template('label.html',
                           label=None,
                           label_sizes=LABEL_SIZES,
                           selected_label=selected_label,
                           hide_company=hide_company,
                           hide_date=hide_date)

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


if __name__ == '__main__':
    app.run(debug=True, port=1689, host="0.0.0.0")
