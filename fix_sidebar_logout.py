#!/usr/bin/env python3
"""
Apply sidebar and logout fixes automatically
"""

import re

def fix_sidebar_logout():
    print("🔧 Applying sidebar and logout fixes...")
    
    with open('ai_ml_auto_bot_final.py', 'r') as f:
        content = f.read()
    
    # Fix 1: Update logout route to redirect instead of JSON
    old_logout = """@app.route('/logout')
def logout():
    logout_user()
    # Add aggressive cache control to logout redirect
    return jsonify({'status': 'success', 'message': 'Logged out successfully'})"""
    
    new_logout = """@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))"""
    
    if old_logout in content:
        content = content.replace(old_logout, new_logout)
        print("✅ Fixed logout route")
    else:
        print("⚠️  Logout route already fixed or different")
    
    # Fix 2: Update JavaScript
    js_start = content.find('<script>')
    js_end = content.find('</script>', js_start) + 9
    
    if js_start != -1 and js_end != -1:
        new_js = """<script>
// Fix sidebar and logout functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOM loaded - initializing sidebar and logout');
    
    // Mobile menu toggle
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (mobileMenuToggle && sidebar) {
        console.log('✅ Found mobile menu toggle and sidebar');
        
        mobileMenuToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('📱 Mobile menu toggle clicked');
            sidebar.classList.toggle('open');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function(e) {
            if (window.innerWidth <= 768) {
                if (!sidebar.contains(e.target) && 
                    !mobileMenuToggle.contains(e.target) && 
                    sidebar.classList.contains('open')) {
                    console.log('📱 Closing sidebar (clicked outside)');
                    sidebar.classList.remove('open');
                }
            }
        });
    } else {
        console.log('❌ Mobile menu elements not found:', {
            toggle: !!mobileMenuToggle,
            sidebar: !!sidebar
        });
    }
    
    // Fix logout button
    const logoutBtn = document.querySelector('button[onclick="logout()"]');
    if (logoutBtn) {
        console.log('✅ Found logout button');
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    }
});

// Global logout function - FIXED
async function logout() {
    console.log('🚪 Logout initiated');
    if (confirm('Are you sure you want to logout?')) {
        try {
            const response = await fetch('/logout', {
                method: 'GET',
                credentials: 'same-origin'
            });
            
            // Since we changed to redirect, just redirect
            window.location.href = '/login';
            
        } catch (error) {
            console.error('Logout error:', error);
            alert('Logout failed. Please try again.');
        }
    }
}

// Add CSS for sidebar open state if missing
const style = document.createElement('style');
style.textContent = `
    .sidebar.open {
        transform: translateX(0);
        opacity: 1;
        visibility: visible;
    }
    
    @media (max-width: 768px) {
        .sidebar {
            transform: translateX(-100%);
            transition: transform 0.3s ease;
        }
        
        .sidebar.open {
            transform: translateX(0);
        }
    }
    
    .mobile-menu-toggle {
        cursor: pointer;
        z-index: 1001;
    }
`;
document.head.appendChild(style);
</script>"""
        
        content = content[:js_start] + new_js + content[js_end:]
        print("✅ Fixed JavaScript")
    
    # Fix 3: Update mobile menu button
    content = content.replace(
        'onclick="toggleMobileMenu()"', 
        ''
    )
    print("✅ Fixed mobile menu button")
    
    # Write updated content
    with open('ai_ml_auto_bot_final.py', 'w') as f:
        f.write(content)
    
    print("🎉 All sidebar and logout fixes applied!")

if __name__ == '__main__':
    fix_sidebar_logout()