import streamlit as st
import pandas as pd
import io

# Function to process charge breakdown reports with Move-In/Move-Out integration
def process_charge_report(charge_files, move_in_out_file):
    results = []
    
    # Load Move-In/Move-Out report
    move_in_out_df = pd.read_excel(move_in_out_file, dtype=str, engine="openpyxl")
    move_in_out_df.columns = move_in_out_df.columns.str.lower().str.strip()
    
    for file in charge_files:
        df = pd.read_excel(file, dtype=str, engine="openpyxl")  # Read file as string
        file_name = file.name  # Get file name

        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()
        
        # Ensure all data is fully converted to strings
        df = df.astype(str).applymap(lambda x: x.strip() if isinstance(x, str) else "")
        df.fillna("", inplace=True)

        # Handle LotR column detection
        lotr_column = next((col for col in df.columns if "lotr" in col or "lot rent" in col), None)
        
        # Apply audit checks
        df["Audit Result"] = "✅ Passed"
        
        # Check for missing LotR charges
        if lotr_column:
            df.loc[df[lotr_column].str.replace(',', '', regex=True).astype(float) == 0, "Audit Result"] = "⚠️ Missing LotR Charge"
        else:
            df["Audit Result"] = "⚠️ Column 'LotR' Not Found"
        
        # Verify Move-In/Move-Out alignment
        if "unit" in df.columns and "move_in_date" in move_in_out_df.columns:
            df = df.merge(move_in_out_df[["unit", "move_in_date"]], on="unit", how="left")
            
            base_rent = 420.00  # Assuming base rent is $420
            
            for index, row in df.iterrows():
                try:
                    move_in_date = pd.to_datetime(row["move_in_date"], errors='coerce')
                    if pd.notna(move_in_date):
                        days_in_month = move_in_date.days_in_month
                        days_not_in_unit = move_in_date.day - 1
                        expected_rent = base_rent - ((base_rent / days_in_month) * days_not_in_unit)
                        df.at[index, "expected_prorated_rent"] = round(expected_rent, 2)

                        actual_rent = float(row[lotr_column].replace(",", ""))
                        if round(expected_rent, 2) != actual_rent:
                            df.at[index, "Audit Result"] = "⚠️ Prorated Rent Mismatch"
                except Exception:
                    df.at[index, "expected_prorated_rent"] = "Error"
        
        results.append((file_name, df))
    
    return results

# Streamlit Web App UI
st.title("Charge Breakdown Audit Bot - Fully Integrated Mode")
st.write("Upload charge breakdown reports along with the Move-In/Move-Out report for a full audit.")

# Multiple file uploader for charge breakdowns
charge_uploaded_files = st.file_uploader("Upload Charge Breakdown Reports (Excel)", type=["xls", "xlsx"], accept_multiple_files=True)

# Single file uploader for Move-In/Move-Out report
move_in_out_uploaded_file = st.file_uploader("Upload Move-In/Move-Out Report (Excel)", type=["xls", "xlsx"], accept_multiple_files=False)

if charge_uploaded_files and move_in_out_uploaded_file:
    st.write("Processing files...")
    processed_data = process_charge_report(charge_uploaded_files, move_in_out_uploaded_file)
    
    for file_name, df in processed_data:
        st.write(f"Audit Results for: {file_name}")
        st.dataframe(df)  # Display processed data
        
        # Download button for audit results
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(f"Download Audit Report for {file_name}", data=csv, file_name=f"{file_name}_audit.csv", mime="text/csv")
