from googleapiclient.discovery import build

from authentication import authenticate

SPREADSHEET_ID = "1V6E0JlEYoX02C_CxGwQIBtfApnub-tvMaCfWldXYloI"
SHEET_NAME = "Applications"


def get_sheets_service():
    creds = authenticate()

    return build(
        "sheets",
        "v4",
        credentials=creds
    )


def get_all_rows():
    """
    Returns all rows in the sheet.

    Returns:
        list[list[str]]

    Example:
        [
            ["id", "name", "status"],
            ["123", "John", "pending"],
            ["456", "Jane", "complete"]
        ]
    """

    service = get_sheets_service()

    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:Z"
    ).execute()

    return result.get("values", [])


def write_row(row_number, values):
    """
    Writes values to a specific row.

    Args:
        row_number: 1-based row number in Google Sheets
        values: list of values

    Example:
        write_row(
            5,
            ["123", "John", "complete"]
        )
    """

    service = get_sheets_service()

    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A{row_number}",
        valueInputOption="RAW",
        body={
            "values": [values]
        }
    ).execute()


def append_row(values):
    """
    Appends a new row to the bottom of the sheet.

    Example:
        append_row(
            ["123", "John", "pending"]
        )
    """

    service = get_sheets_service()

    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:Z",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={
            "values": [values]
        }
    ).execute()


def update_row_by_id(row_id, values):
    """
    Finds a row using the ID in column A and updates that row.

    Args:
        row_id: ID stored in column A
        values: complete row of values

    Example:
        update_row_by_id(
            "abc123",
            ["abc123", "John", "complete"]
        )

    Returns:
        True if the row was found and updated.
        False if the ID was not found.
    """

    rows = get_all_rows()

    # Google Sheets rows are 1-based.
    for row_number, row in enumerate(rows, start=1):

        if not row:
            continue

        # First column is the ID
        current_id = str(row[0])

        if current_id == str(row_id):

            write_row(
                row_number,
                values
            )

            return True

    return False