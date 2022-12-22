from flask import Flask, render_template

app = Flask(__name__)
server = app.server

@app.route('/plot/')

def plot():
    import json
    from bokeh.plotting import figure, output_file, show
    from bokeh.models import ColumnDataSource, LogColorMapper, GeoJSONDataSource, LinearColorMapper, ColorBar, Range1d, NumeralTickFormatter, HoverTool
    from bokeh.palettes import Category20c, Spectral, GnBu, brewer, PRGn, RdYlGn
    from bokeh.palettes import Viridis6 as palette
    from bokeh.transform import cumsum
    from bokeh.embed import components
    from bokeh.resources import CDN

    import geopandas as gpd
    import pandas as pd
    import numpy as np
    import math

    from bs4 import BeautifulSoup
    import requests

    desal_url = 'https://en.wikipedia.org/wiki/Desalination_by_country'
    table_cl = "wikitable sortable"

    response = requests.get(desal_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    desal_table = soup.find('table', attrs={'class': table_cl})

    # Load Data
    des = pd.read_html(str(desal_table))[0]

    # Convert capacity to integer
    des['capacity (cum)'] = des['Capacity (per day)'].apply(lambda x: x.split(' ')[0][:-3].replace(',', ''))
    des['capacity (cum)'] = pd.to_numeric(des['capacity (cum)'], downcast="integer")

    # Feature engineering
    des.drop(['Completion', 'Coordinates', 'Completion', 'Capacity (per day)'], axis=1, inplace=True)
    des.columns = ['country', 'territory', 'city', 'name', 'capacity_cum (per day)']
    des['country'].fillna("Baja", inplace=True)

    df = des.groupby('country')['capacity_cum (per day)'].agg(['sum', 'count']).reset_index()

    df.columns = ['country', 'capacity', 'plants']
    
    # Load Patches (Geometry)
    borders = 'ne_110m_admin_0_countries.shp'
    gdf = gpd.read_file(borders)[['ADMIN', 'ADM0_A3', 'geometry']]

    # Rename columns
    gdf.columns = ['country', 'country_code', 'geometry']

    ## Map
    # Initiate Map Chart
    # Merge data with co-ordinates
    geo_df = gdf.merge(df, left_on='country', right_on='country', how='left')

    # Read data to json
    df_json = json.loads(geo_df.to_json())

    # Convert to string like object
    map_data = json.dumps(df_json)

    # Assign Source
    map_source = GeoJSONDataSource(geojson = map_data)

    # Color Mapper
    color_mapper = LinearColorMapper(palette=palette[::-1],
            low=df['capacity'].min(), high=df['capacity'].max())

    # Colour scale
    tick_labels = {
            '2': 'Index 2',
            '3': 'Index 3',
            '4':'Index 4',
            '5':'Index 5',
            '6':'Index 6',
            '7':'Index 7',
            '8':'Index 8'
            }

    color_bar = ColorBar(color_mapper=color_mapper, label_standoff=5, width = 600, height = 30,
        border_line_color=None,location = (20,0), orientation = 'horizontal',
        major_label_overrides = tick_labels)

    # Map
    TOOLS = "pan,wheel_zoom,reset,hover,save"

    map_fig = figure(plot_width=725, plot_height=500, 
            tools=TOOLS, x_axis_location=None, y_axis_location=None,
            tooltips = [
                ("Country", "@country"),
                ("Daily capacity", "$@capacity{0,0.0}"),
                ("Operational plants", "@plants")
                ])

    map_fig.grid.grid_line_color = None
    map_fig.hover.point_policy = "follow_mouse"
    
    # Assign patches
    map_fig.patches("xs", "ys", source=map_source, fill_color={"field":"capacity", "transform":color_mapper},
            fill_alpha=0.7, line_color="black", line_width=0.5)
    
    map_fig.add_layout(color_bar, 'below')
    
    # Upload components to variables
    script_m, div_m = components(map_fig)
    
    # Upload page to Javascript
    js_page = CDN.js_files[0]

    return render_template("plot.html",
            script_m=script_m,
            div_m=div_m,
            js_page=js_page)

if __name__ =="__main__":
    app.run(debug=True)
