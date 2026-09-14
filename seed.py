"""One-off setup script: creates tables, default plans and a controlled
initial administrator account.

Technical Documentation Section 05: "The initial administrator is created
through a controlled setup command, not through public registration."
Section 11 gives the illustrative plan pricing used here.
"""

import sys
from datetime import date

from app import create_app
from app.extensions import db
from app.models import Plan, User, Subscription, Prediction

app = create_app()


def seed():
    with app.app_context():
        db.create_all()

        if Plan.query.count() == 0:
            plans = [
                Plan(name="Free", price_rwf=0, scan_limit=5, history_days=7, is_active=True),
                Plan(name="Individual Pro", price_rwf=3000, scan_limit=100, history_days=365, is_active=True),
                Plan(name="Institution", price_rwf=100000, scan_limit=2000, history_days=730, is_active=True),
            ]
            db.session.add_all(plans)
            db.session.commit()
            print("Seeded plans: Free, Individual Pro, Institution")

        if User.query.filter_by(role="admin").count() == 0:
            admin = User(name="System Administrator", email="admin@wcs.local", role="admin", status="active")
            admin.set_password("ChangeMe123!")
            db.session.add(admin)
            db.session.flush()
            free_plan = Plan.query.filter_by(name="Free").first()
            db.session.add(Subscription(user_id=admin.id, plan_id=free_plan.id, status="active", period_start=date.today()))
            db.session.commit()
            print("Seeded administrator account: admin@wcs.local / ChangeMe123! (change immediately after setup)")

        # Optional interface-demonstration data: NOT a real classification.
        # Clearly flagged with is_placeholder=True and surfaced in the UI as
        # "(demo placeholder)" -- see app/templates/history.html. This exists
        # only to show what a populated history/feedback screen looks like
        # while no trained model is available; it carries no accuracy claim.
        if "--with-demo-data" in sys.argv:
            demo = User.query.filter_by(email="demo@wcs.local").first()
            if demo is None:
                demo = User(name="Demo Resident", email="demo@wcs.local", role="user", status="active")
                demo.set_password("DemoPass123!")
                db.session.add(demo)
                db.session.flush()
                free_plan = Plan.query.filter_by(name="Free").first()
                db.session.add(Subscription(user_id=demo.id, plan_id=free_plan.id, status="active", period_start=date.today()))
                db.session.add(Prediction(
                    user_id=demo.id, model_version_id=None, predicted_class=None,
                    confidence=None, is_uncertain=True, is_placeholder=True,
                ))
                db.session.commit()
                print("Seeded demo account: demo@wcs.local / DemoPass123! (placeholder history record only)")


if __name__ == "__main__":
    seed()
