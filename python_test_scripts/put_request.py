# "post_processing_cv": True,
import requests
import json
url = "https://viatouchmedia-prod.apigee.net/loyalty/machines/activity"



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
    
payload = {
  "user_activity_request_type": "ORDER_ACTIVITY_REPORT",
        "machine_id": "d9607d17-d101-4f6e-ba27-8fa6e11f8833",
        "machine_name": "Parthedo",
        "report_id": "f49e80fd-278f-4294-82ed-5d0562c9e924",
        "invoice_id": "59186f2c-4c43-4e64-91f9-8cc0c0196ddf",
        "payment_type": "APPLE_PAY",
        "transaction_start_date": 1761057063000,
        "transaction_start_date_str": "2025-10-21:20:31:03",
        "transaction_duration_seconds": 20,
        "activities": [
            {
                "id": "94f76368-1f0b-4d96-908b-fd02724c4f2b",
                "user_activity_type": "USER_PUTBACK",
                "row": 2,
                "column": 1,
                "count": 5,
                "in_use_count": 1,
                "previous_count": 4,
                "product_id": "00de18a3-f2e5-4cfc-b3a2-1d9a1912c405",
                "product_name": "Quest Chips - Loaded Taco",
                "activity_time": "2025-10-21:14:31:03",
                "activity_time_str": "2025-10-21:17:31:03",
                "is_validation": True,
                "price": 375
            },
            {
                "id": "9deed7dd-6abb-44d6-b04e-175ffcaebe8f",
                "user_activity_type": "DOOR_OPENED",
                "row": 0,
                "column": 0,
                "count": 0,
                "in_use_count": 0,
                "previous_count": 0,
                "activity_time": "2025-10-21:14:31:04",
                "activity_time_str": "2025-10-21:17:31:04"
            },
            {
                "id": "9ba1930f-0db6-4991-99d7-d83355ddb323",
                "user_activity_type": "USER_PICKUP",
                "row": 2,
                "column": 1,
                "count": 4,
                "in_use_count": 1,
                "previous_count": 5,
                "product_id": "00de18a3-f2e5-4cfc-b3a2-1d9a1912c405",
                "product_name": "Quest Chips - Loaded Taco",
                "activity_time": "2025-10-21:14:31:05",
                "activity_time_str": "2025-10-21:17:31:05",
                "is_validation": True,
                "price": 375
            },
            {
                "id": "160a0777-bdd5-47cb-a8d8-d5c9cb0f7a8e",
                "user_activity_type": "USER_PUTBACK",
                "row": 2,
                "column": 1,
                "count": 5,
                "in_use_count": 1,
                "previous_count": 4,
                "product_id": "00de18a3-f2e5-4cfc-b3a2-1d9a1912c405",
                "product_name": "Quest Chips - Loaded Taco",
                "activity_time": "2025-10-21:14:31:07",
                "activity_time_str": "2025-10-21:17:31:07",
                "is_validation": True,
                "price": 375
            },
            {
                "id": "8b601ba4-1d2e-4f38-ad17-b23db847fa63",
                "user_activity_type": "USER_PICKUP",
                "row": 2,
                "column": 3,
                "count": 5,
                "in_use_count": 1,
                "previous_count": 6,
                "product_id": "6e5d77c6-62b4-4042-858e-9deb543320e8",
                "product_name": "Quest Chips Chili Lime",
                "activity_time": "2025-10-21:14:31:08",
                "activity_time_str": "2025-10-21:17:31:08",
                "is_validation": True,
                "post_processing_cv": True,
                "price": 375
            },
            {
                "id": "061f5a14-4499-42f6-a393-02e08235c6ae",
                "user_activity_type": "USER_PICKUP",
                "row": 2,
                "column": 3,
                "count": 4,
                "in_use_count": 1,
                "previous_count": 5,
                "product_id": "6e5d77c6-62b4-4042-858e-9deb543320e8",
                "product_name": "Quest Chips Chili Lime",
                "activity_time": "2025-10-21:14:31:09",
                "activity_time_str": "2025-10-21:17:31:09",
                "is_validation": True,
                "price": 375
            },
            {
                "id": "d0f9e158-5cc6-4f7f-9786-45224a07402d",
                "user_activity_type": "USER_PICKUP",
                "row": 2,
                "column": 1,
                "count": 4,
                "in_use_count": 1,
                "previous_count": 5,
                "product_id": "00de18a3-f2e5-4cfc-b3a2-1d9a1912c405",
                "product_name": "Quest Chips - Loaded Taco",
                "activity_time": "2025-10-21:14:31:09",
                "activity_time_str": "2025-10-21:17:31:09",
                "is_validation": True,
                "price": 375
            },
            {
                "id": "0499707c-dda4-4625-8211-d537a9edbc80",
                "user_activity_type": "USER_PICKUP",
                "row": 4,
                "column": 2,
                "count": 1,
                "in_use_count": 1,
                "previous_count": 2,
                "product_id": "dea91bb0-fc62-4c58-a0ad-fae928286627",
                "product_name": "Skullcandy DIME 3",
                "activity_time": "2025-10-21:14:31:12",
                "activity_time_str": "2025-10-21:17:31:12",
                "is_validation": True,
                "post_processing_cv": True,
                "price": 2999
            },
            {
                "id": "27b9525e-4c28-4d0f-9c8b-40c37aaee730",
                "user_activity_type": "USER_PUTBACK",
                "row": 2,
                "column": 1,
                "count": 5,
                "in_use_count": 1,
                "previous_count": 4,
                "product_id": "00de18a3-f2e5-4cfc-b3a2-1d9a1912c405",
                "product_name": "Quest Chips - Loaded Taco",
                "activity_time": "2025-10-21:14:31:12",
                "activity_time_str": "2025-10-21:17:31:12",
                "is_validation": True,
                "price": 375
            },
            {
                "id": "e47cbbf7-ed15-4230-bd57-d8e42f3b88f4",
                "user_activity_type": "USER_PICKUP",
                "row": 2,
                "column": 1,
                "count": 4,
                "in_use_count": 1,
                "previous_count": 5,
                "product_id": "00de18a3-f2e5-4cfc-b3a2-1d9a1912c405",
                "product_name": "Quest Chips - Loaded Taco",
                "activity_time": "2025-10-21:14:31:13",
                "activity_time_str": "2025-10-21:17:31:13",
                "is_validation": True,
                "price": 375
            },
            {
                "id": "2c5dcac1-37cc-46ea-953f-bb134ca844d4",
                "user_activity_type": "USER_PUTBACK",
                "row": 2,
                "column": 1,
                "count": 5,
                "in_use_count": 1,
                "previous_count": 4,
                "product_id": "00de18a3-f2e5-4cfc-b3a2-1d9a1912c405",
                "product_name": "Quest Chips - Loaded Taco",
                "activity_time": "2025-10-21:14:31:17",
                "activity_time_str": "2025-10-21:17:31:17",
                "is_validation": True,
                "price": 375
            },
            {
                "id": "d05b561f-96c9-47fc-bbf3-8d7da6be667b",
                "user_activity_type": "USER_PICKUP",
                "row": 2,
                "column": 1,
                "count": 4,
                "in_use_count": 1,
                "previous_count": 5,
                "product_id": "00de18a3-f2e5-4cfc-b3a2-1d9a1912c405",
                "product_name": "Quest Chips - Loaded Taco",
                "activity_time": "2025-10-21:14:31:18",
                "activity_time_str": "2025-10-21:17:31:18",
                "is_validation": True,
                "price": 375
            },
            {
                "id": "63dbfd03-a580-4959-83a4-2a8e852f8b2e",
                "user_activity_type": "DOOR_CLOSED",
                "row": 0,
                "column": 0,
                "count": 0,
                "in_use_count": 0,
                "previous_count": 0,
                "activity_time": "2025-10-21:14:31:21",
                "activity_time_str": "2025-10-21:17:31:21"
            },
            {
                "id": "5bb868ae-618d-442e-8a0e-b5b2f64fe9ea",
                "user_activity_type": "USER_PUTBACK",
                "row": 2,
                "column": 3,
                "count": 4,
                "in_use_count": 1,
                "previous_count": 3,
                "product_id": "6e5d77c6-62b4-4042-858e-9deb543320e8",
                "product_name": "Quest Chips Chili Lime",
                "activity_time": "2025-10-21:14:31:23",
                "activity_time_str": "2025-10-21:17:31:23",
                "is_validation": True,
                "price": 375
            }
        ]
    }

access_token = "HdbyRPBNHgp3VPiZpwtT44JC7AW5"
transaction_id = "59186f2c-4c43-4e64-91f9-8cc0c0196ddf"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {access_token}"
} 
response = requests.put(url, headers=headers, data=json.dumps(payload))

print("status Code: ", response.status_code)
print('response: ', response.json())
   
base_url = "https://viatouchmedia-prod.apigee.net/loyalty"
body = {
    "line_items": [
        {
            # add to shelf that is already added
            "quantity": 1,
            "shelf_row": 2,
            "shelf_column": 3,
            "op_type": "update"
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