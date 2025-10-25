# app.py (Selenium Version)
import os
import logging
import random
import string
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from asgiref.wsgi import WsgiToAsgi

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

def generate_random_string(length=12):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    return webdriver.Chrome(options=chrome_options)

@app.route('/create', methods=['GET', 'POST'])
def create_account():
    email = request.args.get('email') or request.form.get('email')
    if not email:
        return jsonify({"status": "failed", "message": "Email required"}), 400

    driver = None
    try:
        driver = create_driver()
        driver.get('https://platform.cloudways.com/signup')
        
        # Wait for form to load (or Cloudflare challenge to pass)
        wait = WebDriverWait(driver, 20)
        form = wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
        
        # Fill fields using Selenium
        user_details = {"email": email, "first_name": "Test", "last_name": "User"}
        generated_password = generate_random_string()
        user_details["password"] = generated_password

        # First name
        first_name_input = driver.find_element(By.NAME, 'first_name')  # Adjust if name differs
        first_name_input.send_keys('Test')

        # Last name
        last_name_input = driver.find_element(By.NAME, 'last_name')
        last_name_input.send_keys('User')

        # Email
        email_input = driver.find_element(By.NAME, 'email')
        email_input.send_keys(email)

        # Password
        pwd_input = driver.find_element(By.NAME, 'password')
        pwd_input.send_keys(generated_password)

        # Confirm password
        confirm_input = driver.find_element(By.NAME, 'confirm_password')
        confirm_input.send_keys(generated_password)

        # Dropdown: Describe myself
        describe_select = driver.find_element(By.NAME, 'user_type')  # Adjust name
        from selenium.webdriver.support.ui import Select
        Select(describe_select).select_by_visible_text('Developer')

        # Dropdown: Monthly spending
        spend_select = driver.find_element(By.NAME, 'monthly_spending')  # Adjust name
        Select(spend_select).select_by_visible_text('Less than $50')

        # Submit
        submit_btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"]')
        submit_btn.click()

        # Wait for response and check for success
        wait.until(lambda d: "check your email" in d.page_source.lower() or "activation" in d.page_source.lower() or "verification" in d.page_source.lower())
        
        page_source = driver.page_source.lower()
        success_indicators = ["activation email sent", "please check your email", "account created", "verification link"]
        success = any(indicator in page_source for indicator in success_indicators)

        if success:
            logging.info(f"Successful signup attempt for {email}")
            return jsonify({
                "status": "success",
                "message": "Signup completed, check your email.",
                "user_details": user_details
            })
        else:
            logging.warning(f"Signup attempt failed for {email}. Page snippet: {driver.page_source[:300]}...")
            return jsonify({"status": "failed", "message": "Signup failed or no success indicator found."})

    except TimeoutException:
        logging.error(f"Timeout waiting for form for {email}")
        return jsonify({"status": "failed", "message": "Timeout: Anti-bot challenge or slow load."}), 500
    except WebDriverException as e:
        logging.error(f"Selenium error for {email}: {str(e)}")
        return jsonify({"status": "failed", "message": f"Browser error: {str(e)} (Check ChromeDriver setup)."}), 500
    except Exception as e:
        logging.error(f"Unexpected error for {email}: {str(e)}")
        return jsonify({"status": "failed", "message": f"Unexpected error: {str(e)}"}), 500
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app_asgi = WsgiToAsgi(app)
    app.run(host='0.0.0.0', port=port, debug=True)
else:
    app_asgi = WsgiToAsgi(app)
