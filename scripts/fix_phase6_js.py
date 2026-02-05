#!/usr/bin/env python3
"""
Fix Phase 6 JavaScript syntax errors in brain_dashboard.html
"""

import re

# Read the file
with open('app/templates/admin/brain_dashboard.html', 'r') as f:
    content = f.read()

# Fix the manualResume function with proper string escaping
old_function = r"""async function manualResume\(\) \{
    const confirmed = confirm\(
        '⚠️ MANUAL OVERRIDE WARNING
.*?
.*?You will need to monitor the system very closely after resuming\.'
    \);"""

new_function = """async function manualResume() {
    const confirmed = confirm(
        '⚠️ MANUAL OVERRIDE WARNING\\\\n\\\\n' +
        'You are about to manually resume signals after an automatic pause.\\\\n\\\\n' +
        'The watchdog detected a problem with the model and paused signals for your protection.\\\\n\\\\n' +
        'Are you ABSOLUTELY SURE you want to override this safety measure?\\\\n\\\\n' +
        'You will need to monitor the system very closely after resuming.'
    );"""

content = re.sub(old_function, new_function, content, flags=re.DOTALL)

# Fix the prompt line
old_prompt = r"""const phrase = prompt\('Enter confirmation phrase exactly as shown:

MANUAL OVERRIDE CONFIRMED'\);"""

new_prompt = """const phrase = prompt('Enter confirmation phrase exactly as shown:\\\\n\\\\nMANUAL OVERRIDE CONFIRMED');"""

content = re.sub(old_prompt, new_prompt, content)

# Fix the alert line
old_alert = r"""alert\('✅ ' \+ data\.message \+ '

Signals have been resumed\. Monitor the system closely!'\);"""

new_alert = """alert('✅ ' + data.message + '\\\\n\\\\nSignals have been resumed. Monitor the system closely!');"""

content = re.sub(old_alert, new_alert, content)

# Write back
with open('app/templates/admin/brain_dashboard.html', 'w') as f:
    f.write(content)

print("✅ Fixed JavaScript syntax errors in brain_dashboard.html")
