import os
import json
import numpy as np
import logging
from collections import defaultdict
import re
from utils import config

def clean_name(name):
        return ''.join(re.findall(r'[a-zA-Z]+', name)).lower()

def check_pairs(cv_activities):
    product_counts =  defaultdict(lambda: {'USER_PICKUP':0, 'USER_PUTBACK':0})
    
    for activity in cv_activities:
        for action, product in activity.items():
            product_counts[product][action]+=1
    
    final_pickup = []
    for product_name, product_actions in product_counts.items():
        net = product_actions['USER_PICKUP'] - product_actions['USER_PUTBACK']
        if net>0:
            final_pickup.extend([product_name]*net)
    return final_pickup
   
def cv_product_present(json_file, cv_activities, stream):

    config_products = config.cv_products[str(stream)]
    with open(json_file, 'r') as file:
        raw_json = json.load(file)  
    useract = raw_json["user_activity_instance"]["user_activities"]
    # print(useract)
    ls_activities = []
    
    for activity in useract:
        
        user_action = activity.get('user_activity_type')
        product_name = activity.get('product_name')
        
        if product_name:
            ls_activities.append({user_action: product_name})
        
    ls_checkout = check_pairs(ls_activities)
    cv_checkout = check_pairs(cv_activities)
    
    combined_list = [clean_name(name) for name in ls_checkout] +  [clean_name(name) for name in cv_checkout] 
        
    # print(combined_list)
    cv_product_set = set([clean_name(name) for name in config_products])
    detected_products_set = set(combined_list)

    intersection_set = cv_product_set & detected_products_set
    # print(intersection_set)
    return intersection_set

# if __name__ == "__main__":
#     json_file_path = "/home/parth/camera-preview-pipeline/data_for_cv_testing/office_transaction_1/user_activities.json"
#     cv_activities = [
#         {"USER_PICKUP": "Quest-chips Chili lime"},
#         {"USER_PICKUP": "Quest-chips Loaded-Taco"},
#         {"USER_PUTBACK": "Quest-chips Loaded-Taco"}
#     ]
#     products = cv_product_present(json_file_path, cv_activities, config_products)