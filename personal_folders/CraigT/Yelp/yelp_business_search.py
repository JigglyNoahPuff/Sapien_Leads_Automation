#%%
import requests
import json
import pandas as pd

API_KEY = "nWG-5cGFojivklrg_K31zuWWUv3jn5-ByjrGKacyFnVQ-gWHuBIWpYSEAvRiBT2KlKaIgqu_tRmhP5TZjrNahTAx_xRSPOrdV-Ko5SdayZbJTFVm3Srj5pUXxgmUYHYx"
HEADERS = {f'Authorization': f'Bearer {API_KEY}'}
URL = 'https://api.yelp.com/v3/businesses/search'

#%%

headers = HEADERS
url = URL
business_type = input("What kind of business are you looking for: ")
business_location = input("Where do you want to look: ")

params = {'term': f'{business_type}', 'location': f'{business_location}'}
req = requests.get(url, params=params, headers=headers)
raw_data_dict = json.loads(req.text)
business_info_list = []

# single threaded put all the business info dictionaries into a list
for business in raw_data_dict["businesses"]:
    business_url = f"https://api.yelp.com/v3/businesses/{business['id']}"
    req = requests.get(business_url, headers=headers)
    dic = json.loads(req.text)

    business_info_list.append(dic)

# save the individual json file so its easier to look at
#with open('fist_business.json', 'w') as f:
    #json.dump(business_info_list[0],fp=f, indent=4)

#print(business_info_list[0])

#%%
# put all our data into a pandas dataframe and export as a csv
meta3 = ['id','alias','name','image_url','is_claimed','is_closed','url','phone','display_phone','review_count','rating','location','coordinates','photos','hours']
business_df = pd.json_normalize(business_info_list, record_path=['categories'], meta=meta3, errors='ignore', record_prefix='categories_')

csv_name = input("What do you want to name your file: ")
business_df.to_csv(f"./data/raw/{csv_name}.csv", index=False)

# %%


