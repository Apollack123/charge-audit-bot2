import streamlit as st
import pandas as pd

# Function to process charge breakdown reports
def process_charge_report(files):
    results = []
    for file in files:
        df = pd.read_excel(file)  # Read the Excel file
        file_name = file.name  # Get file name

        # Debugging: Show column names in Streamlit output
        st.write(f"Columns in {file_name}:", df.columns.tolist())

        # Normalize column names to lowercase and strip spaces
        df.columns = df.columns.str.lower().str.strip()

        # Handle potential variations of 'LotR' column name
        lotr_column = None
        for col in df.columns:
            if "lotr" in col or "lot rent" in col:
                lotr_column = col
                break

        # Apply audit checks based on detected column names
        if lotr_column:
            df["Audit Result"] = "Valid"
            df.loc[df[lotr_column] > 0, "Audit Result"] = "Check Utilities"
        else:
            df["Audit Result"] = "Column 'LotR' not found"

        results.append((file_name, df))
    
    return results

# Streamlit Web App UI
st.title("Charge Breakdown Audit Bot - Debug Mode")
st.write("Upload multiple charge breakdown reports to run an audit.")

# Multiple file uploader
uploaded_files = st.file_uploader("Upload Charge Breakdown Reports (Excel)", type=["xls", "xlsx"], accept_multiple_files=True)

if uploaded_files:
    st.write("Processing files...")
    processed_data = process_charge_report(uploaded_files)
    
    for file_name, df in processed_data:
        st.write(f"Audit Results for: {file_name}")
        st.dataframe(df)  # Display processed data
        
        # Download button for audit results
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(f"Download Audit Report for {file_name}", data=csv, file_name=f"{file_name}_audit.csv", mime="text/csv")
