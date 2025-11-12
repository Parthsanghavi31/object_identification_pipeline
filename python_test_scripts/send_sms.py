import requests
from collections import defaultdict, Counter
import re, json

def sms_alert(json_file, cv_activities, post_transid):
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

    line_items = activity['line_items']
    bought_products = [
        clean_name(item["product_name"])
        for item in line_items
        for _ in range(item["quantity"])
    ]

    # Step 3: Compare both
    picked_counter = Counter(picked_products)
    bought_counter = Counter(bought_products)

    print("Picked Products :", picked_counter)
    print("Bought Products :", bought_counter)

    if picked_counter == bought_counter:
        print("Picked products match the bought products.")
    else:
        print("Mismatch found between picked and bought products.")

    duration = activity['duration']
   
    dashboard_url = f'https://dashboard.getvicki.com/reports/undefined/invoice/{post_transid}/activity/{report_id}'
    payload = f'["CreateSMSText", "{"Mismatch found between picked and bought products. Please review it!", (dashboard_url)}"]'

    try:
        response = requests.post(url=vicki_app, data=payload)
        if response.status_code == 200:
            print(response)
            return True
    except Exception as e:
        print(f"Error sending SMS alert: {e}")
    return False

# if __name__ == "__main__":
#     json_file_path = '/home/parth/camera-preview-pipeline/data_for_cv_testing/4e9a520d-9a5a-480d-bb95-b34e1cac65e8/user_activities.json'
#     post_transid = ' 4e9a520d-9a5a-480d-bb95-b34e1cac65e8'
#     cv_activities = [
#     {"USER_PICKUP": "Quest-chips Loaded-Taco"},
#     {"USER_PICKUP": "Quest-chips Loaded-Taco"},
#     {"USER_PUTBACK": "Quest-chips Loaded-Taco"}
# ]
#     sms_alert(json_file_path, cv_activities, post_transid)
   