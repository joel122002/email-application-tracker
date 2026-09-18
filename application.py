from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional

from sheets import (
    get_all_rows,
    append_row,
    update_row_by_id,
)


class Status(str, Enum):
    APPLIED = "applied"
    REJECTED = "rejected"
    PROCEEDED = "proceeded"


@dataclass
class Application:
    id: str
    date: str
    company_name: str
    role_name: str
    status: Status


def _row_to_application(row: list[str]) -> Optional[Application]:
    """
    Converts a Google Sheets row into an Application object.

    Expected columns:
        ID
        Date
        Company Name
        Role Name
        Status
    """

    if len(row) < 5:
        return None

    try:
        return Application(
            id=str(row[0]),
            date=str(row[1]),
            company_name=str(row[2]),
            role_name=str(row[3]),
            status=Status(str(row[4]).lower()),
        )
    except ValueError:
        # Invalid status in the sheet
        return None


def _application_to_row(application: Application) -> list[str]:
    """
    Converts an Application object into a Google Sheets row.
    """

    return [
        application.id,
        application.date,
        application.company_name,
        application.role_name,
        application.status.value,
    ]


def update_status_by_id(
    application_id: str,
    status: Status,
) -> bool:
    """
    Updates the status of an application using its ID.

    Returns:
        True if the application was found and updated.
        False if the ID was not found.

    Example:
        update_status_by_id(
            "abc123",
            Status.REJECTED
        )
    """

    rows = get_all_rows()

    for row in rows:
        application = _row_to_application(row)

        if application is None:
            continue

        if application.id == str(application_id):

            application.status = status

            return update_row_by_id(
                application_id,
                _application_to_row(application)
            )

    return False


def create_application(
    application_id: str,
    application_date: str,
    company_name: str,
    role_name: str,
    status: Status = Status.APPLIED,
) -> None:
    """
    Creates a new application row.

    Example:
        create_application(
            application_id="abc123",
            application_date="2026-09-17",
            company_name="Google",
            role_name="Software Engineer",
        )
    """

    application = Application(
        id=str(application_id),
        date=application_date,
        company_name=company_name,
        role_name=role_name,
        status=status,
    )

    append_row(
        _application_to_row(application)
    )


def get_last_matching_application_id(
    company_name: str,
    role_name: str,
) -> Optional[str]:
    """
    Finds the ID of the last matching application.

    Matching rules:

    1. First, look for rows where both company and role match.
       If multiple exist, return the ID of the LAST one.

    2. If no exact company + role match exists, look for rows
       belonging to the same company with status == applied.

       Among those:
         - Prefer rows with no role name.
         - If multiple have no role name, return the LAST one.
         - Otherwise return the LAST applied row for the company.

    3. Return None if nothing matches.

    Example:
        get_last_matching_application_id(
            "Google",
            "Software Engineer"
        )
    """

    rows = get_all_rows()

    exact_matches = []
    applied_company_matches = []
    applied_company_without_role = []

    for row in rows:
        application = _row_to_application(row)

        if application is None:
            continue

        same_company = (
            application.company_name.strip().lower()
            == company_name.strip().lower()
        )

        same_role = (
            application.role_name.strip().lower()
            == role_name.strip().lower()
        )

        # Exact company + role match
        if same_company and same_role:
            exact_matches.append(application)

        # Fallback: same company + applied
        if same_company and application.status == Status.APPLIED:
            applied_company_matches.append(application)

            # No role name
            if not application.role_name.strip():
                applied_company_without_role.append(application)

    # Rule 1:
    # Exact matches -> return the last one
    if exact_matches:
        return exact_matches[-1].id

    # Rule 2:
    # Prefer the last same-company applied row with no role
    if applied_company_without_role:
        return applied_company_without_role[-1].id

    # Otherwise return the last same-company applied row
    if applied_company_matches:
        return applied_company_matches[-1].id

    return None