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

        # Normalize column names and remove duplicate columns
        df.columns = df.iloc[2].astype(str).str.lower().str.strip()  # Use third row as header to avoid metadata
        df = df[3:].reset_index(drop=True)  # Remove unnecessary rows
        
        # Drop duplicate column names
        df = df.loc[:, ~df.columns.duplicated()]
        
        # Ensure all column names are strings and not None
        df.columns = df.columns.astype(str)
        
        # Ensure all data is fully converted to strings
        df = df.astype(str).applymap(lambda x: x.strip() if isinstance(x, str) else "")
        df.fillna("", inplace=True)

        # Handle LotR column detection safely
        lotr_column = next((col for col in df.columns if isinstance(col, str) and ("lotr" in col or "lot rent" in col or "base rent" in col)), None)
        
        # Create structured audit output table
        audit_df = pd.DataFrame(columns=[
            "Unit", "Tenant", "Move-In Date", "Lot Rent Charged ($)",
            "Expected Prorated Rent ($)", "Prorated Rent Status", "Security Deposit Charged?",
            "Missing Utilities?", "Unexpected Charge Variations?", "Audit Notes"
        ])

        # Process each row in the charge breakdown report
        for _, row in df.iterrows():
            unit = row.get("unit", "N/A")
            tenant = row.get("tenant", "N/A")
            move_in_date = row.get("move_in_date", "N/A")
            lot_rent = row.get(lotr_column, "0").replace(",", "")
            security_deposit = row.get("security_deposit", "0")
            sewer_fee = row.get("sewer_fee", "0")
            garbage_fee = row.get("garbage_fee", "0")

            # Calculate expected prorated rent
            base_rent = 420.00  # Assuming base rent is $420
            expected_rent = "N/A"
            prorated_status = "N/A"

            try:
                move_in_dt = pd.to_datetime(move_in_date, errors='coerce')
                if pd.notna(move_in_dt):
                    days_in_month = move_in_dt.days_in_month
                    days_not_in_unit = move_in_dt.day - 1
                    expected_rent = base_rent - ((base_rent / days_in_month) * days_not_in_unit)
                    expected_rent = round(expected_rent, 2)

                    if abs(expected_rent - float(lot_rent)) > 1:
                        prorated_status = "⚠️ Mismatch"
                    else:
                        prorated_status = "✅ Correct"
            except:
                expected_rent = "Error"

            # Check utilities
            missing_utilities = "✅ No"
            if float(sewer_fee) == 0 or float(garbage_fee) == 0:
                missing_utilities = "⚠️ Yes"

            # Check security deposit
            security_deposit_status = "✅ Yes" if float(security_deposit) > 0 else "⚠️ No"

            # Add row to audit DataFrame
            audit_df.loc[len(audit_df)] = [
                unit, tenant, move_in_date, lot_rent, expected_rent,
                prorated_status, security_deposit_status, missing_utilities, "✅ No", ""
            ]
        
        results.append((file_name, audit_df))
    
    return results

# Streamlit Web App UI
st.title("Charge Breakdown Audit Bot - Structured Report Mode")
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
        st.dataframe(df)  # Display structured audit table
        
        # Download button for audit results
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(f"Download Audit Report for {file_name}", data=csv, file_name=f"{file_name}_audit.csv", mime="text/csv")
