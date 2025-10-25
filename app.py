# app.py
import os
import logging
import random
import string
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from asgiref.wsgi import WsgiToAsgi

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
        response = session.get('https://platform.cloudways.com/signup', timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        form = soup.find('form')
        if not form:
            return jsonify({"status": "failed", "message": "Signup form not found on the page."}), 500

        action = form.get('action', '')
        if not action.startswith('http'):
            from urllib.parse import urljoin
            action = urljoin(response.url, action)
        method = form.get('method', 'post').lower()

        data = {}
        user_details = {"email": email}
        for inp in form.find_all('input'):
            name = inp.get('name')
            if not name:
                continue
            if inp.get('type') == 'hidden':
                data[name] = inp.get('value', '')
            elif 'email' in name.lower() or inp.get('type') == 'email':
                data[name] = email

        # Fill name if present
        name_input = form.find('input', attrs={'name': lambda x: x and 'name' in x.lower()})
        if name_input and name_input.get('name'):
            data[name_input.get('name')] = 'Test User'
            user_details["name"] = 'Test User'

        # Fill password if present
        pwd_input = form.find('input', attrs={'type': 'password'})
        if pwd_input and pwd_input.get('name'):
            generated_password = generate_random_string()
            data[pwd_input.get('name')] = generated_password
            user_details["password"] = generated_password

        if method == 'post':
            submit_response = session.post(action, data=data, timeout=10)
        else:
            submit_response = session.get(action, params=data, timeout=10)
        submit_response.raise_for_status()

        # Check for success indicators
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
            logging.warning(f"Signup attempt failed for {email}: {submit_response.text[:200]}...")
            return jsonify({"status": "failed", "message": "Signup failed or form submission issue."})

    except requests.exceptions.RequestException as e:
        logging.error(f"Request error for {email}: {str(e)}")
        return jsonify({"status": "failed", "message": "Network error during signup."}), 500
    except Exception as e:
        logging.error(f"Unexpected error for {email}: {str(e)}")
        return jsonify({"status": "failed", "message": "Unexpected error."}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app_asgi = WsgiToAsgi(app)
    app.run(host='0.0.0.0', port=port, debug=True)
else:
    app_asgi = WsgiToAsgi(app)
