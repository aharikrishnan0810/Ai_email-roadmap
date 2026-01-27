import os
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email import message_from_bytes
from bs4 import BeautifulSoup

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def get_gmail_service():
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES
        )
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def fetch_emails(service, from_email=None, label_ids=['INBOX'], max_results=5):
    results = service.users().messages().list(
        userId='me',
        labelIds=label_ids,
        maxResults=max_results
    ).execute()

    messages = results.get('messages', [])
    emails = []

    for msg in messages:
        msg_data = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='raw'
        ).execute()

        raw_data = base64.urlsafe_b64decode(msg_data['raw'])
        mime_msg = message_from_bytes(raw_data)

        subject = mime_msg.get('Subject', '')
        sender = mime_msg.get('From', '')

        if from_email and from_email.lower() not in sender.lower():
            continue

        body = ""

        for part in mime_msg.walk():
            content_type = part.get_content_type()
            payload = part.get_payload(decode=True)

            if not payload:
                continue

            text = payload.decode(errors="ignore")

            if content_type == "text/plain":
                body = text
                break

            if content_type == "text/html" and not body:
                body = BeautifulSoup(text, "html.parser").get_text()

        emails.append({
            "gmail_id": msg["id"],
            "subject": subject,
            "from": sender,
            "body": body.strip()
        })

    return emails


