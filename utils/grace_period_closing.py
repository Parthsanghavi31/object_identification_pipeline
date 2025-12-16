import requests
import json
import logging

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


def close_grace_period(logger, transaction_id):
    admin_access_token = get_admin_access_token()
    url = f"https://viatouchmedia-test.apigee.net/loyalty/orders/{transaction_id}/complete"
    headers = {
        "Authorization": f"Bearer {admin_access_token}",
        "Content-Type": "application/json"
    }

    payload = {}
    if admin_access_token:
        try:
            response = requests.put(url, headers=headers, json=payload)

            if response.status_code == 200:
                logger.info("Grace Period closed successfully")
            else:
                logger.info(f"Error {response.status_code}: {response.text}")

        except Exception as e:
            logger.info(f"Request failed: {e}")
    else:
        logger.error("No access token found.")


if __name__ == "__main__":
    admin_access_token = get_admin_access_token()
    print("Admin token:", admin_access_token)
    logger = logging.getLogger()
    transaction_id = "4f276f6e-2c28-4cc8-b5ec-454b2f675698"

    # Only call if token came properly
    if admin_access_token:
        close_grace_period(logger, transaction_id)
