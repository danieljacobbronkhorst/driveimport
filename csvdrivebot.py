from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
import pandas as pd
from googleapiclient.http import MediaIoBaseDownload
import os
import glob
import json

# ----------------------------
# LOCAL SAVE CONFIG
# ----------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_FOLDER = os.path.join(SCRIPT_DIR, "Download")
os.makedirs(LOCAL_FOLDER, exist_ok=True)
LOCAL_FILE_NAME = "export_attendance.csv"
LOCAL_FILE_PATH = os.path.join(LOCAL_FOLDER, LOCAL_FILE_NAME)

# ----------------------------
# CONFIG
# ----------------------------
FOLDER_ID = '1Oi_udzlWD1fEx7U5_kdu2kJZfkRrXsMK'
FILE_PREFIX = 'export_'

# ----------------------------
# AUTHENTICATION
# ----------------------------
#SERVICE_ACCOUNT_FILE = os.path.join(SCRIPT_DIR, 'service_account.json')
#SCOPES = ['https://www.googleapis.com/auth/drive']
#credentials = service_account.Credentials.from_service_account_file(
#    SERVICE_ACCOUNT_FILE, scopes=SCOPES
#)
#drive_service = build('drive', 'v3', credentials=credentials)

SCOPES = ['https://www.googleapis.com/auth/drive']

# Read JSON from GitHub Secret
creds_json = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
creds_dict = json.loads(creds_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)



# ----------------------------
# GET ALL FILES IN FOLDER
# ----------------------------
query = f"'{FOLDER_ID}' in parents and name contains '{FILE_PREFIX}' and mimeType='text/csv'"
results = drive_service.files().list(
    q=query,
    fields="files(id, name, modifiedTime)"
).execute()
files = results.get('files', [])

if not files:
    print("❌ No CSV files found.")
    exit()

# ----------------------------
# SPLIT INTO PROCESSED AND UNPROCESSED
# ----------------------------
processed_files = [f for f in files if '__processed' in f['name']]
unprocessed_files = [f for f in files if '__processed' not in f['name']]

# Find latest processed file timestamp
latest_processed_time = max([f['modifiedTime'] for f in processed_files], default=None)

# Filter unprocessed files newer than latest processed
if latest_processed_time:
    candidate_files = [
        f for f in unprocessed_files if f['modifiedTime'] > latest_processed_time
    ]
else:
    candidate_files = unprocessed_files

if not candidate_files:
    print("✅ No new files to process.")
    exit()

# Pick the most recently modified file
today_file = max(candidate_files, key=lambda x: x['modifiedTime'])
file_id = today_file['id']
file_name = today_file['name']
print(f"✅ Selected file: {file_name} (ID: {file_id})")

# ----------------------------
# DOWNLOAD CSV
# ----------------------------
request = drive_service.files().get_media(fileId=file_id)
fh = io.BytesIO()
downloader = MediaIoBaseDownload(fh, request)

done = False
while not done:
    status, done = downloader.next_chunk()
    print(f"Download {int(status.progress() * 100)}%.")

fh.seek(0)
df = pd.read_csv(fh)
print("✅ CSV loaded successfully.")
print(df.head())

# ----------------------------
# CLEAR THE DOWNLOAD FOLDER
# ----------------------------
for f in glob.glob(os.path.join(LOCAL_FOLDER, '*')):
    os.remove(f)
print(f"🗑 Cleared {len(glob.glob(os.path.join(LOCAL_FOLDER, '*')))} file(s) from the download folder.")

# ----------------------------
# SAVE CSV LOCALLY
# ----------------------------
df.to_csv(LOCAL_FILE_PATH, index=False)
print(f"✅ CSV saved locally as: {LOCAL_FILE_PATH}")

# ----------------------------
# RENAME FILE TO MARK AS PROCESSED
# ----------------------------
new_name = file_name + "__processed"
drive_service.files().update(fileId=file_id, body={'name': new_name}).execute()
print(f"✅ Renamed file on Google Drive to: {new_name}")
