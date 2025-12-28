#!/usr/bin/env python3
"""Manual save confirm script for persistence verification."""
from app import create_app
import os

app = create_app()
with app.app_context():
    ctx = app.extensions.get('ai_bot_context', {})
    pm = ctx.get('persistence_manager')
    print('persistence_manager:', bool(pm))
    if not pm:
        print('Persistence manager not available')
    else:
        ok = pm.save_complete_state(
            ctx.get('ultimate_trader'),
            ctx.get('ultimate_ml_system'),
            ctx.get('trading_config', {}),
            ctx.get('top_symbols', []),
            ctx.get('historical_data', {}),
        )
        print('manual_save_result:', ok)
        print('bot_state exists?', os.path.exists('bot_persistence/default/bot_state.json'))
        backups_dir = 'bot_persistence/default/backups'
        backups = sorted(os.listdir(backups_dir)) if os.path.exists(backups_dir) else []
        print('backups_count:', len(backups))
        if backups:
            latest = backups[-1]
            print('latest_backup:', latest)
            with open(os.path.join(backups_dir, latest), 'r') as f:
                content = f.read()
            print('--- backup content (first 1000 chars) ---')
            print(content[:1000])
            print('--- end ---')
