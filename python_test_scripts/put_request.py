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
          "machine_id": "aee23560-60c4-409f-993e-abccc502432e",
        "machine_name": "PF - Queens (Woodside), NY Sundries",
        "report_id": "95c13bbd-363a-43a5-a63b-77d8ace07281",
        "invoice_id": "57deaf12-863f-48cd-bfaa-4888d89e909b",
        "payment_type": "UNAVAILABLE",
        "transaction_start_date": 1762961529000,
        "transaction_start_date_str": "2025-11-12:21:32:09",
        "transaction_cv_media_url": "https://viatouchmedia-prod.apigee.net/loyalty-images/cv_processed_media/20251112/210926d4-df88-4b0b-954a-858831a84f3c/57deaf12-863f-48cd-bfaa-4888d89e909b/media_processed.mp4",
        "transaction_cv_media_url_list": [
            "https://viatouchmedia-prod.apigee.net/loyalty-images/cv_processed_media/20251112/210926d4-df88-4b0b-954a-858831a84f3c/57deaf12-863f-48cd-bfaa-4888d89e909b/media_processed.mp4",
            "https://viatouchmedia-prod.apigee.net/loyalty-images/cv_processed_media/20251112/210926d4-df88-4b0b-954a-858831a84f3c/57deaf12-863f-48cd-bfaa-4888d89e909b/media_processed_masked.mp4",
            "https://viatouchmedia-prod.apigee.net/loyalty-images/cv_processed_media/20251112/672cd835-fde4-4312-ae1a-16a135505efa/57deaf12-863f-48cd-bfaa-4888d89e909b/media_processed.mp4",
            "https://viatouchmedia-prod.apigee.net/loyalty-images/cv_processed_media/20251112/672cd835-fde4-4312-ae1a-16a135505efa/57deaf12-863f-48cd-bfaa-4888d89e909b/media_processed_masked.mp4"
        ],
        "transaction_duration_seconds": 9,
        "activities": [
            {
                "id": "c336984e-94f0-4c8f-bc7a-5f80f1a16f53",
                "user_activity_type": "DOOR_OPENED",
                "row": 0,
                "column": 0,
                "count": 0,
                "in_use_count": 0,
                "previous_count": 0,
                "activity_time": "2025-11-12:15:32:09",
                "activity_time_str": "2025-11-12:18:32:09"
            },
            {
                "id": "17ab94fe-d202-4a47-9578-bed9c0b1e089",
                "user_activity_type": "USER_PUTBACK",
                "row": 2,
                "column": 1,
                "count": 5,
                "in_use_count": 0,
                "previous_count": 5,
                "product_id": "0ad58880-f755-411d-a988-7e2209e88d9f",
                "product_name": "Quest Chips - Loaded Taco",
                "activity_time": "2025-11-12:15:32:13",
                "activity_time_str": "2025-11-12:18:32:13",
                "is_validation": True,
                "price": 375,
                "feedback": "True"
            },
            {
                "id": "39b5bc1d-a708-4abc-9ded-1cc3ac29861c",
                "user_activity_type": "USER_PICKUP",
                "row": 2,
                "column": 1,
                "count": 6,
                "in_use_count": 0,
                "previous_count": 6,
                "product_id": "0ad58880-f755-411d-a988-7e2209e88d9f",
                "product_name": "Quest Chips - Loaded Taco",
                "activity_time": "2025-11-12:15:32:13",
                "activity_time_str": "2025-11-12:18:32:13",
                "is_validation": True,
                "price": 375,
                "feedback": "True"
            },
            {
                "id": "a2dabacf-ef58-4d6e-a91f-192f56b2ffff",
                "user_activity_type": "USER_PICKUP",
                "row": 2,
                "column": 5,
                "count": 5,
                "in_use_count": 0,
                "previous_count": 5,
                "product_id": "b674e462-8850-4eb1-8aea-fb714e816aac",
                "product_name": "Legendary Protein Chip - Ranch",
                "activity_time": "2025-11-12:15:32:17",
                "activity_time_str": "2025-11-12:18:32:17",
                "is_validation": True,
                "price": 375,
                "post_processing_cv": True,
                "feedback": "True"
            },
            {
                "id": "c7817580-5ba9-45ec-b71e-93eeafaa8b30",
                "user_activity_type": "DOOR_CLOSED",
                "row": 0,
                "column": 0,
                "count": 0,
                "in_use_count": 0,
                "previous_count": 0,
                "activity_time": "2025-11-12:15:32:17",
                "activity_time_str": "2025-11-12:18:32:17"
            },
            {
                "id": "caed8f17-ad44-4cf0-8b86-5b5c1c15bd56",
                "user_activity_type": "PRODUCT_MEDIA",
                "row": 0,
                "column": 0,
                "count": 0,
                "in_use_count": 0,
                "previous_count": 0,
                "media_id": "http://192.168.1.140:3000/3d968018-02c8-4c81-a3ac-e87af1cf9048",
                "activity_time": "2025-11-12:15:32:18",
                "activity_time_str": "2025-11-12:18:32:18"
            }
        ]
    }

access_token = "RdcjL0vshXMRVmsGGuxGmH1v2Zqd"
transaction_id = "59186f2c-4c43-4e64-91f9-8cc0c0196ddf"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {access_token}"
} 
response = requests.put(url, headers=headers, data=json.dumps(payload))

print("status Code: ", response.status_code)
print('response: ', response.json())
   
# base_url = "https://viatouchmedia-prod.apigee.net/loyalty"
# body = {
#     "line_items": [
#         {
#             # add to shelf that is already added
#             "quantity": 1,
#             "shelf_row": 2,
#             "shelf_column": 3,
#             "op_type": "update"
#         }
#         # {
#         #     # update shelf with minimal fields
#         #     "quantity": 1,
#         #     "shelf_row": 2,
#         #     "shelf_column": 1,
#         #     "op_type": "update"
#         # }
#     ]
# }
# change_line_items(access_token, base_url, transaction_id, body)
# get_updated_line_items(base_url, transaction_id)