from jinja2 import Environment, FileSystemLoader

# Mock User
class MockUser:
    is_authenticated = True
    is_admin = False

print("Setting up Jinja2...")
env = Environment(loader=FileSystemLoader('/Users/tahir/Desktop/ai-bot/app/templates'))

# Mock Flask globals
env.globals['url_for'] = lambda endpoint, **values: f"/{endpoint}"
env.globals['get_flashed_messages'] = lambda: []
env.globals['current_user'] = MockUser()
env.globals['request'] = type('obj', (object,), {'endpoint': 'dashboard'})
env.globals['asset_url'] = lambda filename: f"/static/{filename}"
env.globals['csrf_token'] = lambda: "mock_token"

try:
    print("Rendering base.html...")
    template = env.get_template('base.html')
    html = template.render(active_page='dashboard', version_label='Testing')
    
    checks = {
        "Marketplace": "Marketplace" in html,
        "Grid Bot": "Grid Bot" in html,
        "Connect Exchanges": "Connect Exchanges" in html
    }
    
    print("\n--- RESULTS ---")
    for feature, passed in checks.items():
        status = "✅ FOUND" if passed else "❌ MISSING"
        print(f"{feature}: {status}")

except Exception as e:
    print(f"Error: {e}")
