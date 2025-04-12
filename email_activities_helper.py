import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from datetime import datetime, timezone
import time

# Define the required scopes for Gmail API
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

def authenticate():
    """Authenticate and return Gmail API service."""
    creds = None

    # Load credentials from token.json if it exists
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # Refresh or authenticate if credentials are invalid
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("Authentication failed! Run `auth.py` first.")
            return None

    # Build the Gmail service
    service = build('gmail', 'v1', credentials=creds)
    return service

def send_email(service, to_email, subject, message_text):
    """Send an email using Gmail API."""
    try:
        # Create MIME message
        msg = MIMEMultipart()
        msg['to'] = to_email
        msg['subject'] = subject
        msg.attach(MIMEText(message_text, 'plain'))

        # Encode message in base64
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        # Send email using Gmail API
        message = {'raw': raw_message}
        sent_message = service.users().messages().send(userId='me', body=message).execute()

        return f"✅ Email sent successfully to {to_email}! Message ID: {sent_message['id']}"
    
    except Exception as e:
        return f"❌ Error sending email: {e}"

def was_email_sent(service, to_email, subject_filter):
    """
    Verifies whether an email with a specific subject and recipient was sent
    in the current or previous minute.

    Args:
        service: Authenticated Gmail API service.
        to_email (str): Recipient email address to search for.
        subject_filter (str): Subject string to filter sent messages.

    Returns:
        str: Verification result message.
    """
    try:
        # Build Gmail query
        query_parts = []
        if subject_filter:
            query_parts.append(f'subject:"{subject_filter}"')
        if to_email:
            query_parts.append(f'to:{to_email}')
        query = ' '.join(query_parts)

        # Search 'SENT' messages with query
        results = service.users().messages().list(userId='me', labelIds=['SENT'], q=query, maxResults=5).execute()
        messages = results.get('messages', [])

        if not messages:
            return f"❌ No sent emails found matching To: {to_email}, Subject: {subject_filter}"

        now = datetime.now(timezone.utc)
        current_minute = now.replace(second=0, microsecond=0)
        previous_minute = current_minute.timestamp() - 60  # one minute ago (in seconds)

        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()

            internal_date_ms = int(msg_data.get('internalDate', 0))
            sent_time = datetime.fromtimestamp(internal_date_ms / 1000, tz=timezone.utc)
            sent_timestamp = sent_time.timestamp()

            if previous_minute <= sent_timestamp <= now.timestamp():
                return f"✅ Email was sent successfully at {sent_time.strftime('%Y-%m-%d %H:%M:%S')} UTC."

        return f"❌ No emails were sent in the current or previous minute."

    except Exception as e:
        return f"❌ Error verifying sent email: {e}"