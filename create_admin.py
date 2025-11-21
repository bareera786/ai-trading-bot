#!/usr/bin/env python3
"""
Script to create an admin user for the trading bot
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from datetime import datetime
import os

# Recreate the app context
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///trading_bot.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=None)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

# UserTrade model
class UserTrade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    signal_data = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    action_taken = db.Column(db.String(50))

# UserPortfolio model for multi-user portfolio management
class UserPortfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Float, default=0.0)
    avg_price = db.Column(db.Float, default=0.0)
    current_price = db.Column(db.Float, default=0.0)
    pnl = db.Column(db.Float, default=0.0)
    pnl_percent = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Risk management fields
    max_position_size = db.Column(db.Float, default=0.1)  # Max % of portfolio
    stop_loss = db.Column(db.Float, default=0.05)  # Stop loss %
    take_profit = db.Column(db.Float, default=0.1)  # Take profit %

    # User-specific settings
    auto_trade_enabled = db.Column(db.Boolean, default=False)
    risk_level = db.Column(db.String(20), default='medium')  # low, medium, high

    __table_args__ = (db.UniqueConstraint('user_id', 'symbol', name='unique_user_symbol'),)

def create_admin_user():
    with app.app_context():
        # Check if admin user already exists
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user:
            print("Admin user already exists!")
            return

        # Create admin user
        admin = User(username='admin', email='admin@example.com', is_admin=True, is_active=True)
        admin.set_password('admin123')  # Change this password!

        db.session.add(admin)
        db.session.commit()

        print("✅ Admin user created successfully!")
        print("Username: admin")
        print("Email: admin@example.com")
        print("Password: admin123")
        print("⚠️  Please change the default password after first login!")

if __name__ == '__main__':
    create_admin_user()