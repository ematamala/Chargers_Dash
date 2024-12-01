import dash
from dash import dcc, html, Input, Output, ClientsideFunction
import numpy as np
import pandas as pd
import datetime
from datetime import datetime as dt
import pathlib


app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
app.title = "CityVitae Contract Dashboard"

server = app.server
app.config.suppress_callback_exceptions = True

# Path
BASE_PATH = pathlib.Path(__file__).parent.resolve()
DATA_PATH = BASE_PATH.joinpath("data").resolve()

# Read data
df_tr = pd.read_csv(DATA_PATH.joinpath("transactions_history.csv"))     # Transaction History
df_chargers = pd.read_csv(DATA_PATH.joinpath("charge_box2.csv"))        # Chargers
df_contracts = pd.read_csv(DATA_PATH.joinpath("contract.csv"))          # Contracts

# remove unused columns
df_tr.drop(columns=["connector_pk", "type" , "id_tag", "city","street","house_number","country" ,"tariffKW","unitsKW","tariffMIN","unitsMIN","date_registered","status","comment","chkSuspendedEV","gracePeriod" , "suspendedEV_timestamp"], inplace=True)
df_contracts.drop(columns=["enterprises_id","contract_type","date_signed","date_start","date_end","houseowner_id","prefix","status","balance_in","balance_out","notifications_contact_id"], inplace=True)

# Combine Data Frames to incorporate name of contract, first import id contract of each charger
df_tr = df_tr.merge(df_chargers, how="left", on="charge_box_id")
# Combine Data Frames to incorporate name of contract, second import  name of each charger
df_tr = df_tr.merge(df_contracts, how="left", left_on="contract_id", right_on="id", validate="many_to_one")
df_tr["Number of Records"] = 1

# Format Time and date
df_tr["start_timestamp"] = df_tr["start_timestamp"].apply(lambda x: dt.strptime(x, "%Y-%m-%d %H:%M:%S.%f"))  # String -> Datetime
df_tr["stop_timestamp"]  = df_tr["stop_timestamp"].apply(lambda x: dt.strptime(x, "%Y-%m-%d %H:%M:%S.%f"))  # String -> Datetime

# Converts UTC Time to Local Time
df_tr["start_timestamp"] = pd.DatetimeIndex(pd.to_datetime(df_tr["start_timestamp"], format='%Y-%m-%d %H:%M:%S')).tz_localize("UTC").tz_convert('America/New_York')
df_tr["stop_timestamp"] = pd.DatetimeIndex(pd.to_datetime(df_tr["stop_timestamp"], format='%Y-%m-%d %H:%M:%S')).tz_localize("UTC").tz_convert('America/New_York')

# Insert weekday
df_tr["Days of Wk"] = df_tr["Start Hour"] = df_tr["start_timestamp"]
df_tr["Days of Wk"] = df_tr["Days of Wk"].apply(lambda x: dt.strftime(x, "%A"))  # Datetime -> weekday string

# Insert Start Hour
df_tr["Start Hour"] = df_tr["Start Hour"].apply(lambda x: dt.strftime(x, "%H"))

# Insert Duration in hours
df_tr["Duration_HH"] = df_tr["stop_timestamp"] - df_tr["start_timestamp"]
df_tr["Duration_HH"] = round(df_tr["Duration_HH"].dt.seconds / 3600, 0)

#Create List of Contracts
contracts_list = df_tr["name"].unique()

# create a list Create dictionary with a list of chargers of each contract
# no used now fot the furure
list_contract_charger = []
for contract in contracts_list:
    filtered_by_contract = df_tr[df_tr["name"] == contract]
    list_chargers_in_contract = filtered_by_contract["charge_box_id"].unique()
    list_contract_charger.append({"contract" : contract , "chargers" : list_chargers_in_contract })

#Create List of Days
day_list = ["Sunday","Saturday","Friday","Thursday","Wednesday","Tuesday","Monday"]

# Register all chargers
chargers_list = df_tr["charge_box_id"].unique().tolist()
wait_time_inputs = [Input((i + "_wait_time_graph"), "selectedData") for i in contracts_list]
score_inputs = [Input((i + "_score_graph"), "selectedData") for i in contracts_list]

# Head of the Dashboard
def description_card():
    """

    :return: A Div containing dashboard title & descriptions.
    """
    return html.Div(
        id="description-card",
        children=[
            html.H5("Chargers Use Analytics"),
            html.H3("Chargers Use Dashboard"),
            html.Div(
                id="intro",
                children="Explore charger use by Contract.",
            ),
        ],
    )


def generate_control_card():
    """

    :return: A Div containing controls for graphs.
    """


    return html.Div(
        id="control-card",
        children=[
            # Drop down menu to select contract.
            html.P("Select Contract"),
            dcc.Dropdown(
                id="contract-select",
                options=[{"label": i, "value": i} for i in contracts_list],
                value=contracts_list[0],
            ),

            html.Br(),
            # Drop down menu to select start and end date.
            html.P("Select Check-In Time"),
            dcc.DatePickerRange(
                id="date-picker-select",
                start_date=dt(2022, 12, 1),
                end_date=dt(2024, 10, 31),
                min_date_allowed=dt(2022, 1, 1),
                max_date_allowed=dt(2024, 12, 31),
                initial_visible_month=dt(2024, 10, 1),
            ),
            html.Br(),
            html.Br(),
            html.Br(),
        ],
    )


def generate_charger_volume_heatmap(start, end, contract, hm_click, reset):
    """
    :param: start: start date from selection.
    :param: end: end date from selection.
    :param: contract: contract from selection.
    :param: hm_click: clickData from heatmap.
    :param: charger_type: list of chargers from selection.
    :param: reset (boolean): reset heatmap graph if True.

    :return: Patient volume annotated heatmap.
    """
    #Filters by Contract and selected chargers
    filtered_df = df_tr[
        (df_tr["name"] == contract) & True
    ]
    #Filters by Start and End Date
    filtered_df = filtered_df.sort_values("start_timestamp").set_index("start_timestamp")[
        start:end
    ]
    x_axis = [datetime.time(i).strftime("%H") for i in range(24)]  # 24hr time list
    y_axis = day_list
    pd.set_option('display.max_columns', None)

    hour_of_day = ""
    weekday = ""
    shapes = []

    if hm_click is not None:
        hour_of_day = hm_click["points"][0]["x"]
        weekday = hm_click["points"][0]["y"]

        # Add shapes
        x0 = x_axis.index(hour_of_day) / 24
        x1 = x0 + 1 / 24
        y0 = y_axis.index(weekday) / 7
        y1 = y0 + 1 / 7

        shapes = [
            dict(
                type="rect",
                xref="paper",
                yref="paper",
                x0=x0,
                x1=x1,
                y0=y0,
                y1=y1,
                line=dict(color="#ff6347"),
            )
        ]

    # Get z value : sum(number of records) based on x, y,


# --------------------

    z = np.zeros((7, 24))
    annotations = []

    for ind in filtered_df.index:
        dia = filtered_df['Days of Wk'][ind]
        hour_st = int(filtered_df['Start Hour'][ind])
        dura = int(filtered_df["Duration_HH"][ind])
        hora2 = hour_st
        dia2 = dia
        #print(f"dia:{dia} Hora Inicio {hora}  Duracion {dura}")
        for i in range(dura):
            hora2 = hour_st + i
            if hora2 > 23:
                hora2 = hora2 - 24
                if dia == "Monday":
                    dia2 = "Tuesday"
                elif dia == "Tuesday":
                    dia2 = "Wednesday"
                elif dia == "Wednesday":
                    dia2 = "Thursday"
                elif dia == "Thursday":
                    dia2 = "Friday"
                elif dia == "Friday":
                    dia2 = "Saturday"
                elif dia == "Saturday":
                    dia2 = "Sunday"
                elif dia == "Sunday":
                    dia2 = "Monday"
            ind_x = int(hora2)
            ind_y = day_list.index(dia2)
            z[ind_y][ind_x] = z[ind_y][ind_x] + 1

#["Sunday","Saturday","Friday","Thursday","Wednesday","Tuesday","Monday"]
#--------------
    annotations = []

    for ind_y, day in enumerate(y_axis):
        filtered_day = filtered_df[filtered_df["Days of Wk"] == day]
        for ind_x, x_val in enumerate(x_axis):
            sum_of_record = int(z[ind_y][ind_x])
            annotation_dict = dict(
                showarrow=False,
                text="<b>" + str(sum_of_record) + "<b>",
                xref="x",
                yref="y",
                x=x_val,
                y=day,
                font=dict(family="sans-serif"),
            )
            # Highlight annotation text by self-click
            if x_val == hour_of_day and day == weekday:
                if not reset:
                    annotation_dict.update(size=15, font=dict(color="#ff6347"))

            annotations.append(annotation_dict)

    # Heatmap
    hovertemplate = "<b> %{y}  %{x} <br><br> %{z} Charges"

    data = [
        dict(
            x=x_axis,
            y=y_axis,
            z=z,
            type="heatmap",
            name="",
            hovertemplate=hovertemplate,
            showscale=False,
            colorscale=[[0, "#caf3ff"], [1, "#2c82ff"]],
        )
    ]

    layout = dict(
        margin=dict(l=70, b=50, t=50, r=50),
        modebar={"orientation": "v"},
        font=dict(family="Open Sans"),
        annotations=annotations,
        shapes=shapes,
        xaxis=dict(
            side="top",
            ticks="",
            ticklen=2,
            tickfont=dict(family="sans-serif"),
            tickcolor="#ffffff",
        ),
        yaxis=dict(
            side="left", ticks="", tickfont=dict(family="sans-serif"), ticksuffix=" "
        ),
        hovermode="closest",
        showlegend=False,
    )
    return {"data": data, "layout": layout}

app.layout = html.Div(
    id="app-container",
    children=[
        # Banner
        html.Div(
            id="banner",
            className="banner",
            children=[html.Img(src=app.get_asset_url("Logo_CityVitae.png"))],
        ),
        # Left column

        html.Div(
            id="left-column",
            className="four columns",
            children=[description_card(), generate_control_card()]
            + [
                html.Div(
                    ["initial child"], id="output-clientside", style={"display": "none"}
                )
            ],
        ),
        # Right column
        html.Div(
            id="right-column",
            className="eight columns",
            children=[
                # Start Time Heatmap
                html.Div(
                    id="charger_volume_card",
                    children=[
                        html.B(f"Start Hour Time and Day"),
                        html.Hr(),
                        dcc.Graph(id="charger_volume_hm"),
                        html.Div(
                            id="reset-btn-outer",
                            children=html.Button(id="reset-btn", children="Show All", n_clicks=0),
                        ),
                    ],
                ),
            ],
        ),
    ],
)

@app.callback(
    Output("charger_volume_hm", "figure"),
    [
        Input("date-picker-select", "start_date"),
        Input("date-picker-select", "end_date"),
        Input("contract-select", "value"),
        Input("charger_volume_hm", "clickData"),
        Input("reset-btn", "n_clicks"),
   ],
)

def update_heatmap(start, end, contract, hm_click,  reset_click):
    start = start + " 00:00:00"
    end = end + " 00:00:00"

    reset = False
    # Find which one has been triggered
    ctx = dash.callback_context

    if ctx.triggered:
        prop_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if prop_id == "reset-btn":
            reset = True

    # Return to original hm(no colored annotation) by resetting

    return generate_charger_volume_heatmap(
        start, end, contract, hm_click, reset
    )


app.clientside_callback(
    ClientsideFunction(namespace="clientside", function_name="resize"),
    Output("output-clientside", "children"),
    [Input("wait_time_table", "children")] + wait_time_inputs + score_inputs,
)

# Run the server
if __name__ == "__main__":
    app.run_server(debug=True)

