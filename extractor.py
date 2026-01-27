import os
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email import message_from_bytes
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import psycopg2
# ------------------- Gmail API Setup -------------------
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

load_dotenv()

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
EMAIL_FILTER = os.getenv("EMAIL_FILTER")
MAX_EMAILS = int(os.getenv("MAX_EMAILS", 10))



def create_table_if_not_exists():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id SERIAL PRIMARY KEY,
            gmail_id TEXT UNIQUE,
            sender TEXT,
            subject TEXT,
            body TEXT,
            category VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()
    print("Table emails created successfully")


def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            SCOPES
        )
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

# ------------------- Fetch Emails -------------------
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

# ------------------- Email Classification -------------------
def classify_email(subject, body):
    text = f"{subject} {body}".lower()

    # -------- STRONG PLACEMENT INDICATORS --------
    strong_keywords = [
        "job role", "job opportunity", "drive", "campus drive",
        "interview", "shortlisted", "selection process",
        "offer letter", "ctc", "package", "salary",
        "joining", "recruitment", "hiring",
        "registration link", "apply", "eligibility criteria",
        "online test", "technical round", "hr round"
    ]

    # -------- WEAK INDICATORS (NOT ENOUGH ALONE) --------
    weak_keywords = [
        "placement coordinator",
        "placement cell",
        "training and placement",
        "tpo",
        "career guidance"
    ]

    # -------- NEGATIVE / NON-PLACEMENT INDICATORS --------
    non_placement_keywords = [
        "meeting", "circular", "notice", "holiday",
        "exam", "assignment", "attendance",
        "seminar", "workshop", "fee",
        "internal assessment", "class schedule"
    ]

    # 1️⃣ If strong placement keywords found → Placement
    for word in strong_keywords:
        if word in text:
            return "Placement"

    # 2️⃣ If weak keyword exists, check context
    if any(w in text for w in weak_keywords):
        # Only placement if job-related context exists
        context_keywords = [
            "company", "drive", "interview", "apply",
            "registration", "job", "role"
        ]
        for ctx in context_keywords:
            if ctx in text:
                return "Placement"
        return "Other"

    # 3️⃣ If clearly non-placement → Other
    for word in non_placement_keywords:
        if word in text:
            return "Other"

    return "Other"

# ------------------- PostgreSQL DB -------------------
def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )


def insert_email(gmail_id, sender, subject, body, category):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO emails (gmail_id, sender, subject, body, category)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (gmail_id) DO NOTHING
        """,
        (gmail_id, sender, subject, body, category)
    )

    if cursor.rowcount == 0:
        print(f"Duplicate email skipped: {subject}")
    else:
        print(f"Email stored: {subject}")

    conn.commit()
    cursor.close()
    conn.close()



# ------------------- Main Execution -------------------
if __name__ == "__main__":
    create_table_if_not_exists()
    service = get_gmail_service()

    emails = fetch_emails(
        service,
        from_email=EMAIL_FILTER,
        max_results=MAX_EMAILS
    )

    if not emails:
        print("No emails found from given sender")
    else:
        for i, e in enumerate(emails, start=1):
            category = classify_email(e["subject"], e["body"])

            
            insert_email(
    e["gmail_id"],
    e["from"],
    e["subject"],
    e["body"],
    category
)


            print(f"\n========== EMAIL {i} ==========")
            print("From:", e["from"])
            print("Subject:", e["subject"])
            print("Category:", category)
            print("\nCONTENT:\n")
            print(e["body"])
