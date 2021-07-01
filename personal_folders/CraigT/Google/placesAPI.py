import requests
import pandas as pd



place_api_key = 'AIzaSyA6au7_HvaVdwGpyrRdgsKTgCcug8UIckM'

where = input('where do you want to look: ')
business_type = input('what kind of business are you looking for: ')

# get the latitude and longitude for the place we are looking for
def geocode(where, place_api_key=place_api_key):
  url = 'https://maps.googleapis.com/maps/api/geocode/json'
  geocodeP = {'key':place_api_key, 'address':where}
  df = pd.json_normalize(requests.get(url, params=geocodeP).json()['results'])
  return f"{df['geometry.location.lat'].loc[0]}, {df['geometry.location.lng'].loc[0]}"

# get the places_df according to the place and business type we are looking for
def get_place_df(where, business_type, place_api_key=place_api_key):
  url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
  location = geocode(where)
  params = {'key':place_api_key, 'location':location, 'radius':'16000', 'query':business_type}
  req = requests.get(url, params=params).json()
  df = pd.json_normalize(req['results'])
  return df

# get a list of the place ids from the place df
def get_place_ids(place_df):
    place_ids = list(place_df.place_id.values)
    return place_ids

# get the full place details df
def get_place_details(place_ids, place_api_key):
    temp_dfs = []
    url = 'https://maps.googleapis.com/maps/api/place/details/json'
    for id in place_ids:
        params = {'key': place_api_key, 'place_id': id}
        response = requests.get(url, params=params).json()
        temp_df = pd.json_normalize(response['result'])
        temp_dfs.append(temp_df)
    df = pd.concat(temp_dfs, sort=False)
    return df


places_df = get_place_df(where=where, business_type=business_type)
place_ids = get_place_ids(places_df)
place_details_df = get_place_details(place_ids, place_api_key)
print(place_details_df.head())
google_csv_name = input('name the csv: ')

place_details_df.to_csv(f'./data/raw/google/{google_csv_name}', index=False)

