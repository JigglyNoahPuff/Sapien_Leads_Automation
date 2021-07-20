import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import datetime
import pytz
import dash_table
from dash.dependencies import Input, Output, State
from time import sleep

import pandas as pd
import requests as r
import json
import re

from bs4 import BeautifulSoup as bs


###################################################################################
#### geocode: Description: converts adresses into latitude and longitude.      ####
####          The data is formatted as a string in the foramt "{lat}, long"    ####
###################################################################################
def geocode(where='Rexburg,ID', noahsSecretKey='AIzaSyAFwMkv-fhkD6r8uzDMUt0qrmuaoCCAkfY'):
  url = 'https://maps.googleapis.com/maps/api/geocode/json'
  geocodeP = {'key':noahsSecretKey, 'address':where}
  df = pd.json_normalize(r.get(url, params=geocodeP).json()['results'], max_level=10)
  return f"{df['geometry.location.lat'].loc[0]}, {df['geometry.location.lng'].loc[0]}"


####################################################################################
#### getGooglePlaces: Description: returns results from google Place Search     ####
####                  API.  The data is formatted   into a pandas dataframe.    ####
####                                                                            ####
####################################################################################
def getGooglePlaces(where='Rexburg,ID', business='chiropractor', npt=True, noahsSecretKey='AIzaSyAFwMkv-fhkD6r8uzDMUt0qrmuaoCCAkfY', radius=16):
    url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
    location = geocode(where)
    p = {'key':noahsSecretKey, 'location': location, 'radius':radius, 'query':business}
    j = r.get(url, params=p).json()
    
    df = pd.json_normalize(j['results'])

    while npt:
        try:
            npt = j['next_page_token']
            sleep(5)
        except:
            break
        try:
            p = {'key':noahsSecretKey, 'pagetoken': npt}
            j = r.get(url, params=p).json()

            tempDf = pd.json_normalize(j['results'])
            df = pd.concat([df, tempDf], ignore_index=True)
        except:
            print('It done did not work Captain Sassypants!')

    return df

####################################################################################
#### getGooglePlaceDetails: Description: returns results from google Place      ####
####                        Details API.  The data is formatted into a pandas   ####
####                        dataframe.                                          ####
####################################################################################
def getGooglePlaceDetails(where='Rexburg,ID', business='chiropractor', noahsSecretKey='AIzaSyAFwMkv-fhkD6r8uzDMUt0qrmuaoCCAkfY', radius=16):
    df = getGooglePlaces(where, business, radius=radius)
    url = 'https://maps.googleapis.com/maps/api/place/details/json'
    place_ids = list(df.place_id.values)
    temp_dfs = list()

    for id in place_ids:
        sleep(1)
        try:
            p = {'key':noahsSecretKey, 'place_id':id}
            response = r.get(url, params=p).json()
            temp_df = pd.json_normalize(response['result'])
            temp_dfs.append(temp_df)
        except:
            sleep(5)
            pass
    place_details_df = pd.concat(temp_dfs, sort = False)
    place_details_df.reset_index(inplace=True, drop=True)
    place_details_df.reset_index(inplace=True)
    place_details_df.rename({'index': 'displayOrder'}, inplace=True, axis=1)

    if temp_dfs:
        print('Branch 1!')
        return place_details_df
    else:
        print('Branch 2!')
        return df

####################################################################################
#### getYelpResults: Description: returns results from yelp business search     ####
####                  API.  The data is formatted into a pandas dataframe.      ####
####                                                                            ####
####################################################################################
def getYelpResults(where='Rexburg,ID', business='chiropractor'):
    url = 'https://api.yelp.com/v3/businesses/search'
    apiKey = 'Bearer XxySt6ePK76WoVD-5OPIOgtTVwve6y01ithytLphNCnYtIJfRmq-OUx_tJymCq7u4J183c4efyRSD0EQeIYyC3Fp3EMjjgQE-oH-j3PVKqEFjMCiFNcQb7Wl4C_nYHYx'
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
    newColumns = list(yelpDf.columns)
    newColumns[0] = 'displayOrder'
    yelpDf.columns = newColumns

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
    if row['is_claimed']:
        score += 5
    if row['image_url']:
        score += 1 * 5
    score += row.review_count_score
    score += row.categories_score * 1.5
    score += (float(row.rating) / 5) * 4
    if row['location.address1']:
        score += 1 * 4
    if row['phone']:
        score += 1 * 4
    score += (1 - row['displayOrder_score']) * 5
    score += row['listingWordCount_score'] * 4
    if row['display_phone']:
        score += 1 * 4

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
    score += (1 - row['displayOrder_score']) * 5
    if row['photosLength'] > 0:
        score += 1 * 5
    score += row.review_count_score
    score += row.categories_score * 1.5
    if len(str(row['formatted_phone_number'])) > 0:
        score += 1 * 4
    if len(str(row['opening_hours.weekday_text'])) > 0:
        score += 1 * 4
    return score


# add email to place details
def get_email(row):
    try:
        website = row['website']
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'}
        response = r.get(str(website), headers=headers, timeout=2, allow_redirects=False)
        html_doc = response.content
        soup = bs(html_doc, 'html.parser')
        pageContent = soup.prettify() 
        eList = re.findall('[\w\-\+\~]+@[\w\-\+\~]+\.[\w\-\+\~]+\.*[a-z]*', pageContent)
        newList = []
        for e in eList:
            if e.find('facebook') == -1 and e.find('yelp') == -1 and e.find('google') == -1 and e.find('yellow') == -1 and e.find('linkedin') == -1  and e.find('hdscores') == -1 and e not in newList:
                newList.append(e)
        return newList
    except:
        return ['No Emails Found']



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
    dbc.Container([
            dbc.Row([
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
                        id="locationInputCol",
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
                        id="businessInputCol",
                    ),
                    dbc.Col([
                            # Date filter
                            html.H6('Radius Size in Kilometers'),
                            
                            dcc.Input(
                                id="radiusInput",
                                placeholder="Input radius size",
                                value=16,
                                debounce=True,
                            ),
                        ],
                        style = {'padding': '1rem'},
                        id="radiusInputCol",
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
                                value='google',
                                placeholder='Select Source...'
                            ),
                        ],
                        style = {'padding': '1rem'},
                        id="dataSourceSelectCol",
                    ),
            ], id='inputRow'),
                dcc.Tabs(id='tabs-parent', value='bTable', children=[
                    dcc.Tab(label='Table', value='bTable', id='bTableTab', children=[
                        dbc.Container(
                            children=[
                                    dbc.Row([
                                        dbc.Col([], id='tableSourceHeader'),
                                        dbc.Col([
                                                html.Button("Download Subset", id="btn_subset_csv", style={'background-color': 'rgba(37, 116, 169, 1)', 'border': 'none',
                                                                                            'color': 'white', 'text-align': 'center', 
                                                                                            'display': 'inline-block', 'font-size': '24px'}), 
                                                dcc.Download(id="download_subset_csv")
                                            ],
                                            style={'width': '25%', 'padding':'1rem', 'justify-content':'center', 'display':'flex'},
                                        ),
                                        dbc.Col([
                                                html.Button("Download Full", id="btn_full_csv", style={'background-color': 'rgba(37, 116, 169, 1)', 'border': 'none',
                                                                                            'color': 'white', 'text-align': 'center', 
                                                                                            'display': 'inline-block', 'font-size': '24px'}), 
                                                dcc.Download(id="download_full_csv")
                                            ],
                                            style={'width': '25%', 'padding':'1rem', 'justify-content':'center', 'display':'flex'},
                                        ),
                                    ]),
                                    dbc.Row([
                                        dbc.Col([
                                            dash_table.DataTable(
                                                id='businessTable',
                                                style_cell={
                                                    'whiteSpace': 'normal',
                                                    'height': 'auto',
                                                },
                                                columns=[
                                                    {"name": ['Name'], "id":'name'},
                                                    {"name": ['Review Count'], "id":'review_count'},
                                                    {"name": ['Rating'], "id":'rating'},
                                                    {"name": ['Phone'], "id":'display_phone'},
                                                    {"name": ['Address'], "id": 'location.display_address'},
                                                    {"name": ['Predicted Match'], "id": 'score'}
                                                    ],
                                                merge_duplicate_headers=True,
                                            )
                                            ], style={'width':'100%', 'padding':'0rem', 'padding-top':'1rem', 'margin':'0rem'})
                                    ])
                            ], id='btContainer', style={'width':'100%', 'padding':'0rem', 'padding-top':'1rem', 'margin':'0rem'}
                        ),
                    ]),
                    dcc.Tab(label='Joint Tables', value='bTables', id='bTablesTab', children=[
                        dbc.Container(
                            children=[
                                    dbc.Row([
                                        dbc.Col([
                                                html.Button("Commence Search", id="btn_tables_search", style={'background-color': 'rgba(37, 116, 169, 1)', 'border': 'none',
                                                                                            'color': 'white', 'text-align': 'center', 
                                                                                            'display': 'inline-block', 'font-size': '24px'}), 
                                            ],
                                            style={'width': '25%', 'padding':'1rem', 'justify-content':'center', 'display':'flex'},
                                        ),
                                        dbc.Col([
                                                html.Button("Download Subsets", id="btn_subsets_csv", style={'background-color': 'rgba(37, 116, 169, 1)', 'border': 'none',
                                                                                            'color': 'white', 'text-align': 'center', 
                                                                                            'display': 'inline-block', 'font-size': '24px'}), 
                                                dcc.Download(id="download_subsets_csv")
                                            ],
                                            style={'width': '25%', 'padding':'1rem', 'justify-content':'center', 'display':'flex'},
                                        ),
                                        dbc.Col([
                                                html.Button("Download Fulls", id="btn_fulls_csv", style={'background-color': 'rgba(37, 116, 169, 1)', 'border': 'none',
                                                                                            'color': 'white', 'text-align': 'center', 
                                                                                            'display': 'inline-block', 'font-size': '24px'}), 
                                                dcc.Download(id="download_fulls_csv")
                                            ],
                                            style={'width': '25%', 'padding':'1rem', 'justify-content':'center', 'display':'flex'},
                                        ),
                                    ]),
                                    dbc.Row([
                                        dbc.Col([
                                            dash_table.DataTable(
                                                id='googTable',
                                                style_cell={
                                                    'whiteSpace': 'normal',
                                                    'height': 'auto',
                                                },
                                                columns=[
                                                    {"name": ['Google', 'Name'], "id":'name'},
                                                    {"name": ['Google', 'Phone'], "id":'display_phone'},
                                                    {"name": ['Google', 'Address'], "id": 'location.display_address'},
                                                    {"name": ['Google', 'Score'], "id": 'score'}
                                                    ],
                                                merge_duplicate_headers=True,
                                            )
                                            ], style={'width':'100%', 'padding':'0rem', 'padding-top':'1rem', 'margin':'0rem'}),
                                        dbc.Col([
                                            dash_table.DataTable(
                                                id='yelpTable',
                                                style_cell={
                                                    'whiteSpace': 'normal',
                                                    'height': 'auto',
                                                },
                                                columns=[
                                                    {"name": ['Yelp', 'Name'], "id":'name'},
                                                    {"name": ['Yelp', 'Phone'], "id":'display_phone'},
                                                    {"name": ['Yelp', 'Address'], "id": 'location.display_address'},
                                                    {"name": ['Yelp', 'Score'], "id": 'score'}
                                                    ],
                                                merge_duplicate_headers=True,
                                            )
                                            ], style={'width':'100%', 'padding':'0rem', 'padding-top':'1rem', 'margin':'0rem'})
                                    ])
                            ], id='btsContainer', style={'width':'100%', 'padding':'0rem', 'padding-top':'1rem', 'margin':'0rem'}
                        ),
                    ]),
                    dcc.Tab(label='Report', value='bReport', children=[
                        dbc.Container(children=[
                                dbc.Container(
                                fluid=True, 
                                children=[
                                        dbc.Row([
                                            dbc.Col([
                                                    html.H6('Select a company:'),
                                                    dcc.Dropdown(
                                                                id="companies-dropdown",
                                                                options=[],
                                                                ),
                                                ], width=9, style={'padding':'1rem'}, id="companies-dropdown-col"),
                                            dbc.Col(dbc.Button('Toggle Print View', id='printButton', style={'width':'100%'}), style={'padding':'1rem'}, width=3)
                                        ], style={'padding':'1rem'}),
                                ], style={'margin':'1rem'}),
                                dbc.Container(
                                    fluid=True, 
                                    children=[
                                            dbc.Row(html.H2('Choose a value.', id='company-header', style={'color':'rgba(31, 58, 147, 1)'})),
                                            html.Hr(),
                                            dbc.Row([
                                                dbc.Col([
                                                    html.H4('Website', style={'color':'rgba(31, 58, 147, 1)'}), 
                                                    html.P('', id='ktfiga-website')
                                                ]),
                                                dbc.Col([
                                                    html.H4('Phone', style={'color':'rgba(31, 58, 147, 1)'}), 
                                                    html.P('', id='ktfiga-phone')
                                                ]),
                                                dbc.Col([
                                                    html.H4('Hours of Operation', style={'color':'rgba(31, 58, 147, 1)'}), 
                                                    html.P('', id='ktfiga-hoo')
                                                ], width=5),
                                            ], style={'padding':'1rem'}),
                                            dbc.Row([
                                                dbc.Col([
                                                    html.H4('Address', style={'color':'rgba(31, 58, 147, 1)'}), 
                                                    html.P('', id='ktfiga-add')
                                                ]),
                                                dbc.Col([
                                                    html.H4('Categories', style={'color':'rgba(31, 58, 147, 1)'}), 
                                                    html.P('', id='ktfiga-cat')
                                                ]),
                                                dbc.Col([
                                                    html.H4('Emails', style={'color':'rgba(31, 58, 147, 1)'}), 
                                                    html.P('', id='ktfiga-emails')
                                                ], width=5)
                                            ], style={'padding':'1rem'}),
                                            dbc.Row([
                                                dbc.Col([
                                                    html.H4('Rating', style={'color':'rgba(31, 58, 147, 1)'}), 
                                                    html.P('', id='ktfiga-rat')
                                                ]),
                                                dbc.Col([
                                                    html.H4('Review Count', style={'color':'rgba(31, 58, 147, 1)'}), 
                                                    html.P('', id='ktfiga-rc')
                                                ]),
                                                dbc.Col([
                                                    html.H4('Search Display Order', style={'color':'rgba(31, 58, 147, 1)'}), 
                                                    html.P('', id='ktfiga-sdo')
                                                ], width=5),
                                            ], style={'padding':'1rem'}),
                                            dbc.Row([
                                                dbc.Col([
                                                    html.H4('Photos Amount', style={'color':'rgba(31, 58, 147, 1)'}), 
                                                    html.P('', id='ktfiga-pa')
                                                ], width=7),
                                                dbc.Col([
                                                    html.H4('Percentage Match', style={'color':'rgba(31, 58, 147, 1)'}), 
                                                    html.P('', id='ktfiga-pm')
                                                ], width=5)
                                            ], style={'padding':'1rem'}),
                                        ], style={'padding':'3rem', 'padding-top':'1rem', 'margin':'3rem', 'margin-top':'1rem'}),
                            ], style={'padding':'2rem', 'padding-top':'1rem', 'margin':'2rem', 'margin-top':'1rem'}, id='hiddenContainer')
                    ]),
                    dcc.Tab(label='License', value='license', id='license', children=[
                        dbc.Container(
                            children=[
                                    dbc.Row([
                                        dbc.Col([html.H1('MIT License')], id='licenseHeader'),
                                    ]),
                                    dbc.Row(
                                        html.P('Permission is hereby granted, free of charge, to any person obtaining a copy \
                                                of this software and associated documentation files (the "Software"), to deal in \
                                                the Software without restriction, including without limitation the rights to use,\
                                                copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the \
                                                Software, and to permit persons to whom the Software is furnished to do so, \
                                                subject to the following conditions:')
                                    ),
                                    dbc.Row(
                                        html.P('The above copyright notice and this permission notice shall be included in all copies \
                                                or substantial portions of the Software.')
                                    ),
                                    dbc.Row(
                                        html.P('THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, \
                                                INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A \
                                                PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT \
                                                HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION \
                                                OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE \
                                                SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.')
                                    )
                            ], id='licenseContainer', style={'width':'100%', 'padding':'0rem', 'padding-top':'1rem', 'margin':'0rem'}
                        ),
                    ]),
                ], style={'width':'100%', 'padding':'0rem', 'padding-top':'1rem', 'margin':'0rem'}),
    ]),
    dcc.Store(id='globalDf'),
    dcc.Store(id='yelpGlobalDf'),
    dcc.Store(id='googDf'),
])


## This is a dataframe that is meant to store the data so that it can be saved to a csv
# globalDf = pd.DataFrame({'Empty':[]})
# yelpGlobalDf = pd.DataFrame({'Empty':[]})
# googDf = pd.DataFrame({'Empty':[]})


# ------------------- CALLBACK FUNCTIONS --------------------- #
## These are where the callback functions are stored.  Callback functions are functions that run when a given input is modified.


####################################################################################
#### getResultsTable:  Description: This function checks whether the yelp or    ####
####                   google option is selected, aggregates the data from      ####
####                   the api related to the source, cleans the data, and      ####
####                   then returns the data back to the dashTable  w.             ####
####################################################################################
@app.callback(
    [Output("businessTable", "data"),
    Output('companies-dropdown', 'options'),
    Output('tableSourceHeader', 'children'),
    Output('globalDf', 'data')],
    Input("locationInput", "value"),
    Input("businessInput", "value"),
    Input('dataSourceSelect', 'value'),
    Input('radiusInput', 'value'))
def getResultsTable(location, business, source, radius):
    # check if yelp is selected
    if location is None or business is None or radius is None or location == '' or business == '' or radius == '':
        raise PreventUpdate 
    if source == 'yelp':
        yelpDf = getYelpResults(location, business)
        # applies the getYelpCategories to the categories column and saves it to the same column
        yelpDf['categories'] = yelpDf['categories'].apply(getYelpCategories)
        # calculates the score to be given for review counts.  It uses min-max scaling.
        yelpDf['review_count_score'] = (yelpDf['review_count']  - yelpDf['review_count'].min()) / (yelpDf['review_count'].max() - yelpDf['review_count'].min())
        # calculates the length of the list in the categories column.
        yelpDf['categories_len'] = yelpDf['categories'].str.split(',').apply(lambda x: len(x))
        # calculates the score to be given for categories length.  It uses min-max scaling.
        yelpDf['categories_score'] = (yelpDf['categories_len'] - 1) / (yelpDf['categories_len'].max() - 1)
        # calculates the score to be given for display order (The order it would appear when searched).  It uses min-max scaling.
        yelpDf['displayOrder_score'] = ((yelpDf['displayOrder']) / yelpDf['displayOrder'].max())
        # calculates the length of the words in companies name.  This is to get some idea of a descriptive title.
        yelpDf['listingWordCount'] = yelpDf['name'].apply(lambda x: len(x.split()))
        # calculates the score to be given for businesses name.  It uses min-max scaling.
        yelpDf['listingWordCount_score'] = (yelpDf['listingWordCount'] - yelpDf['listingWordCount'].min()) / (yelpDf['listingWordCount'].max() -  yelpDf['listingWordCount'].min())
        # pull the address out of its list
        yelpDf['location.display_address'] = yelpDf['location.display_address'].apply(lambda x: x[0] if x is not None and len(x) == 1 else x[0] + ' ' + x[1] if x is not None and len(x) == 2 else x[0] + ' ' + x[1] + ' ' + x[2] if x is not None and len(x) == 3 else '')

        try:
            # # calculates the length of the list in the photos column
            yelpDf['photosLength'] = yelpDf['photos'].apply(lambda x: len(x) if x is not None and type(x) is list else 0)
        except: 
            # yelpDf['photos'] = 0
            yelpDf['photosLength'] = 0

        # yelpDf['photosLength'] = yelpDf['photos'].apply(lambda x: len(x) if x is not None and x != '' else 0)

        # uses the rankYelp() function from above to perform a row wise calculation
        yelpDf['score'] = yelpDf.apply(lambda x: rankYelp(x), axis=1)
        # performs min-max scaling and then multiplies it by 100 to turn it into a percentage.  
        # This percentage is a percentage of the things they are doing wrong compared to their competitors.
        # The best possible for a business to have is 0% and the worst possible would be 100%.
        # Mike would want to talk to those closer to 100%.
        yelpDf['score'] = 100 - (yelpDf['score'] / yelpDf['score'].max()) * 100
        # sorts the rows by the score so those with the worst score are on top.
        yelpDf.sort_values(['score'], ascending=False, inplace=True)
        # converts the score column from a float into a string of the format "{score}%"
        yelpDf['score'] = yelpDf['score'].apply(lambda x: f'{x:.2f}%')
        # set website series to a default value
        yelpDf['website'] = "Website Info Unavailable"
        # set hours series to a default value
        yelpDf['opening_hours.weekday_text'] = "Hours Info Unavailable"
        # set emails series to a default value
        yelpDf['emails'] = "Emails Info Unavailable"
        yelpDf['last_name'] = 'unknown'
        yelpDf['location_search'] = location
        yelpDf['business_search'] = business
        yelpDf['source_search'] = source

        options = [{'label':company, 'value':company} for company in yelpDf.name.values]

        # dash tables want to format to be in a dict so the ".to_dict('records')" converts it from a pandas dataframe into the right format
        return yelpDf.to_dict('records'), options, html.H2('Yelp'), yelpDf.to_dict('records')

    # if it wasnt yelp then it must be google
    # note: most of the renaming is just to match the name of the columns from the yelp api
    else:
        # get the google data
        googleDf = getGooglePlaceDetails(location, business, radius=radius)
        try:
            googleDf['photosLength'] = googleDf['photos'].apply(lambda x: len(x) if x is not None and type(x) is list else 0)
        except:
            googleDf['photosLength'] = 0
        # fill nans in the dataframe
        googleDf.fillna(0, inplace=True)

        # create a copy of the 'user_ratings_total' column and call it 'review_count'
        googleDf['review_count'] = googleDf['user_ratings_total']
        # change below to be googleDf
        googleDf['review_count_score'] = (googleDf['review_count']  - googleDf['review_count'].min()) / (googleDf['review_count'].max() - googleDf['review_count'].min())
        # applies the getGoogleCategories function to the 'types' column and saves it as a new column called categories.
        googleDf['categories'] = googleDf['types'].apply(getGoogleCategories)
        # calculates the score to be given for display order (The order it would appear when searched).  It uses min-max scaling.
        googleDf['displayOrder_score'] = ((googleDf['displayOrder']) / googleDf['displayOrder'].max())
        # gets the length of the list in the types column
        googleDf['categories_len'] = googleDf['types'].apply(lambda x: len(x))
        # gets the score of the categories column. It uses min-max scaling
        googleDf['categories_score'] = (googleDf['categories_len'] - 1) / (googleDf['categories_len'].max() - 1)
        # get the phone number and rename to match yelpDf
        googleDf.rename({'international_phone_number':'display_phone'}, axis=1, inplace=True)

        
        # uses the rankGoogle() function from above to perform a row wise calculation
        googleDf['score'] = googleDf.apply(lambda x: rankGoogle(x), axis=1)
        # performs min-max scaling and then multiplies it by 100 to turn it into a percentage.  
        # This percentage is a percentage of the things they are doing wrong compared to their competitors.
        # The best possible for a business to have is 0% and the worst possible would be 100%.
        # Mike would want to talk to those closer to 100%.
        googleDf['score'] = 100 - (googleDf['score'] / googleDf['score'].max()) * 100
        # sorts the rows by the score so those with the worst score are on top.
        googleDf.sort_values(['score'], ascending=False, inplace=True)
        # converts the score column from a float into a string of the format "{score}%"
        googleDf['score'] = googleDf['score'].apply(lambda x: f'{x:.2f}%')
        # replace website zeros with "No Website Listed"
        googleDf['website'] = googleDf['website'].apply(lambda x: "No Website Listed" if not x else x)
        # replace hours zeros with "No Hours Listed"
        googleDf['opening_hours.weekday_text'] = googleDf['opening_hours.weekday_text'].apply(lambda x: "No Hours Listed" if not x else x)
        # set emails series to a default value
        googleDf['emails'] = googleDf.apply(lambda row: get_email(row) if row['website'] != 'No Website Listed' else 'No Email Listed', axis=1)
        googleDf['last_name'] = 'unknown'
        googleDf['location_search'] = location
        googleDf['business_search'] = business
        googleDf['source_search'] = source
        googleDf['location.display_address'] = googleDf['formatted_address']

        options = [{'label':company, 'value':company} for company in googleDf.name.values]

        return googleDf.to_dict('records'), options, html.H2('Google'), googleDf.to_dict('records')


####################################################################################
#### func:  Description: downloads the data in globalDf as a .csv file          ####
####################################################################################
@app.callback(
    Output("download_full_csv", "data"),
    Input("btn_full_csv", "n_clicks"),
    [State("locationInput", "value"),
    State("businessInput", "value"),
    State('dataSourceSelect', 'value'),
    State('globalDf', 'data')],
    prevent_initial_call=True)
def func(n_clicks, location, business, dataSource, globalDf):
    try:
        return dcc.send_data_frame(pd.DataFrame(globalDf).to_csv, f"{dataSource}_{location}_{business}_rankingsResultsFull_{datetime.datetime.now().date()}.csv")
    except:
        raise PreventUpdate

####################################################################################
#### func:  Description: downloads the data in globalDf as a .csv file          ####
####################################################################################
@app.callback(
    Output("download_subset_csv", "data"),
    Input("btn_subset_csv", "n_clicks"),
    [State("locationInput", "value"),
    State("businessInput", "value"),
    State('dataSourceSelect', 'value'),
    State('globalDf', 'data')],
    prevent_initial_call=True)
def func2(n_clicks, location, business, dataSource, globalDf):
    try:
        return dcc.send_data_frame(pd.DataFrame(globalDf)[['name', 'rating', 'website', 'last_name', 'display_phone', 'Email', 'location.display_address', 'location_search', 'business_search', 'source_search']].to_csv, f"{dataSource}_{location}_{business}_rankingsResultsSubset_{datetime.datetime.now().date()}.csv")
    except:
        raise PreventUpdate

@app.callback(
    [Output('company-header', 'children'),
    Output('ktfiga-website', 'children'),
    Output('ktfiga-phone', 'children'),
    Output('ktfiga-hoo', 'children'),
    Output('ktfiga-add', 'children'),
    Output('ktfiga-cat', 'children'),
    Output('ktfiga-emails', 'children'),
    Output('ktfiga-rat', 'children'),
    Output('ktfiga-rc', 'children'),
    Output('ktfiga-sdo', 'children'),
    Output('ktfiga-pa', 'children'),
    Output('ktfiga-pm', 'children')],
    Input('companies-dropdown', 'value'),
    [State('dataSourceSelect', 'value'),
    State('globalDf', 'data')], prevent_initial_call=True)
def kermitTheFrogIsGayApparently(companyName, source, globalDf):
    globalDf = pd.DataFrame(globalDf)
    kTFIGADf = globalDf.copy()[globalDf.name == companyName].reset_index(drop=True)
    emailsString = ''
    hoursString = ''
    if source == 'yelp':
        sourceText = ' | Yelp SEO'
        emailsString = kTFIGADf['emails'].loc[0]
        hoursString = kTFIGADf['opening_hours.weekday_text'].loc[0]
    else:
        sourceText = ' | Google SEO'
        emailsList = kTFIGADf['emails'].loc[0]
        for email in emailsList:
            emailsString = emailsString + email + '\n'
        hoursList = kTFIGADf['opening_hours.weekday_text'].loc[0]
        for hours in hoursList:
            hoursString = hoursString + hours + '\n'
        if len(kTFIGADf['emails'].loc[0]) <= 1: 
            emailsString = kTFIGADf['emails'].loc[0]
        if len(kTFIGADf['opening_hours.weekday_text'].loc[0]) <= 1:
            hoursString = kTFIGADf['opening_hours.weekday_text'].loc[0]
    
    return [companyName + sourceText, kTFIGADf['website'].loc[0], kTFIGADf['display_phone'].loc[0], hoursString, 
    kTFIGADf['location.display_address'].loc[0], kTFIGADf['categories'].loc[0], emailsString, kTFIGADf['rating'].loc[0],
    kTFIGADf['review_count'].loc[0], kTFIGADf['displayOrder'].loc[0] + 1, kTFIGADf['photosLength'].loc[0], kTFIGADf['score'].loc[0]]


@app.callback(
    [Output('inputRow', 'style'),
    Output('companies-dropdown-col', 'style'),
    Output('bTableTab', 'style')],
    Input('printButton', 'n_clicks'), prevent_initial_call=True)
def printToggle(n_clicks):
    if n_clicks % 2 == 1:
        return {'display':'none'}, {'display':'none'}, {'display':'none'}
    return {}, {'padding':'1rem'}, {}


####################################################################################
#### getResultsTable:  Description: This function checks whether the yelp or    ####
####                   google option is selected, aggregates the data from      ####
####                   the api related to the source, cleans the data, and      ####
####                   then returns the data back to the dashTable.             ####
####################################################################################
@app.callback(
    [Output("googTable", "data"),
    Output('yelpTable', 'data'),
    Output('yelpGlobalDf', 'data'),
    Output('googDf', 'data')],
    Input("btn_tables_search", "n_clicks"),
    [State("businessInput", "value"),
    State('locationInput', 'value'),
    State('radiusInput', 'value')],
    prevent_initial_call=True)
def getResultsTables(n_clicks, business, location, radius):
    if location is None or business is None or radius is None or location == '' or business == '' or radius == '':
        raise PreventUpdate 
    yelpDf = getYelpResults(location, business)
    # applies the getYelpCategories to the categories column and saves it to the same column
    yelpDf['categories'] = yelpDf['categories'].apply(getYelpCategories)
    # calculates the score to be given for review counts.  It uses min-max scaling.
    yelpDf['review_count_score'] = (yelpDf['review_count']  - yelpDf['review_count'].min()) / (yelpDf['review_count'].max() - yelpDf['review_count'].min())
    # calculates the length of the list in the categories column.
    yelpDf['categories_len'] = yelpDf['categories'].str.split(',').apply(lambda x: len(x))
    # calculates the score to be given for categories length.  It uses min-max scaling.
    yelpDf['categories_score'] = (yelpDf['categories_len'] - 1) / (yelpDf['categories_len'].max() - 1)
    # calculates the score to be given for display order (The order it would appear when searched).  It uses min-max scaling.
    yelpDf['displayOrder_score'] = ((yelpDf['displayOrder']) / yelpDf['displayOrder'].max())
    # calculates the length of the words in companies name.  This is to get some idea of a descriptive title.
    yelpDf['listingWordCount'] = yelpDf['name'].apply(lambda x: len(x.split()))
    # calculates the score to be given for businesses name.  It uses min-max scaling.
    yelpDf['listingWordCount_score'] = (yelpDf['listingWordCount'] - yelpDf['listingWordCount'].min()) / (yelpDf['listingWordCount'].max() -  yelpDf['listingWordCount'].min())
    # pull the address out of its list
    yelpDf['location.display_address'] = yelpDf['location.display_address'].apply(lambda x: x[0] if x is not None and len(x) == 1 else x[0] + ' ' + x[1] if x is not None and len(x) == 2 else x[0] + ' ' + x[1] + ' ' + x[2] if x is not None and len(x) == 3 else '')

    try:
        # # calculates the length of the list in the photos column
        yelpDf['photosLength'] = yelpDf['photos'].apply(lambda x: len(x) if x is not None and type(x) is list else 0)
    except: 
        # yelpDf['photos'] = 0
        yelpDf['photosLength'] = 0

    # yelpDf['photosLength'] = yelpDf['photos'].apply(lambda x: len(x) if x is not None and x != '' else 0)

    # uses the rankYelp() function from above to perform a row wise calculation
    yelpDf['score'] = yelpDf.apply(lambda x: rankYelp(x), axis=1)
    # performs min-max scaling and then multiplies it by 100 to turn it into a percentage.  
    # This percentage is a percentage of the things they are doing wrong compared to their competitors.
    # The best possible for a business to have is 0% and the worst possible would be 100%.
    # Mike would want to talk to those closer to 100%.
    yelpDf['score'] = 100 - (yelpDf['score'] / yelpDf['score'].max()) * 100
    # sorts the rows by the score so those with the worst score are on top.
    yelpDf.sort_values(['score'], ascending=False, inplace=True)
    # converts the score column from a float into a string of the format "{score}%"
    yelpDf['score'] = yelpDf['score'].apply(lambda x: f'{x:.2f}%')
    # set website series to a default value
    yelpDf['website'] = "Website Info Unavailable"
    # set hours series to a default value
    yelpDf['opening_hours.weekday_text'] = "Hours Info Unavailable"
    # set emails series to a default value
    yelpDf['emails'] = "Emails Info Unavailable"
    yelpDf['last_name'] = 'unknown'
    yelpDf['location_search'] = location
    yelpDf['business_search'] = business
    yelpDf['source_search'] = 'yelp'

    # note: most of the renaming is just to match the name of the columns from the yelp api

    # get the google data
    googleDf = getGooglePlaceDetails(location, business, radius=radius)
    try:
        googleDf['photosLength'] = googleDf['photos'].apply(lambda x: len(x) if x is not None and type(x) is list else 0)
    except:
        googleDf['photosLength'] = 0
    # fill nans in the dataframe
    googleDf.fillna(0, inplace=True)

    # create a copy of the 'user_ratings_total' column and call it 'review_count'
    googleDf['review_count'] = googleDf['user_ratings_total']
    # change below to be googleDf
    googleDf['review_count_score'] = (googleDf['review_count']  - googleDf['review_count'].min()) / (googleDf['review_count'].max() - googleDf['review_count'].min())
    # applies the getGoogleCategories function to the 'types' column and saves it as a new column called categories.
    googleDf['categories'] = googleDf['types'].apply(getGoogleCategories)
    # calculates the score to be given for display order (The order it would appear when searched).  It uses min-max scaling.
    googleDf['displayOrder_score'] = ((googleDf['displayOrder']) / googleDf['displayOrder'].max())
    # gets the length of the list in the types column
    googleDf['categories_len'] = googleDf['types'].apply(lambda x: len(x))
    # gets the score of the categories column. It uses min-max scaling
    googleDf['categories_score'] = (googleDf['categories_len'] - 1) / (googleDf['categories_len'].max() - 1)
    # get the phone number and rename to match yelpDf
    googleDf.rename({'international_phone_number':'display_phone'}, axis=1, inplace=True)

    
    # uses the rankGoogle() function from above to perform a row wise calculation
    googleDf['score'] = googleDf.apply(lambda x: rankGoogle(x), axis=1)
    # performs min-max scaling and then multiplies it by 100 to turn it into a percentage.  
    # This percentage is a percentage of the things they are doing wrong compared to their competitors.
    # The best possible for a business to have is 0% and the worst possible would be 100%.
    # Mike would want to talk to those closer to 100%.
    googleDf['score'] = 100 - (googleDf['score'] / googleDf['score'].max()) * 100
    # sorts the rows by the score so those with the worst score are on top.
    googleDf.sort_values(['score'], ascending=False, inplace=True)
    # converts the score column from a float into a string of the format "{score}%"
    googleDf['score'] = googleDf['score'].apply(lambda x: f'{x:.2f}%')
    # replace website zeros with "No Website Listed"
    googleDf['website'] = googleDf['website'].apply(lambda x: "No Website Listed" if not x else x)
    # replace hours zeros with "No Hours Listed"
    googleDf['opening_hours.weekday_text'] = googleDf['opening_hours.weekday_text'].apply(lambda x: "No Hours Listed" if not x else x)
    # set emails series to a default value
    googleDf['emails'] = googleDf.apply(lambda row: get_email(row) if row['website'] != 'No Website Listed' else 'No Email Listed', axis=1)
    googleDf['last_name'] = 'unknown'
    googleDf['location_search'] = location
    googleDf['business_search'] = business
    googleDf['source_search'] = 'google'
    googleDf['location.display_address'] = googleDf['formatted_address']

    return googleDf.to_dict('records'), yelpDf.to_dict('records'), googleDf.to_dict('records'), yelpDf.to_dict('records')


####################################################################################
#### func:  Description: downloads the data as a .csv file                      ####
####################################################################################
@app.callback(
    Output("download_fulls_csv", "data"),
    Input("btn_fulls_csv", "n_clicks"),
    [State("locationInput", "value"),
    State("businessInput", "value"),
    State('yelpGlobalDf', 'data'),
    State('googDf', 'data')],
    prevent_initial_call=True)
def func3(n_clicks, location, business, googDf, yelpGlobalDf):
    try:
        tempDf = pd.concat([pd.DataFrame(googDf), pd.DataFrame(yelpGlobalDf)], ignore_index=True)
        return dcc.send_data_frame(tempDf.to_csv, f"{location}_{business}_rankingsResultsFull_{datetime.datetime.now().date()}.csv")
    except:
        raise PreventUpdate

####################################################################################
#### func:  Description: downloads the data as a .csv file                      ####
####################################################################################
@app.callback(
    Output("download_subsets_csv", "data"),
    Input("btn_subsets_csv", "n_clicks"),
    [State("locationInput", "value"),
    State("businessInput", "value"),
    State('yelpGlobalDf', 'data'),
    State('googDf', 'data')],
    prevent_initial_call=True)
def func4(n_clicks, location, business, googDf, yelpGlobalDf):
    try:
        tempDf = pd.concat([pd.DataFrame(googDf), pd.DataFrame(yelpGlobalDf)], ignore_index=True)
        return dcc.send_data_frame(pd.DataFrame(tempDf[['name', 'rating', 'website', 'last_name', 'display_phone', 'Email', 'location.display_address', 'location_search', 'business_search', 'source_search']]).to_csv, f"{location}_{business}_rankingsResultsSubset_{datetime.datetime.now().date()}.csv")
    except:
        raise PreventUpdate


# -------------------------- MAIN ---------------------------- #

# standard code to start the app. port 8080 is what google cloud uses
if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8080, debug=False, use_reloader=False)