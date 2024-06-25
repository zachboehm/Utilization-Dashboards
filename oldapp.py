import pandas as pd
import plotly_express as px
import streamlit as st
import matplotlib as plt
import datetime

st.set_page_config(page_title='Hours Dashboard',
                   page_icon=':bar_chart:',
                   layout='wide')


#Clean up the File and establish some parameters
with st.sidebar:
    uploaded_file = st.file_uploader('Upload Workplace CSV Export:')

df = pd.read_csv(uploaded_file)

# Check if the client column is blank and the PTO column contains 'TRUE'
mask = (df['Client'].isnull()) & (df['PTO'] == 'TRUE')

# Update the client column based on the conditions
df.loc[mask, 'Client'] = 'PTO'
df.loc[df['Client'].isnull(), 'Client'] = 'Admin'

nonbillable_clients = ['Admin','PTO']
df['Date'] = pd.to_datetime(df['Date'])
df['Full name'] = df['First name'].str.cat(df['Last name'], sep=' ')
df['Billable'] = ~df['Client'].isin(nonbillable_clients)
df['Month'] = df['Date'].dt.month
df['Year'] = df['Date'].dt.year
df['Client'] = df['Client'].astype(str)


print(df)

with st.sidebar:
    revenue_data = st.file_uploader('Upload QBO P&L by Customer for Matching Time Period:')
    rev_month = st.selectbox('Select Month of Revenue Data:',[1,2,3,4,5,6,7,8,9,10,11,12])
    rev_year = st.selectbox('Select Year of Revenue Data:',[2023,2024])

df1 = pd.read_excel(revenue_data,engine='openpyxl',header=4)
df1.columns.values[0] = 'Item'

if 'TOTAL' in df1.columns:
    df1.drop('TOTAL', axis=1, inplace=True)

df1['Item'] = df1['Item'].str.strip()

strings_to_keep = ['Total Services Revenue',
                   'Total Direct Salaries & Benefits',
                   'Royalty Fees',
                   'Total Expenses',
                   'Net Operating Income']

df1 = df1[df1['Item'].isin(strings_to_keep)]

melted_df = pd.melt(df1, id_vars='Item', var_name='Client', value_name='Value')
melted_df['Month'] = rev_month
melted_df['Year'] = rev_year
melted_df['Client'] = melted_df['Client'].astype(str)

merged_df = pd.merge(df,melted_df, on=['Client', 'Month', 'Year'])

print(merged_df)

client = 'High Country Community Health'



filtered_df = merged_df[merged_df['Client'] == client]
result_df = filtered_df[['Full name','Duration']]
result_df = result_df.groupby(['Full name']).sum().reset_index()

filtered_df1 = filtered_df[filtered_df['Item'] == 'Total Services Revenue']
revenue_for_period = filtered_df1['Value'].max()

print(f'Total Revenue for {client}: {revenue_for_period}')

print(result_df.to_string(index=False))


# ---- SIDEBAR ----
st.sidebar.header('Select Filters Here:')

client = st.sidebar.multiselect(
    'Select Client(s):',
    options=df['Client'].unique(),
    default=None
)

employee = st.sidebar.multiselect(
    'Select Employee(s):',
    options=df['Full name'].unique(),
    default=None
)

default_start_date = df['Date'].min()
default_end_date = df['Date'].max()

start_date = st.sidebar.date_input('Start Date:',value=default_start_date)
end_date = st.sidebar.date_input('End Date:',value=default_end_date)

df_selection = df.query(
    'Client == @client & `Full name` ==@employee & Date >= @start_date & Date <= @end_date'
)

df_selection_emp = df.query(
    '`Full name` ==@employee & Date >= @start_date & Date <= @end_date'
)

df_selection_dates = df.query(
    'Date >= @start_date & Date <= @end_date'
)

df_selection_clients = df.query(
    'Client == @client & Date >= @start_date & Date <= @end_date'
)

 # ---- MAINPAGE ----
st.title('Workplace Timecard Visualizer')
st.subheader(f'Timecard Dataset Summary from {start_date} to {end_date}')

# DATASET OVERVIEW Billable Percentage
left_column_1, right_column_1 = st.columns(2)
billable_hours_by_emp = df_selection_dates.groupby(['Full name', 'Billable'])['Duration'].sum().unstack(fill_value=0).reset_index()
billable_hours_by_emp.columns = ['Full name', 'Non-Billable Hours', 'Billable Hours']
billable_hours_by_emp['Billable Percentage'] = (billable_hours_by_emp['Billable Hours'] / (billable_hours_by_emp['Billable Hours'] + billable_hours_by_emp['Non-Billable Hours'])).round(3) * 100

# DATASET OVERVIEW All Client Hours [Bar Chart]
all_client_hours = df_selection_dates[~df_selection_dates['Client'].str.contains('Admin')]
all_client_hours = all_client_hours.groupby(by=['Client']).sum(numeric_only=True)[['Duration']].sort_values('Duration',ascending=True).tail(15)
fig_all_client_hours = px.bar(
    all_client_hours,
    x='Duration',
    y=all_client_hours.index,
    orientation='h',
    title=f'Top 15 Clients by Hours from {start_date} to {end_date}',
    template='plotly_white'
)

# DATASET OVERVIEW All Client Revenue [Bar Chart]
all_client_revenue = merged_df[merged_df['Item']=='Total Services Revenue']
all_client_revenue = all_client_revenue.groupby(by=['Client']).max(numeric_only=True)[['Value']].sort_values('Value',ascending=True).tail(15)
fig_all_client_revenue = px.bar(
    all_client_revenue,
    x='Value',
    y=all_client_revenue.index,
    orientation='h',
    title=f'Top 15 Clients by Revenue from {start_date} to {end_date}',
    template='plotly_white'
)


with left_column_1:
    st.dataframe(billable_hours_by_emp.sort_values('Billable Percentage',ascending=False), hide_index=True, column_config={'Billable Percentage':st.column_config.ProgressColumn('Billable Percentage',format='%d',min_value=0,max_value=100)},use_container_width=True)

    
with right_column_1:
    right_column_1.plotly_chart(fig_all_client_hours, use_container_width=True)
    right_column_1.plotly_chart(fig_all_client_revenue, use_container_width=True)
    
st.markdown('---')

# ---- Employee Detail ----

st.subheader('Employee Detail (Filterable by Employee and Date)')

# Table showing all Clients for a given Employee with billable percentage for the time period
total_hours_by_client = df_selection_emp.groupby('Client')['Duration'].sum().reset_index()
total_non_billable_hours = total_hours_by_client[total_hours_by_client['Client'].isin(nonbillable_clients)]['Duration'].sum()
total_hours = total_hours_by_client['Duration'].sum().round(1)
emp_billable_pct = ((total_hours - total_non_billable_hours) / total_hours).round(3) * 100
st.text(f'By Client Breakdown for {employee}, Total Hours: {total_hours}')

# Pie chart visualising the table above
fig_total_hours_by_client = px.pie(total_hours_by_client,values='Duration',names='Client')

left_column_2, right_column_2 = st.columns(2)
with left_column_2:
    st.dataframe(total_hours_by_client,hide_index=True,use_container_width=True)

with right_column_2:
    right_column_2.plotly_chart(fig_total_hours_by_client, use_container_width=True)
    

# ---- Client Detail ----

st.markdown('---')

total_hours_by_emp = df_selection_clients.groupby('Full name')['Duration'].sum().reset_index()
total_hours_emp = total_hours_by_emp['Duration'].sum().round(1)


st.subheader('Client Detail (Filterable by Client and Date)')
st.text(f'{client} Time Breakdown by Employee, Total Hours: {total_hours_emp}')  
st.dataframe(total_hours_by_emp,hide_index=True,use_container_width=True)
