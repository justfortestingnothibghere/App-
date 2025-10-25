# app.py
import os
import logging
import random
import string
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from asgiref.wsgi import WsgiToAsgi
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

def generate_random_string(length=12):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route('/create', methods=['GET', 'POST'])
def create_account():
    email = request.args.get('email') or request.form.get('email')
    if not email:
        return jsonify({"status": "failed", "message": "Email required"}), 400

    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        response = session.get('https://platform.cloudways.com/signup', timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        form = soup.find('form')
        if not form:
            return jsonify({"status": "failed", "message": "Signup form not found on the page."}), 500

        action = form.get('action', '')
        if not action.startswith('http'):
            action = urljoin(response.url, action)
        method = form.get('method', 'post').lower()

        data = {}
        user_details = {"email": email, "first_name": "Test", "last_name": "User"}
        for inp in form.find_all('input'):
            name = inp.get('name')
            if not name:
                continue
            if inp.get('type') == 'hidden':
                data[name] = inp.get('value', '')
            elif 'first' in name.lower() or 'fname' in name.lower():
                data[name] = 'Test'
            elif 'last' in name.lower() or 'lname' in name.lower():
                data[name] = 'User'
            elif 'email' in name.lower() or inp.get('type') == 'email':
                data[name] = email
            elif inp.get('type') == 'password' and 'confirm' not in name.lower():
                generated_password = generate_random_string()
                data[name] = generated_password
                user_details["password"] = generated_password
            elif 'confirm_password' in name.lower():
                data[name] = user_details["password"]  # Match the generated password

        # Handle dropdown selects
        # "I would best describe myself as" - default to "Developer"
        describe_select = form.find('select', attrs={'name': lambda x: x and 'describe' in x.lower() or 'user_type' in x.lower()})
        if describe_select and describe_select.get('name'):
            data[describe_select.get('name')] = 'Developer'

        # "My monthly hosting spending is" - default to "Less than $50"
        spend_select = form.find('select', attrs={'name': lambda x: x and 'spend' in x.lower() or 'hosting' in x.lower()})
        if spend_select and spend_select.get('name'):
            data[spend_select.get('name')] = 'Less than $50'

        if method == 'post':
            submit_response = session.post(action, data=data, timeout=15)
        else:
            submit_response = session.get(action, params=data, timeout=15)
        submit_response.raise_for_status()

        text_lower = submit_response.text.lower()
        success_indicators = [
            "activation email sent",
            "please check your email",
            "account created",
            "verification link",
            "check your email for verification"
        ]
        success = any(indicator in text_lower for indicator in success_indicators)

        if success:
            logging.info(f"Successful signup attempt for {email}")
            return jsonify({
                "status": "success",
                "message": "Signup completed, check your email.",
                "user_details": user_details
            })
        else:
            logging.warning(f"Signup attempt failed for {email}. Response snippet: {submit_response.text[:300]}...")
            return jsonify({"status": "failed", "message": f"Signup failed (possible validation error). Check logs. Response status: {submit_response.status_code}"})

    except requests.exceptions.RequestException as e:
        error_message = f"Network error during signup: {str(e)}"
        logging.error(f"Request error for {email}: {str(e)}")
        return jsonify({"status": "failed", "message": error_message}), 500
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        logging.error(f"Unexpected error for {email}: {str(e)}")
        return jsonify({"status": "failed", "message": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app_asgi = WsgiToAsgi(app)
    app.run(host='0.0.0.0', port=port, debug=True)
else:
    app_asgi = WsgiToAsgi(app)
