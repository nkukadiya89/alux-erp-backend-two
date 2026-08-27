# Customer Bulk Import Test Data

This folder contains test data files for Customer Master bulk import functionality.

## Files

### `customer_valid.csv`
Contains **10 valid customer records** with complete data including:
- All Customer fields (basic info, addresses, business details)
- Single Contact Person per customer
- Single Banking Details per customer
- Proper foreign key references by name (Customer Type, Sales Executive)

### `customers_with_errors.csv`
Contains **10 records with intentional errors** for testing error handling:
- Missing required fields
- Duplicate customer names
- Invalid field lengths
- Invalid foreign key references
- Invalid business/company type values
- Invalid data types

## CSV Format

### Required Columns
- **Customer Name** (required, unique)
- **Person Name** (required)
- **Phone Number** (required)
- **Business Type** (required: INDIAN or OVERSEAS)

### Optional Columns
- Customer Number (auto-generated if not provided)
- Email, Designation
- GSTIN Number, PAN Number, GST Type (for INDIAN business type)
- Import Export Code, Beneficiary Agent Code (for OVERSEAS business type)
- Customer Type (name of CustomerType, not ID)
- Sales Executive (username, not ID)
- Sales Executive Assistant (username, not ID)
- All address fields (office and factory)
- Credit Limit, Due Days, Delivery Days
- Company Type (customer/vendor/customer_vendor)
- Customer Section No, Licence No, Note
- Is Company Visible On Documents (true/false/1/0/yes/no)

### Related Data Columns (Single Record Per Customer)
- **Contact Person Name**
- **Contact Person Designation**
- **Contact Person Mobile Number**
- **Contact Person Email**
- **Bank Name**
- **Bank Account Number**
- **Bank IFSC Code**
- **Bank Branch Address**
- **Beneficiary Swift Code** (optional)
- **Bank AD Code**

## What to Write in CSV: Customer Type, Sales Executive, Sales Executive Assistant

Use these column names in your CSV: **Customer Type**, **Sales Executive**, **Sales Executive Assistant**.

### Customer Type
- **Write:** The **name** of the customer type (as stored in Customer Type master).
- **Lookup:** Case-insensitive; exact match first, then contains.
- **Examples:** `Corporate Customer`, `Export Customer`, `Nbabcdd`
- **Leave empty** to leave the field blank (no customer type).

### Sales Executive
- **Write any one of:**
  - **Username** (e.g. `admin`, `sales_manager`)
  - **Full name** (e.g. `Shivam Varu`, `Raj Chitroda`)
  - **First name only** (e.g. `Shivam`)
  - **Email** (e.g. `admin@example.com`) if the value contains `@`
- **Lookup:** Case-insensitive. Tried in order: username → full name → first name → email.
- **Leave empty** to leave the field blank.

### Sales Executive Assistant
- **Write any one of:** Same as Sales Executive (username, full name, first name, or email).
- **Examples:** `Raj Chitroda`, `admin`, `sales_assistant`
- **Leave empty** to leave the field blank.

**Summary for CSV:**

| Column name               | What to write                          | Example        |
|---------------------------|----------------------------------------|----------------|
| Customer Type             | CustomerType name                      | Corporate Customer |
| Sales Executive           | Username, or full name, or first name, or email | Shivam Varu or admin |
| Sales Executive Assistant | Same as Sales Executive                | Raj Chitroda or admin |

## Foreign Key References (legacy note)

All foreign key fields accept **names/usernames** instead of IDs:

1. **Customer Type**: Use CustomerType `name` (case-insensitive)
2. **Sales Executive**: Use User username, full name, first name, or email (case-insensitive)
3. **Sales Executive Assistant**: Same as Sales Executive

## Business Rules

### Business Type Validation
- **INDIAN**: Requires GSTIN, PAN, GST Type, Udyam No, Applicable GST
- **OVERSEAS**: Requires Import Export Code, Beneficiary Agent Code
- Fields from opposite type are automatically set to null

### Company Type Validation
- **vendor**: Customer Section No, Customer Type, Sales Executive, Sales Executive Assistant, Delivery Days are set to null
- **customer** or **customer_vendor**: All fields allowed

## Testing Workflow

1. **Test Valid Import**:
   - Use `customer_valid.csv`
   - Expected: 10 customers created with contact persons and banking details
   - Check import logs for success

2. **Test Error Handling**:
   - Use `customers_with_errors.csv`
   - Expected: All records should fail with appropriate error messages
   - Check import errors endpoint for detailed error information
   - Download error report CSV

3. **Test Dry Run**:
   - Use `customer_valid.csv` with `dry_run=true`
   - Expected: Validation only, no database changes
   - Check import log shows dry_run status

## Sample Data Structure

Each row in `customer_valid.csv` represents:
- One Customer record
- One ContactPerson record (if Contact Person Mobile Number provided)
- One BankingDetails record (if Bank Account Number provided)

## Notes

- Customer Number is auto-generated if not provided (format: CUST{CODE}{RANDOM})
- All foreign key lookups are case-insensitive
- Related data (ContactPerson, BankingDetails) is created only if required fields are provided
- Business type and company type validations are automatically applied
- Duplicate customer names are prevented
- Duplicate customer numbers are prevented

## Troubleshooting

### Common Issues

1. **Customer Type not found**:
   - Ensure CustomerType exists with matching name
   - Check case sensitivity (lookup is case-insensitive)

2. **User not found**:
   - Ensure User exists with matching username
   - Check username spelling

3. **Duplicate customer name**:
   - Customer names must be unique
   - Check existing customers before import

4. **Invalid business type fields**:
   - INDIAN customers cannot have Import Export Code
   - OVERSEAS customers cannot have GSTIN/PAN

5. **Invalid company type fields**:
   - Vendor customers cannot have Customer Section No, Customer Type, Sales Executive, etc.

