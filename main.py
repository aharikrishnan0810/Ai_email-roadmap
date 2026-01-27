import os
import base64
import google.generativeai as genai
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email import message_from_bytes

# ------------------- Load Gemini API -------------------
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "models/gemini-flash-latest"
model = genai.GenerativeModel(MODEL_NAME)
print(f"Using model: {MODEL_NAME}")

# ------------------- Gmail API Setup -------------------
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('gmail', 'v1', credentials=creds)
    return service

def fetch_emails(service, from_email=None, label_ids=['INBOX'], max_results=5):
    """
    Fetch latest emails from Gmail. Optionally filter by sender email.
    """
    results = service.users().messages().list(userId='me', labelIds=label_ids, maxResults=max_results).execute()
    messages = results.get('messages', [])
    emails = []

    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='raw').execute()
        raw_data = base64.urlsafe_b64decode(msg_data['raw'])
        mime_msg = message_from_bytes(raw_data)
        subject = mime_msg['subject']
        sender = mime_msg['From']

        # Filter by sender if provided
        if from_email and from_email.lower() not in sender.lower():
            continue

        # Get plain text content
        if mime_msg.is_multipart():
            for part in mime_msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
            else:
                body = ""
        else:
            body = mime_msg.get_payload(decode=True).decode()

        emails.append({"subject": subject, "from": sender, "body": body})

    return emails


# ------------------- Gemini Extractor -------------------
def extract_information(email_text: str) -> str:
    prompt = f"""
You are an intelligent information extraction system.

Carefully read the email content below and extract ALL important and relevant information.
Rewrite the extracted information as ONE clear, professional paragraph.

Rules:
- Do not use bullet points
- Do not use JSON
- Do not omit any important details
- Maintain logical flow
- Ignore signatures and disclaimers

EMAIL CONTENT:
{email_text}
"""
    response = model.generate_content(prompt)
    return response.text.strip()

# ------------------- Main Execution -------------------
if __name__ == "__main__":
    service = get_gmail_service()

    # Fetch emails ONLY from this sender
    emails = fetch_emails(service, from_email="aharikrishnan0810gdc@gmail.com", max_results=10)

    if not emails:
        print("No emails found from aharikrishnan0810gdc@gmail.com")
    else:
        for i, e in enumerate(emails, start=1):
            print(f"\n================ Email {i}: {e['subject']} ================\n")
            summary = extract_information(e["body"])
            print(summary)

