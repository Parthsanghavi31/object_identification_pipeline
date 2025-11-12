import re
import json
import numpy
import os
import requests
import json
from utils import login
from utils import config

def update_view_activities_dashboard(logger, json_path, cv_activities):

    with open(json_path, 'r') as file:
        user_activity = json.load(file)

    user_instance = user_activity.pop("user_activity_instance")
    user_instance["activities"] = user_instance.pop("user_activities")
    user_activity.update(user_instance)

    user_activity["user_activity_request_type"] = "ORDER_ACTIVITY_REPORT"

    result = {}

    for activity in user_activity["activities"]:
        activity_id = activity["id"]
        activity_type = activity["user_activity_type"]
        product_name = activity.get("product_name")  # will return None if not present

        # only include entries that have a product_name
        if product_name:
            result[activity_id] = {activity_type: product_name}

    def normalize(s):
        return re.sub(r'\W+', '', s).lower()

    normalized_comparisons = [((normalize(k), normalize(v)), i) for i, d in enumerate(cv_activities) for k, v in d.items()]

    used_comparisons = set()
    matching_ids = []

    for _id, activity in result.items():
        for k, v in activity.items():
            norm_key = normalize(k)
            norm_val = normalize(v)
            for (comp_key, comp_val), idx in normalized_comparisons:
                if idx in used_comparisons:
                    continue
                if (norm_key, norm_val) == (comp_key, comp_val):
                    matching_ids.append(_id)
                    used_comparisons.add(idx)
                    break

    logger.info(f"Matching IDs: {matching_ids}" )

    for activity in user_activity["activities"]:
        if activity["id"] in matching_ids:
            activity["post_processing_cv"] = True

    # print(json.dumps(user_activity, indent=2))

    base_url, machine_id, machine_token, machine_api_key = login.get_custom_machine_settings(config.vicki_app, logger)
    access_token = login.get_current_access_token(base_url, machine_id, machine_token, machine_api_key, logger)
    url = "https://viatouchmedia-prod.apigee.net/loyalty/machines/activity"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.put(url, headers=headers, data=json.dumps(user_activity))

    logger.info(f"status Code: {response.status_code}" )
    logger.info(f'response: {response.json()}')

# if __name__ == "__main__":
#     json_path = "/home/parth/camera-preview-pipeline/e9a54ad4-75d2-41e2-a13c-0b5ed6593afb/user_activities.json"
    
#     comparison_list = [
#         # {"USER_PICKUP": "Quest-chips Chili lime"},
#         {"USER_PICKUP": "Quest-chips Loaded-Taco"}
#         # {"USER_PUTBACK": "Quest-chips Loaded-Taco"}
#     ]

#     update_view_activities_dashboard(json_path, comparison_list)

# def send_alert(json_file_path, cv_activities):
    