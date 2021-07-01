import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
from io import StringIO
import os
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import pandas as pd
import os
import datetime
import pytz
import dash_table
from dash.dependencies import Input, Output
import requests as r
import json
import pandas as pd
from time import sleep

###################################################################################
#### geocode: Description: converts adresses into latitude and longitude.      ####
####          The data is formatted as a string in the foramt "{lat}, long"    ####
###################################################################################
def geocode(where, noahsSecretKey='AIzaSyD2DlvTBX6J8cPqauh6bb7UONGvIRIHXRs'):
  url = 'https://maps.googleapis.com/maps/api/geocode/json'
  geocodeP = {'key':noahsSecretKey, 'address':where}
  df = pd.json_normalize(r.get(url, params=geocodeP).json()['results'], max_level=10)
  return f"{df['geometry.location.lat'].loc[0]}, {df['geometry.location.lng'].loc[0]}"


####################################################################################
#### getGooglePlaces: Description: returns results from google Place Search     ####
####                  API.  The data is formatted   into a pandas dataframe.    ####
####                                                                            ####
####################################################################################
def getGooglePlaces(where='Rexburg,ID', business='chiropractor', npt=None, noahsSecretKey='AIzaSyD2DlvTBX6J8cPqauh6bb7UONGvIRIHXRs'):
  url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
  location = geocode(where)
  p = {'key':noahsSecretKey, 'location': location, 'radius':'16000', 'query':business}
  j = r.get(url, params=p).json()
  
  df = pd.json_normalize(j['results'])
  df['photosLength'] = df.photos.apply(lambda x: len(x) if pd.notna(x) else 0)

  return df


####################################################################################
#### getYelpResults: Description: returns results from yelp business search     ####
####                  API.  The data is formatted into a pandas dataframe.      ####
####                                                                            ####
####################################################################################
def getYelpResults(where='Rexburg,ID', business='chiropractor'):
    url = 'https://api.yelp.com/v3/businesses/search'
    apiKey = 'Bearer 04lJwHqIaMxuLZotvTpoCbB7eDoVRpdBOJsasdHviWcE06FJXIsKkhykhUYevieVEqAH_kB438niIgNQumCYUwSoiIbdGH1JpI6J1mAYFvD31i0qaJLKqgr2phOUYHYx'
    header = {'Authorization': apiKey}

    if where is None:
        where='Rexburg, ID'

    if business is None:
        business = 'chiropractors'

    parameters = {'location': where, 'term':business}

    response = r.get(url, params=parameters, headers = header)
    responseDict = json.loads(response.text)

    yelpDf = pd.json_normalize(responseDict['businesses'])
    yelpDf.reset_index(inplace=True)

    return yelpDf


####################################################################################
#### getYelpCategories: Description: take a list of categories and returns      #### 
####                    it as a string of the items seperated by ', '           ####
####                                                                            ####
####################################################################################
def getYelpCategories(catList):
    # catString = ''
    # for cat in catList:
    #     catString += cat['title'] + ', '
    # return catString[:-2]
    return ', '.join(map(str, catList))


####################################################################################
#### getGoogleCategories: Description: take a list of categories and returns    #### 
####                      it as a string of the items seperated by ', '         ####
####                                                                            ####
####################################################################################
def getGoogleCategories(catList):
    # catString = '  '
    # for i in catList:
    #     catString += i + ', '

    # return catString[:-2]    
    return ', '.join(map(str, catList))


####################################################################################
#### rankYelp: Description: this is a function to be used in a df.apply().      #### 
####                        It takes each row and checks certain columns        ####
####                        and gives a score for each column totalled and      ####
####                        saved in a new column called score                  ####
####################################################################################
def rankYelp(row):
    score = 0
    # if row.is_claimed is True:
    #     score += 1 * 5
    # if row.url is not None:
    #     score += 1 
    if len(row.image_url) > 0:
        score += 1 * 5
    score += row.review_count_score
    score += row.categories_score * 1.5
    score += (float(row.rating) / 5) * 4
    if len(row['location.address1']) > 0:
        score += 1 * 4
    if len(row.phone) > 0:
        score += 1 * 4
    score += (1 - row['displayOrder_score']) * 5
    score += row['listingWordCount_score'] * 4

    return score


####################################################################################
#### rankGoogle: Description: this is a function to be used in a df.apply().    #### 
####                        It takes each row and checks certain columns        ####
####                        and gives a score for each column totalled and      ####
####                        saved in a new column called score                  ####
####################################################################################
def rankGoogle(row):
    score = 0
    # if row.is_claimed is True:
    #     score += 5
    # if row.url is not None:
    #     score += 1 
    if len(row['photos']) > 0:
        score += 1
    if len(row['formatted_phone_number']) > 0:
        score += 1
    if len(row['opening_hours.weekday_text']) > 0:
        score += 1
    if len(row['opening_hours.open_now']) > 0:
        score += 1
    return score


# -------------------------- DASH ---------------------------- #
## This is the basic intialization of a dash app.  It uses a specific theme as specified.
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.config.suppress_callback_exceptions = True

## The layout portion is the meat of the Dash app.  This is the part that we display to the users.  It is created using Dash/html notation.  While html.Div
##      was most popular initially with Dash.  Dash now has a container/row/column notation that is remarkable easy to use.
##      Source: https://dash.plotly.com/layout
# Layout
app.layout = html.Div(children=[ 
    dbc.Navbar(
        [
            dbc.Container(
                [
                    html.A(
                        # Use row and col to control vertical alignment of logo / brand
                        dbc.Row(
                            [
                                dbc.Col(
                                    html.Img(
                                        src=app.get_asset_url("sapien.png"),
                                        height="50px",
                                    )
                                ),
                                dbc.Col(dbc.NavbarBrand([html.H5("Sapien Designs SEO", style={'padding': '1rem'})])),
                            ],
                            align="center",
                            no_gutters=True,
                        ),
                        href="#",
                    ),
                    dbc.NavbarToggler(id="navbar-toggler"),
                    dbc.Collapse(id="navbar-collapse", navbar=True),
                ]
            )
        ],
        color="rgba(37, 116, 169, 1)",
        dark=True,
    ),
    dbc.Container(
        [
            # Client Company Name - Today's Date
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Span(
                                ["Business Inquiries Report"],
                                className="h1",
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            html.Span(
                                [
                                    # Mountain Standard Time and Date
                                    pytz.timezone("MST")
                                    .normalize(
                                        pytz.utc.localize(datetime.datetime.utcnow())
                                    )
                                    .strftime("%a, %d-%b-%Y")
                                ],
                                className="h3",
                            )
                        ]
                    ),
                ],
                className="align-items-end mt-3",
            ),
            # [Horizontal Line]
            html.Hr(),
        ]
    ),
    dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col([
                            # Date filter
                            html.H6('Location'),
                            
                            dcc.Input(
                                id="locationInput",
                                placeholder="Input a location",
                                debounce=True,
                            ),
                        ],
                        style = {'padding': '1rem'},
                    ),
                    dbc.Col([
                            # Date filter
                            html.H6('Business Type'),
                            
                            dcc.Input(
                                id="businessInput",
                                placeholder="Input a business type",
                                debounce=True,
                            ),
                        ],
                        style = {'padding': '1rem'},
                    ),
                    dbc.Col([
                            # Date filter
                            html.H6('Data Source'),
                            
                            dcc.Dropdown(
                                id="dataSourceSelect",
                                options=[
                                    {'label': 'Google', 'value': 'google'},
                                    {'label': 'Yelp', 'value': 'yelp'},
                                ],
                                value='yelp',
                                placeholder='Select Source...'
                            ),
                        ],
                        style = {'padding': '1rem'},
                    ),
                    html.Div([
                            html.H6('Download as CSV'),
                            
                            html.Button("Download", id="btn_csv", style={'background-color': 'rgba(37, 116, 169, 1)', 'border': 'none',
                                                                         'color': 'white', 'text-align': 'center', 
                                                                         'display': 'inline-block', 'font-size': '24px'}), 
                            dcc.Download(id="download-csv")
                        ],
                        style={'width': '25%', 'padding':'1rem'},
                    ),
                ],
            )
        ]
    ),
    dbc.Container(
        fluid=True,
        children=
            [
                dash_table.DataTable(
                    id='businessTable',
                    columns=[
                        {"name": ['Name'], "id":'name'},
                        {"name": ['Review Count'], "id":'review_count'},
                        {"name": ['Rating'], "id":'rating'},
                        {"name": ['Categories'], "id":'categories'},
                        {"name": ['Phone'], "id":'display_phone'},
                        {"name": ['Address'], "id": 'location.display_address'},
                        {"name": ['Predicted Match'], "id": 'score'}
                        ],
                    merge_duplicate_headers=True,
                )
            ]
    ),
])


## This is a dataframe that is meant to store the data so that it can be saved to a csv
globalDf = pd.DataFrame({'Empty':[]})


# ------------------- CALLBACK FUNCTIONS --------------------- #
## These are where the callback functions are stored.  Callback functions are functions that run when a given input is modified.


####################################################################################
#### getResultsTable:  Description: This function checks whether the yelp or    ####
####                   google option is selected, aggregates the data from      ####
####                   the api related to the source, cleans the data, and      ####
####                   then returns the data back to the dashTable.             ####
####################################################################################
@app.callback(
    Output("businessTable", "data"),
    Input("locationInput", "value"),
    Input("businessInput", "value"),
    Input('dataSourceSelect', 'value'))
def getResultsTable(location, business, source):
    # check if yelp is selected
    if source == 'yelp':
        yelpDf = getYelpResults(location, business)
        # applies the getYelpCategories to the categories column and saves it to the same column
        yelpDf['categories'] = yelpDf['categories'].apply(getYelpCategories)
        # calculates the score to be given for review counts.  It uses min-max scaling.
        yelpDf['reviewCount_score'] = (yelpDf['review_count']  - yelpDf['review_count'].min()) / (yelpDf['review_count'].max() - yelpDf['review_count'].min())
        # calculates the length of the list in the categories column.
        yelpDf['categories_len'] = yelpDf['categories'].str.split(',').apply(lambda x: len(x))
        # calculates the score to be given for categories length.  It uses min-max scaling.
        yelpDf['categories_score'] = (yelpDf['categories_len'] - 1) / (yelpDf['categories_len'].max() - 1)
        # calculates the score to be given for display order (The order it would appear when searched).  It uses min-max scaling.
        yelpDf['displayOrder_score'] = ((yelpDf['displayOrder']) / yelpDf['displayOrder'].max())
        # calculates the length of the words in companies name.  This is to get some idea of a descriptive title.
        yelpDf['listingWordCount'] = yelpDf['name'].apply(lambda x: len(x.split()))
        # calculates the score to be given for businesses name.  It uses min-max scaling.
        yelpDf['listingWord_score'] = (yelpDf['listingWordCount'] - yelpDf['listingWordCount'].min()) / (yelpDf['listingWordCount'].max() -  yelpDf['listingWordCount'].min())
        # replaces missing values with zeroes.
        yelpDf['photos'].fillna([], inplace=True)
        # calculates the length of the list in the photos column
        yelpDf['photosLength'] = yelpDf['photos'].apply(lambda x: len(x))

        # uses the rankYelp() function from above to perform a row wise calculation
        yelpDf['score'] = yelpDf.apply(lambda x: rankYelp(x), axis=1)
        # performs min-max scaling and then multiplies it by 100 to turn it into a percentage.  
        # This percentage is a percentage of the things they are doing wrong compared to their competitors.
        # The best possible for a business to have is 0% and the worst possible would be 100%.
        # Mike would want to talk to those closer to 100%.
        yelpDf['score'] = 100- (yelpDf['score'] / yelpDf['score'].max()) * 100

        # sorts the rows by the score so those with the worst score are on top.
        yelpDf.sort_values(['score'], ascending=False, inplace=True)

        # converts the score column from a float into a string of the format "{score}%"
        yelpDf['score'] = yelpDf['score'].apply(lambda x: f'{x:.2f}%')

        # gets the globalDf and copies the data to it so that it can be downloaded if desired
        global globalDf
        globalDf = yelpDf.copy()

        # dash tables want to format to be in a dict so the ".to_dict('records')" converts it from a pandas dataframe into the right format
        return yelpDf.to_dict('records')
    # if it wasnt yelp then it must be google
    # note: most of the renaming is just to match the name of the columns from the yelp api
    else:
        # get the google data
        googleDf = getGooglePlaces(location, business)
        # try to create a copy of the column 'formatted_address' if it isnt there print 'except' to the console.
        try: googleDf['location.display_address'] = googleDf['formatted_address']
        except: print('except')
        # create a copy of the 'user_ratings_total' column and call it 'review_count'
        googleDf['review_count'] = googleDf['user_ratings_total']
        # change below to be googleDf
        # yelpDf['reviewCount_score'] = (yelpDf['review_count']  - yelpDf['review_count'].min()) / (yelpDf['review_count'].max() - yelpDf['review_count'].min())
        # applies the getGoogleCategories function to the 'types' column and saves it as a new column called categories.
        googleDf['categories'] = googleDf['types'].apply(getGoogleCategories)
        # gets the length of the list in the types column
        googleDf['categories_len'] = googleDf['types'].apply(lambda x: len(x))
        # gets the score of the categories column. It uses min-max scaling
        googleDf['categories_score'] = (googleDf['categories_len'] - 1) / (googleDf['categories_len'].max() - 1)
        # currently the api does not return 
        googleDf['display_phone'] = None

        return googleDf.to_dict('records')


####################################################################################
#### func:  Description: downloads the data in globalDf as a .csv file          ####
####################################################################################
@app.callback(
    Output("download-csv", "data"),
    Input("btn_csv", "n_clicks"),
    prevent_initial_call=True)
def func(n_clicks):
    return dcc.send_data_frame(pd.DataFrame(globalDf).to_csv, "rankingsResults.csv")


# -------------------------- MAIN ---------------------------- #

# standard code to start the app. port 8080 is what google cloud uses
if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8080, debug=True, use_reloader=False)