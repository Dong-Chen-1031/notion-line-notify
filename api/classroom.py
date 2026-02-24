import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from linex.log import logger

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.announcements",
]


def login(
    token_path: str = "token.json", credentials_path: str = "credentials.json"
) -> None:
    """
    login to Google Classroom and save the credentials to token.json for future use.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_path, "w") as token:
            token.write(creds.to_json())


def send_announcement(
    text: str, courseId: int = 825932668195, token_path: str = "token.json"
) -> None:
    """
    Sends an announcement to the specified course.
    """
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    else:
        raise Exception("No credentials found. Please run the login function first.")
    try:
        service = build("classroom", "v1", credentials=creds)

        # Call the Classroom API
        results = (
            service.courses()
            .announcements()
            .create(courseId=courseId, body={"text": text})
        )
        return results.execute()
        # op(results.execute())

    except HttpError as error:
        logger.log(f"An error occurred: {error}")


def list_courses(pageSize: int = 10, token_path: str = "token.json"):
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    else:
        raise Exception("No credentials found. Please run the login function first.")
    try:
        service = build("classroom", "v1", credentials=creds)

        # Call the Classroom API
        results = service.courses().list(pageSize=pageSize).execute()
        courses = results.get("courses", [])

        if not courses:
            print("No courses found.")
            return
        print("Courses:")
        for course in courses:
            print(course["name"])

    except HttpError as error:
        logger.log(f"An error occurred: {error}")


if __name__ == "__main__":
    login()
