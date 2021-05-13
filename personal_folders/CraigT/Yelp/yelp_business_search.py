import requests
import json


API_KEY = "nWG-5cGFojivklrg_K31zuWWUv3jn5-ByjrGKacyFnVQ-gWHuBIWpYSEAvRiBT2KlKaIgqu_tRmhP5TZjrNahTAx_xRSPOrdV-Ko5SdayZbJTFVm3Srj5pUXxgmUYHYx"
HEADERS = {f'Authorization': f'Bearer {API_KEY}'}
URL = 'https://api.yelp.com/v3/businesses/search'


if __name__ == '__main__':
    headers = HEADERS
    url = URL
    business_type = input("What kind of business are you looking for: ")
    business_location = input("Where do you want to look: ")

    params = {'term': f'{business_type}', 'location': f'{business_location}'}
    req = requests.get(url, params=params, headers=headers)
    raw_data_dict = json.loads(req.text)

    business_info_list = []

#single threaded

    for business in raw_data_dict["businesses"]:
        business_url = f"https://api.yelp.com/v3/businesses/{business['id']}"
        req = requests.get(business_url, headers=headers)
        business_info_list.append(req.text)

    



