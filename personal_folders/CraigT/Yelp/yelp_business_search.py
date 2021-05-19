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

print(business_info_list)
#%%
# put all our data into a pandas dataframe and export as a csv
business_df = pd.DataFrame(business_info_list)
business_df.to_csv("business_details.csv")

print(business_df.head(5))

# %%
