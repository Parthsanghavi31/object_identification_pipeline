import requests
import os
import json
import re
from collections import defaultdict, Counter

# Testing with teh update and delete Operation mode as we don't want to upcharge

def select_line_items(cv_activities, config_products, json_file_path):
    """
    Build a PATCH body that:
      - sets each existing line item's quantity to the value from picked_counter (downcharge only)
      - if picked says 0 => delete the line item (no PATCH with quantity:0)
      - if picked >= current => no-op (never upcharge)
      - never add new items

    Returns: picked_counter, bought_counter, body
    """
    with open(json_file_path, 'r') as file:
        activity = json.load(file)

    # --- helpers ---
    def clean_name(name):
        return ''.join(re.findall(r'[a-zA-Z]+', name)).lower()

    # --- build picked_counter (net pickups) ---
    product_counts = defaultdict(lambda: {'USER_PICKUP': 0, 'USER_PUTBACK': 0})
    for item in cv_activities:
        for action, product in item.items():
            product_counts[clean_name(product)][action] += 1

    picked_counter = Counter()
    for prod, acts in product_counts.items():
        net = acts['USER_PICKUP'] - acts['USER_PUTBACK']
        if net > 0:
            picked_counter[prod] = net

    # --- existing ticket snapshot + bought_counter for telemetry ---
    line_items = activity.get('line_items', []) or []
    # bought_counter = Counter()
    # for li in line_items:
    #     pname = clean_name(li.get("product_name", ""))
    #     bought_counter[pname] += int(li.get("quantity", 0))

    # --- build downcharge-only ops ---
    ops = []
    for li in line_items:
        pname_clean = clean_name(li.get("product_name", ""))
        if pname_clean in config_products:
            current_qty = int(li.get("quantity", 0))
            target_qty = picked_counter.get(pname_clean, 0)  # default to 0 if not picked

            row = li.get("shelf_row")
            col = li.get("shelf_column")

            if target_qty == 0:
                if current_qty > 0:
                    # reduce to zero via delete (can't PATCH quantity:0)
                    ops.append({
                        "quantity": current_qty,
                        "shelf_row": row,
                        "shelf_column": col,
                        "op_type": "delete"
                    })
                # if current_qty already 0, no-op
            elif target_qty < current_qty:
                # downcharge to exactly picked quantity
                ops.append({
                    "quantity": int(target_qty),
                    "shelf_row": row,
                    "shelf_column": col,
                    "op_type": "update"
                })

    body = {"line_items": ops}
    print(body)
    return picked_counter, body

def change_line_items(logger, access_token, base_url, transaction_id, body):
    url = f"{base_url}/orders/{transaction_id}"
    headers= {
        "Authorization" : f"Bearer {access_token}",
        "Content-Type" : "application/json"
    }
   
    response = requests.patch(url, headers=headers, json=body)
    if response.status_code == 200:
        logger.info(f"Grace Period: PATCH successful")
    else:
        logger.error(f"{response.status_code} {response.text}")

def get_updated_line_items(logger, base_url, transaction_id):
    url = f"{base_url}/orders/{transaction_id}"
    request = requests.get(url)
    logger.info(f"The Updated Line Items: {request.json()}")
    # print(request.json())

def main():
    base_url = "https://viatouchmedia-prod.apigee.net/loyalty"
    access_token = "gFenQfoMaIyU41AvpraZAc8DgZ4Q"
    transaction_id = "548ed252-14b8-42c1-9bae-1b5b47935cdd"
    
    json_file_path = "/home/raspberrypi5/camera-preview-pipeline/post_archive/user_activities.json"
    
    cv_activities = [
    {"USER_PICKUP": "Quest-chips Loaded-Taco"},
    {"USER_PICKUP": "Quest-chips Loaded-Taco"},
    {"USER_PICKUP": "Quest-chips Loaded-Taco"},
    {"USER_PUTBACK": "Quest-chips Loaded-Taco"}
    ]
    
    # config_products = ["Quest-chips Chili lime", "Quest-chips Loaded-Taco", "Legendary Protein Chip - Ranch"]
    # picked_product, body = select_line_items(cv_activities, config_products, json_file_path)
    # print(picked_product)
    # change_line_items(access_token, base_url, transaction_id, body)
    # get_updated_line_items(base_url, transaction_id)
    url = f"{base_url}/orders/{transaction_id}"
    request = requests.get(url)
    print(request.json())
    
if __name__ == '__main__':
    main()