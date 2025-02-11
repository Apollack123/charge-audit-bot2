import streamlit as st
import pandas as pd

# Function to process charge breakdown reports
def process_charge_report(files):
    results = []
    for file in files:
        df = pd.read_excel(file, header=None, dtype=str, engine="openpyxl")  # Read file as string
        file_name = file.name  # Get file name

        # Debugging: Show raw data preview
        st.write(f"Raw Data Preview for {file_name}:", df.head())

        # Find the first row that looks like column headers
        for i, row in df.iterrows():
            if any(isinstance(val, str) and ("lotr" in val.lower() or "lot rent" in val.lower()) for val in row.values):
                df.columns = row.astype(str)  # Set this row as header
                df = df[i + 1:].reset_index(drop=True)  # Remove rows above header
                break

        # Convert column names to strings and normalize
        df.columns = df.columns.astype(str).str.lower().str.strip()

        # Ensure all data is converted to strings
        df = df.astype(str).applymap(lambda x: x.strip() if isinstance(x, str) else "")

        # Remove non-printable characters and possible corrupt values
        df.replace(r'[^ -~]', '', regex=True, inplace=True)

        # Drop any completely empty columns
        df = df.dropna(axis=1, how="all")

        # Handle potential variations of 'LotR' column name
        lotr_column = None
        for col in df.columns:
            if isinstance(col, str) and ("lotr" in col or "lot rent" in col):
                lotr_column = col
                break

        # Apply audit checks based on detected column names
        df["Audit Result"] = "✅ Passed"
        if lotr_column:
            df.loc[df[lotr_column].str.replace(',', '', regex=True).astype(float) == 0, "Audit Result"] = "⚠️ Missing LotR Charge"
        else:
            df["Audit Result"] = "⚠️ Column 'LotR' Not Found"

        # Additional checks for missing utility fees
        if "sewer_fee" in df.columns:
            df.loc[df["sewer_fee"].isna(), "Audit Result"] = "⚠️ Missing Sewer Fee"
        if "garbage_fee" in df.columns:
            df.loc[df["garbage_fee"].isna(), "Audit Result"] = "⚠️ Missing Garbage Fee"
        if "security_deposit" in df.columns:
            df.loc[df["security_deposit"].isna(), "Audit Result"] = "⚠️ No Security Deposit"

        # Reset index to prevent Streamlit display errors
        df = df.reset_index(drop=True)

        # Drop any problematic columns before displaying
        df = df.loc[:, df.columns.notna()]

        # Ensure all columns are properly formatted as strings
        df = df.astype(str)

        results.append((file_name, df))
    
    return results

# Streamlit Web App UI
st.title("Charge Breakdown Audit Bot - Final Sanitization Mode")
st.write("Upload multiple charge breakdown reports to run an audit.")

# Multiple file uploader
uploaded_files = st.file_uploader("Upload Charge Breakdown Reports (Excel)", type=["xls", "xlsx"], accept_multiple_files=True)

if uploaded_files:
    st.write("Processing files...")
    processed_data = process_charge_report(uploaded_files)
    
    for file_name, df in processed_data:
        st.write(f"Audit Results for: {file_name}")

        # Ensure Streamlit can safely display the dataframe
        df_safe = df.copy()
        df_safe = df_safe.astype(str)  # Convert everything to string format

        # Drop any problematic columns before displaying
        df_safe = df_safe.loc[:, df_safe.columns.notna()]

        st.dataframe(df_safe)  # Display processed data
        
        # Download button for audit results
        csv = df_safe.to_csv(index=False).encode('utf-8')
        st.download_button(f"Download Audit Report for {file_name}", data=csv, file_name=f"{file_name}_audit.csv", mime="text/csv")
