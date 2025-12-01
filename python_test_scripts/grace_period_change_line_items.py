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

def update_line_items(access_token, transaction_id):
    url = f"https://viatouchmedia-test.apigee.net/loyalty/orders/cv/{transaction_id}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "line_items": [
            {
            "shelf_row": 3,
            "shelf_column": 6,
            "quantity": 2,
            "op_type": "delete",
            "cv_intent": "CORRECTION",
            "cv_confidence_level": "0.82"
            }
        ]
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
    transaction_id = "f69176f3-4c1a-449c-9107-484f20b48829"


    update_line_items("AqmjhXOPyZ73Fk8yfLJz5HyWidwS", transaction_id)
