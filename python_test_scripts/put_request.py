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

 
access_token = "AqmjhXOPyZ73Fk8yfLJz5HyWidwS"
transaction_id = "59186f2c-}4c43-4e64-91f9-8cc0c0196ddf"
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