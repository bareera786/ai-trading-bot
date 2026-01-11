from playwright.sync_api import sync_playwright

def test_mobile_view():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 375, "height": 812},  # iPhone X dimensions
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        )
        page = context.new_page()
        
        # Use port 5002 for the Flask server
        page.goto("http://localhost:5002")
        
        # Take a screenshot of the mobile view
        page.screenshot(path="mobile_view.png")
        print("Screenshot of mobile view saved as 'mobile_view.png'")
        
        browser.close()

if __name__ == "__main__":
    test_mobile_view()