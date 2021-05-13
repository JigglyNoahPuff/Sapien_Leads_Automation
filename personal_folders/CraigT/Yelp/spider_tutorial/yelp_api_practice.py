import requests
import json

# our api key
YELP_KEY = "nWG-5cGFojivklrg_K31zuWWUv3jn5-ByjrGKacyFnVQ-gWHuBIWpYSEAvRiBT2KlKaIgqu_tRmhP5TZjrNahTAx_xRSPOrdV-Ko5SdayZbJTFVm3Srj5pUXxgmUYHYx"
# header for the api key
headers = {"Authorization": f"Bearer {YELP_KEY}"}
# search terms
params = {'term': 'chiropractor', 'location': 'Salt Lake City', 'radius': '4000'}
# request
request = requests.get("https://api.yelp.com/v3/businesses/search", params=params, headers=headers)
# convert to dictionary
business_dict = json.loads(request.text)

print(business_dict)

for i in business_dict['businesses']:
    print(i)
    

