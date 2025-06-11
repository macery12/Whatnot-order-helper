from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime

# PostgreSQL database URL from environment variable (Docker-ready fallback)
db_url = os.getenv(
    "DATABASE_URL" 
)
if not db_url:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'instance', 'whatnot_test.db')
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db_url = f"sqlite:///{DB_PATH}"

engine = create_engine(db_url, echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class ScanSession(Base):
    __tablename__ = 'scan_sessions'

    id = Column(Integer, primary_key=True)
    tracking_number = Column(String(100), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    scanned_items = Column(Text)
    finalized = Column(Boolean, default=False)

class Package(Base):
    __tablename__ = 'packages'

    id = Column(Integer, primary_key=True)
    username = Column(String(100))
    order_number = Column(String(100), unique=True)
    product_name = Column(String(200))
    timestamp = Column(String(100))
    bundled = Column(Boolean)
    cancelled = Column(Boolean)
    packed = Column(Boolean, default=False)
    tracking_number = Column(String(100), nullable=True)
    show_date = Column(String(20))
    show_label = Column(String(100), nullable=True)
    image_ids = Column(String, default="")
    identifier = Column(String(20), nullable=True)
    packers = Column(Text, default="")
    label_url = Column(String, nullable=True)
    item_id = Column(String(100))

def init_db():
    Base.metadata.create_all(engine)

def insert_package(data):
    order_number = data.get('order_number', '').strip()
    if not order_number:
        return False

    session = Session()
    try:
        if session.query(Package).filter_by(order_number=order_number).first():
            return False

        pkg = Package(
            username=data.get('username', '').strip(),
            order_number=order_number,
            product_name=data.get('product_name', '').strip(),
            timestamp=data.get('timestamp', '').strip(),
            bundled=bool(data.get('bundled', False)),
            cancelled=bool(data.get('cancelled', False)),
            packed=bool(data.get('packed', False)),
            tracking_number=data.get('tracking_number', '').strip(),
            show_date=data.get('show_date', '').strip(),
            show_label=data.get('show_label', '').strip(),
            image_ids=data.get('image_ids', '').strip(),
            identifier=data.get('identifier', '').strip(),
            label_url=data.get('label_url', '').strip()  
        )

        session.add(pkg)
        session.commit()
        return True
    except Exception as e:
        print(f"⚠️ DB insert failed for order {order_number}: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def package_exists(order_number):
    session = Session()
    exists = session.query(Package).filter_by(order_number=order_number).first() is not None
    session.close()
    return exists

def get_all_packages():
    session = Session()
    packages = session.query(Package).all()
    session.close()
    return packages

def get_shows():
    session = Session()
    shows = session.query(Package.show_date, Package.show_label).distinct().all()
    session.close()
    return sorted(set(shows))

def update_packed(order_number, packed=True):
    session = Session()
    pkg = session.query(Package).filter_by(order_number=order_number).first()
    if pkg:
        pkg.packed = packed
        session.commit()
    session.close()

def update_image_id(order_number, new_image_id):
    session = Session()
    pkg = session.query(Package).filter_by(order_number=order_number).first()
    if pkg:
        current = pkg.image_ids.split(',') if pkg.image_ids else []
        if new_image_id not in current:
            current.append(new_image_id)
            pkg.image_ids = ','.join(current)
            session.commit()
    session.close()

def update_tracking_number(order_number, tracking_number):
    session = Session()
    pkg = session.query(Package).filter_by(order_number=order_number).first()
    if pkg:
        pkg.tracking_number = tracking_number
        session.commit()
    session.close()
