import pandas as pd
import streamlit as st
import io
from xlsxwriter import Workbook


def format_qb_tb(input_file):

    """
     Formats a Trial Balance Report from QuickBooks Online.
     Report must be ran for the date range and have columns separated by month.
     Important to do before using this tool is to open the excel file and copy-paste everything as values.
     QBO exports reports as formulas (=number) and won't be read unless pasted as a value.
     
    """
    
    # Format the Headers
    df = pd.read_excel(input_file, skiprows=3)
    df.iloc[0] = df.iloc[0].ffill()
    df.iloc[0] = df.iloc[0].astype(str) + ' ' + df.iloc[1].astype(str)
    df = df.drop(1).reset_index(drop=True)
    df.iloc[0, 0] = 'Account'
    df = df.fillna(0)
    df.columns = df.iloc[0]
    df = df.drop(0).reset_index(drop=True)

    # Drop the row with "TOTAL" and all rows below it
    total_index = df[df.iloc[:, 0] == 'TOTAL'].index
    if not total_index.empty:
        df = df.iloc[:total_index[0]]
        
    return df

def calculate_activity(df, last_bal_sheet_acc):

    # Get list of months dynamically
    months = []

    for col in df.columns:
        if 'Debit' in col or 'Credit' in col:
            month_year = ' '.join(col.split(' ')[:-1])
            if month_year not in months:
                months.append(month_year)

    print(months)

    for month in months:
        # Calculate Ending Balance for the current month
        debit_col = f'{month} Debit'
        credit_col = f'{month} Credit'
        df[f'{month} Ending Balance'] = df[debit_col] - df[credit_col]
        
        # If not the first month, calculate the Activity
        if month != months[0]:
            previous_month = months[months.index(month) - 1]
            df[f'{month} Activity'] = df[f'{month} Ending Balance'] - df[f'{previous_month} Ending Balance']
            
    print(months)

    # Rearrange columns
    new_columns = []
    for i in range(len(months)):
        month = months[i]
        new_columns.append(f'{month} Debit')
        new_columns.append(f'{month} Credit')
        new_columns.append(f'{month} Ending Balance')
        if i > 0:
            new_columns.append(f'{month} Activity')

    df = df[['Account'] + new_columns]
    print(df)

    specified_value = last_bal_sheet_acc

    # Find the index of the specified value
    specified_index = df.index[df['Account'] == specified_value].tolist()[0]

    # Create a new DataFrame to hold the results
    result_df = pd.DataFrame(df['Account'])

    # Populate the result DataFrame with the correct values
    for i, month in enumerate(months):
        ending_balance_col = f'{month} Ending Balance'
        activity_col = f'{month} Activity'

        # Initialize a new column for the current month
        result_df[month] = None

        if i == 0:
            # For the first month, use the Ending Balance for all rows
            result_df[month] = df[ending_balance_col]
        else:
            # For subsequent months, fill in the 'Ending Balance' for rows up to and including the specified index
            result_df.loc[:specified_index, month] = df.loc[:specified_index, ending_balance_col]

            # Fill in the 'Activity' for rows below the specified index
            result_df.loc[specified_index + 1:, month] = df.loc[specified_index + 1:, activity_col]
            
    
    return result_df

st.write("Run a QuickBooks online Trial Balance Report and set the columns by month for the time period interested in. Look at the Trial Balance report from Quickbooks, and identify the name of the last balance sheet account in the list of accounts and type it in the box below. It must match exactly or this will not work.")

st.text_input("Last balance sheet Account:")

tb_file = st.file_uploader("select an xlsx trial balance")

if tb_file:
    tb = format_qb_tb(tb_file)
    tb1 = calculate_activity(tb, 'Retained Earnings')


button = st.button("Download Excel File")
if tb_file:
    if button:
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        tb1.to_excel(writer, index=False, sheet_name='Sheet1')
        writer.save()
        output.seek(0)
        st.download_button(
            label="Download",
            data=output,
            file_name='output.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
