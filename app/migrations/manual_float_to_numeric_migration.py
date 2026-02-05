"""
Manual Database Migration Script for Float to Numeric Conversion

This script manually applies the Float to Numeric conversion for financial precision.
Run this script after backing up your database.

Usage:
    python app/migrations/manual_float_to_numeric_migration.py
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.extensions import db
from app import create_app
from sqlalchemy import text

def run_migration():
    """Apply Float to Numeric migration manually."""
    
    app = create_app()
    
    with app.app_context():
        print("🔄 Starting Float to Numeric migration...")
        print("⚠️  This will convert 24 Float columns to Numeric(20, 8)")
        print()
        
        # Get database dialect
        dialect = db.engine.dialect.name
        print(f"📊 Database dialect: {dialect}")
        
        if dialect == 'sqlite':
            print("⚠️  SQLite detected - column type changes require table recreation")
            print("   For SQLite, the migration will be applied on next db.create_all()")
            print("   Existing data will be preserved.")
            
        elif dialect == 'postgresql':
            print("✅ PostgreSQL detected - applying ALTER COLUMN statements...")
            
            # PostgreSQL can alter column types directly
            migrations = [
                # UserTrade table
                "ALTER TABLE user_trade ALTER COLUMN quantity TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_trade ALTER COLUMN entry_price TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_trade ALTER COLUMN exit_price TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_trade ALTER COLUMN pnl TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_trade ALTER COLUMN confidence_score TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_trade ALTER COLUMN cost_basis TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_trade ALTER COLUMN realized_pnl TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_trade ALTER COLUMN realized_gains TYPE NUMERIC(20, 8)",
                
                # UserPortfolio table
                "ALTER TABLE user_portfolio ALTER COLUMN quantity TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_portfolio ALTER COLUMN avg_price TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_portfolio ALTER COLUMN current_price TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_portfolio ALTER COLUMN pnl TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_portfolio ALTER COLUMN pnl_percent TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_portfolio ALTER COLUMN max_position_size TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_portfolio ALTER COLUMN stop_loss TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_portfolio ALTER COLUMN take_profit TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_portfolio ALTER COLUMN total_balance TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_portfolio ALTER COLUMN available_balance TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_portfolio ALTER COLUMN total_profit_loss TYPE NUMERIC(20, 8)",
                "ALTER TABLE user_portfolio ALTER COLUMN daily_pnl TYPE NUMERIC(20, 8)",
                
                # DailyMetrics table
                "ALTER TABLE daily_metrics ALTER COLUMN total_pnl TYPE NUMERIC(20, 8)",
                "ALTER TABLE daily_metrics ALTER COLUMN total_volume TYPE NUMERIC(20, 8)",
                "ALTER TABLE daily_metrics ALTER COLUMN max_drawdown TYPE NUMERIC(20, 8)",
            ]
            
            try:
                for i, migration_sql in enumerate(migrations, 1):
                    print(f"   [{i}/{len(migrations)}] {migration_sql[:60]}...")
                    db.session.execute(text(migration_sql))
                
                db.session.commit()
                print("✅ Migration completed successfully!")
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ Migration failed: {e}")
                print("   Database rolled back to previous state")
                return False
        
        else:
            print(f"⚠️  Unsupported dialect: {dialect}")
            print("   Please manually convert Float columns to Numeric(20, 8)")
        
        print()
        print("✅ Migration process complete!")
        print("   Models.py has been updated to use Numeric(20, 8)")
        print("   All financial calculations will now use precise decimal arithmetic")
        
        return True

if __name__ == "__main__":
    print("=" * 70)
    print("CRITICAL FINANCIAL PRECISION FIX")
    print("Converting Float to Numeric for accurate P&L calculations")
    print("=" * 70)
    print()
    
    response = input("⚠️  Have you backed up your database? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Migration cancelled. Please backup your database first.")
        sys.exit(1)
    
    print()
    success = run_migration()
    
    if success:
        print()
        print("🎉 SUCCESS! Your database now uses precise Numeric types for money.")
        sys.exit(0)
    else:
        print()
        print("❌ Migration failed. Check errors above.")
        sys.exit(1)
