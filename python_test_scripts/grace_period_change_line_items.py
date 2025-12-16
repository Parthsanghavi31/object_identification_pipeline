import requests
import json

def get_admin_access_token():
    url = "https://viatouchmedia-test.apigee.net/loyalty/users/login/viatouch-admin"

    headers = {
        "apikey": "GknyR08KAYdjDhlFcQj943eLoIqGKMa2",
        "grant_type": "client_credentials",
        "Content-Type": "application/json"
    }

    body = {
        "password": "Adm1nPa55"
    }

    response = requests.post(url, headers=headers, json=body)

    if response.status_code != 200:
        print(f"Login failed: {response.status_code} {response.text}")
        return None

    data = response.json()
    return data.get("access_token")

def update_line_items(access_token, transaction_id, payload):
    url = f"https://viatouchmedia-test.apigee.net/loyalty/orders/cv/{transaction_id}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.patch(url, headers=headers, json=payload)

        if response.status_code == 200:
            print("Line items updated successfully")
            print("Response:", response.text)
        else:
            print(f"Error {response.status_code}: {response.text}")

    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    admin_access_token = get_admin_access_token()
    print("Admin token:", admin_access_token)    
    transaction_id = "e7f66360-536f-4097-af2b-79c930fae194"

    payload = {
            "line_items": [
                {
                "shelf_row": 2,
                "shelf_column": 3,
                "quantity": 1,
                "op_type": "update",
                "cv_intent": "CORRECTION",
                "cv_confidence_level": "0.82"
                }               
            ]
            }
    update_line_items("0rX9I0ns3l5n7ndPUSOpcACIEg81", transaction_id, payload)
