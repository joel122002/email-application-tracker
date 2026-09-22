import base64
from bs4 import BeautifulSoup
from googleapiclient.discovery import build

from authentication import authenticate


def decode_body(data):
    """Decode Gmail's base64url encoded body."""

    if not data:
        return ""

    decoded = base64.urlsafe_b64decode(data + "===")

    return decoded.decode("utf-8", errors="replace")


def extract_plaintext_body(payload):
    """
    Extract the best available plaintext body from a Gmail message.

    Priority:
        1. text/plain
        2. text/html converted to plaintext
    """

    mime_type = payload.get("mimeType", "")

    # Simple text/plain email
    if mime_type == "text/plain":
        body_data = payload.get("body", {}).get("data")

        if body_data:
            return decode_body(body_data)

    # Simple HTML email
    if mime_type == "text/html":
        body_data = payload.get("body", {}).get("data")

        if body_data:
            html = decode_body(body_data)
            return BeautifulSoup(html, "html.parser").get_text(
                separator="\n"
            )

    # Multipart email
    parts = payload.get("parts", [])

    # First look specifically for text/plain
    for part in parts:
        if part.get("mimeType") == "text/plain":
            body_data = part.get("body", {}).get("data")

            if body_data:
                return decode_body(body_data)

    # If no text/plain exists, look for HTML
    for part in parts:
        if part.get("mimeType") == "text/html":
            body_data = part.get("body", {}).get("data")

            if body_data:
                html = decode_body(body_data)

                return BeautifulSoup(
                    html,
                    "html.parser"
                ).get_text(separator="\n")

    # Recursively search nested multipart sections
    for part in parts:
        if "parts" in part:
            body = extract_plaintext_body(part)

            if body:
                return body

    return ""


def get_last_n_emails(n):
    creds = authenticate()

    service = build(
        "gmail",
        "v1",
        credentials=creds
    )

    # Get latest n messages in Inbox
    result = service.users().messages().list(
        userId="me",
        labelIds=["INBOX"],
        maxResults=n
    ).execute()

    messages = result.get("messages", [])

    emails = []

    for message in messages:

        # Get complete email
        email = service.users().messages().get(
            userId="me",
            id=message["id"],
            format="full"
        ).execute()

        # Extract headers
        headers = email["payload"].get("headers", [])

        from_email = ""
        date = ""
        subject = ""

        for header in headers:
            name = header["name"].lower()

            if name == "from":
                from_email = header["value"]

            elif name == "date":
                date = header["value"]

            elif name == "subject":
                subject = header["value"]

        # Extract body
        plaintext_body = extract_plaintext_body(
            email["payload"]
        )

        emails.append({
            "From": from_email,
            "Date": date,
            "Subject": subject,
            "ID": email["id"],
            "Body": plaintext_body
        })

    return emails