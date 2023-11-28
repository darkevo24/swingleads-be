# app.py
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import uuid
import secrets
from flask_cors import CORS

app = Flask(__name__)
app.config[
    "SQLALCHEMY_DATABASE_URI"
] = "postgres://default:dbWXEvr2ZSi0@ep-wild-feather-19186131.us-east-1.postgres.vercel-storage.com:5432/verceldb"
db = SQLAlchemy(app)
CORS(app)


class Code(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    device_id = db.Column(db.String(36), nullable=False, unique=True)


def generate_code():
    return secrets.token_hex(4)


def cleanup_expired_codes():
    # Remove expired codes from the database
    now = datetime.utcnow()
    expired_codes = Code.query.filter(Code.expires_at < now).all()
    for code in expired_codes:
        db.session.delete(code)
    db.session.commit()


scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_expired_codes, "interval", hours=1)  # Cleanup every 1 hour
scheduler.start()


@app.route("/generate_code", methods=["GET", "POST"])
def generate_and_save_code():
    if request.method == "POST":
        new_code = generate_code()
        expiration_date = datetime.utcnow() + timedelta(days=30)  # 30 days expiration
        device_id = str(uuid.uuid4())
        code_entry = Code(
            code=new_code, expires_at=expiration_date, device_id=device_id
        )
        db.session.add(code_entry)
        db.session.commit()
        return f"Code {new_code} generated and saved with ID {code_entry.id} for device {device_id}"


from sqlalchemy import desc


@app.route("/generate_multiple_codes", methods=["GET", "POST"])
def generate_and_save_multiple_codes():
    if request.method == "POST":
        num_codes = 100
        generated_codes = []

        for _ in range(num_codes):
            new_code = generate_code()
            expiration_date = datetime.utcnow() + timedelta(
                days=30
            )  # 30 days expiration
            device_id = str(uuid.uuid4())
            code_entry = Code(
                code=new_code, expires_at=expiration_date, device_id=device_id
            )
            db.session.add(code_entry)
            generated_codes.append(new_code)

        db.session.commit()

        # Retrieve the last num_codes entries from the Code table
        latest_codes = Code.query.order_by(desc(Code.id)).limit(num_codes).all()

        return f"{num_codes} codes generated and saved with IDs: {', '.join(str(code.id) for code in latest_codes)}"


@app.route("/check_pin", methods=["POST"])
def check_pin():
    if request.method == "POST":
        received_pin = request.json.get("pin")

        # Check if the received PIN exists in the database
        code_entry = Code.query.filter_by(code=received_pin).first()

        if code_entry:
            return {"message": "PIN is valid"}
        else:
            return {"message": "Invalid PIN"}


if __name__ == "__main__":
    with app.app_context():
        # Create database tables
        db.create_all()
    app.run(debug=True)
