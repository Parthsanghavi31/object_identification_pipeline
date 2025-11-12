import requests
from collections import defaultdict, Counter
import re, json
import logging
from utils.grace_period_endpoint import *
from utils import config
from utils import login

def sms_alert(logger, json_file, cv_activities, post_transid, config_products):
    """
    Sends a discrepancy alert via POST request. Returns True if successful, else False.
    """
    
    with open(json_file, 'r') as file:
        activity = json.load(file)
    
    report_id = activity['user_activity_instance']['report_id']
    vicki_app = 'http://192.168.1.140:8085/tsv/flashapi'

    # Function to clean product names (keep only alphabets, lowercase)
    def clean_name(name):
        return ''.join(re.findall(r'[a-zA-Z]+', name)).lower()

    # Count pickups and putbacks
    product_counts = defaultdict(lambda: {'USER_PICKUP': 0, 'USER_PUTBACK': 0})
    
    for item in cv_activities:
        for action, product in item.items():
            cleaned = clean_name(product)
            product_counts[cleaned][action] += 1

    # Compute net picked products
    picked_products = []
    for product, actions in product_counts.items():
        net_quantity = actions['USER_PICKUP'] - actions['USER_PUTBACK']
        if net_quantity > 0:
            picked_products.extend([product] * net_quantity)

    line_items = activity.get('line_items', [])
    if line_items:
        bought_products = [
            clean_name(item["product_name"])
            for item in line_items
            for _ in range(item["quantity"])
        ]
    else:
        bought_products = []
        
    config_products_comibined = config_products['0'] + config_products['1']
    print(config_products_comibined)
    config_products_cleaned = [clean_name(prd) for prd in config_products_comibined]
    bought_product_cleaned = [product for product in bought_products if product in config_products_cleaned]
    logger.info(f"Line items: {line_items}")
    logger.info(f"Filtered bought products: {bought_product_cleaned}")
    
    # Step 3: Compare both
    picked_counter = Counter(picked_products)
    bought_counter = Counter(bought_product_cleaned)

    logger.info(f"Picked Products : {picked_counter}")
    logger.info(f"Bought Products : {bought_counter}")
    
    print(f"Bought Counter: {bought_counter}")

    if picked_counter == bought_counter:    
        logger.info("Picked products match the bought products.")
        
    else:
        #___________________________________________Downcharge_______________________________________________________#
        
        # --- build downcharge-only ops ---
        logger.info("Down-charging the Products in Grace Period time")
        ops = []
        for li in line_items:
            pname_clean = clean_name(li.get("product_name", ""))
            if pname_clean in config_products_cleaned:
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
        base_loyalty_url = "https://viatouchmedia-prod.apigee.net/loyalty"
        base_local_url, machine_id, machine_token, machine_api_key = login.get_custom_machine_settings(config.vicki_app, logger)
        access_token = login.get_current_access_token(base_local_url, machine_id, machine_token, machine_api_key, logger)
        # change_line_items(logger, access_token, base_loyalty_url, post_transid, body)
        # get_updated_line_items(logger, base_loyalty_url, post_transid)
        
        #_____________________________________________________________________________________________________________#
        
        logger.info("Mismatch found between picked and bought products. Sending Alert")
        dashboard_url = f'https://dashboard.getvicki.com/reports/undefined/invoice/{post_transid}/activity/{report_id}'
        payload = f'["CreateSMSText", "{"PF Conference Sundries Machine - Mismatch found between picked and bought products. Please review it!", (dashboard_url)}"]'

        try:
            response = requests.post(url=vicki_app, data=payload)
            if response.status_code == 200:
                logger.info(f"Alert sent successfully : The response is {response}" )
                return True
        except Exception as e:
            logger.error(f"Error sending SMS alert: {e}")
            
    return picked_counter, bought_counter

def recording_successful(logger, json_file_path, transaction_number):

    with open(json_file_path, 'r') as file:
        activity = json.load(file)
    
    report_id = activity['user_activity_instance']['report_id']
    vicki_app = 'http://192.168.1.140:8085/tsv/flashapi'

    dashboard_url = f'https://dashboard.getvicki.com/reports/undefined/invoice/{transaction_number}/activity/{report_id}'
    payload = f'["CreateSMSText", "{"PF Conference Sundries Machine - Transaction  was recorded successfully. Currently it is being processed, please wait a few minutes to see the final charge", (dashboard_url)}"]'

    try:
        response = requests.post(url=vicki_app, data=payload)
        if response.status_code == 200:
            logger.info(f"Video was recorded successfully : The response is {response}" )
            return True
    except Exception as e:
        logger.error(f"SMS Error sending recording successful alert: {e}")


def transaction_too_big_alert(logger, json_file_path, transaction_number):

    with open(json_file_path, 'r') as file:
        activity = json.load(file)
    
    report_id = activity['user_activity_instance']['report_id']
    vicki_app = 'http://192.168.1.140:8085/tsv/flashapi'

    dashboard_url = f'https://dashboard.getvicki.com/reports/undefined/invoice/{transaction_number}/activity/{report_id}'
    payload = f'["CreateSMSText", "{"PF Conference Sundries Machine - Transaction time is too long, the cv algorithm cant process it. Please review it manually!", (dashboard_url)}"]'

    try:
        response = requests.post(url=vicki_app, data=payload)
        if response.status_code == 200:
            logger.info(f"CV Algorithm Failure alert sent successfully : The response is {response}" )
            return True
    except Exception as e:
        logger.error(f"SMS Error sending CV Algorithm faliure alert: {e}")

def transaction_failure_alert(logger, json_file_path, transaction_number):

    with open(json_file_path, 'r') as file:
        activity = json.load(file)
    
    report_id = activity['user_activity_instance']['report_id']
    vicki_app = 'http://192.168.1.140:8085/tsv/flashapi'

    dashboard_url = f'https://dashboard.getvicki.com/reports/undefined/invoice/{transaction_number}/activity/{report_id}'
    payload = f'["CreateSMSText", "{"PF Conference Sundries Machine - CV Alogrithm didnt complete and Failed(Its in failed_upload_dir). Please review it!", (dashboard_url)}"]'

    try:
        response = requests.post(url=vicki_app, data=payload)
        if response.status_code == 200:
            logger.info(f"CV Algorithm Failure alert sent successfully : The response is {response}" )
            return True
    except Exception as e:
        logger.error(f"SMS Error sending CV Algorithm faliure alert: {e}") 

if __name__ == "__main__":
    
    json_file_path = 'failed_uploads/0c246b4e-ec99-4f1c-8ef3-294eeeae244e/user_activities.json'
    post_transid = '0c246b4e-ec99-4f1c-8ef3-294eeeae244e'
    cv_activities = [
    {"USER_PICKUP": "Quest-chips Loaded-Taco"},
    {"USER_PICKUP": "Quest-chips Loaded-Taco"},
    {"USER_PUTBACK": "Quest-chips Loaded-Taco"}
    ]
    logger = logging.getLogger(__name__)
    cv_products = {
    "0": [
        "Quest-chips Chili lime",
        "Quest Chips - Loaded Taco",
        "Legendary Protein Chip - Ranch"
    ],
    "1": [
        "pepsi 500ml",
        "diet pepsi 500ml",
        "mountain dew 500ml"
    ]
}

    sms_alert(logger, json_file_path, cv_activities, post_transid, cv_products)
   