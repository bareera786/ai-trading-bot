#!/usr/bin/env python3
"""
Phase 6 UI Integration Script
Automatically adds Health Monitor UI and JavaScript to brain_dashboard.html
"""

import re

# Read the dashboard file
with open('app/templates/admin/brain_dashboard.html', 'r') as f:
    content = f.read()

# Read the Health Monitor HTML component
with open('app/templates/admin/health_monitor_component.html', 'r') as f:
    health_monitor_html = f.read()

# Read the JavaScript functions
with open('app/static/js/phase6_health_monitor.js', 'r') as f:
    health_monitor_js = f.read()

# 1. Insert Health Monitor HTML before "<!-- Model Registry -->"
if '<!-- Model Registry -->' in content and 'id="healthMonitor"' not in content:
    content = content.replace(
        '        <!-- Model Registry -->',
        health_monitor_html + '\n\n        <!-- Model Registry -->'
    )
    print("✅ Health Monitor HTML added")
else:
    print("⚠️  Health Monitor HTML already exists or Model Registry marker not found")

# 2. Insert JavaScript before the closing </script> tag
# Find the last </script> in the file
script_close_pattern = r'(\s*)(</script>)(\s*)({% endblock %})'
if re.search(script_close_pattern, content) and 'fetchHealthMetrics' not in content:
    # Add JS before the last </script>
    content = re.sub(
        script_close_pattern,
        r'\1\n' + health_monitor_js + r'\n\1\2\3\4',
        content
    )
    print("✅ Health Monitor JavaScript added")
else:
    print("⚠️  Health Monitor JavaScript already exists or script tag not found")

# Write back
with open('app/templates/admin/brain_dashboard.html', 'w') as f:
    f.write(content)

print("\n🎉 Phase 6 UI integration complete!")
print("\nNext steps:")
print("1. Review the changes in brain_dashboard.html")
print("2. Deploy to VPS: ./scripts/deployment/deploy_to_vps_complete.sh")
print("3. Run database migration on VPS")
