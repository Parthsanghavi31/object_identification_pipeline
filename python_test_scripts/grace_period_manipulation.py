import requests
import os
import json
import re
from collections import defaultdict, Counter

def change_line_items(access_token, base_url, transaction_id, body):
    url = f"{base_url}/orders/{transaction_id}"
    headers= {
        "Authorization" : f"Bearer {access_token}",
        "Content-Type" : "application/json"
    }
    print(body)
    response = requests.patch(url, headers=headers, json=body)
    if response.status_code == 200:
        print(f"Grace Period: PATCH successful")
    else:
        print(f"{response.status_code} {response.text}")

def get_updated_line_items(base_url, transaction_id):
    url = f"{base_url}/orders/{transaction_id}"
    request = requests.get(url)
    print(f"The Updated Line Items: {request.json()}")
    # print(request.json())

def main():
    base_url = "https://viatouchmedia-prod.apigee.net/loyalty"
    access_token = "K1zHvdHAuBYCykyDoMPkVZNF1NbA"
    transaction_id = "4b984408-8ddd-4a12-b999-10c900b03d2e"
    body = {
        "line_items": [
            {
                # add to shelf that is already added
                "quantity": 1,
                "shelf_row": 2,
                "shelf_column": 5,
                "op_type": "add"
            }
            # {
            #     # update shelf with minimal fields
            #     "quantity": 1,
            #     "shelf_row": 2,
            #     "shelf_column": 1,
            #     "op_type": "update"
            # }
        ]
    }
    change_line_items(access_token, base_url, transaction_id, body)
    get_updated_line_items(base_url, transaction_id)
    
if __name__ == '__main__':
    main()