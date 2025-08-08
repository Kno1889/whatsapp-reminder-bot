from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import constants
import os

class AuthenticationError(Exception):
    pass


def download_files(page_num: int):
    try:
        drive = authenticate()
    except:
        # TODO: Automate deleting?
        raise AuthenticationError("Please re-auth, delete creds.json")
    
    pages_file_list = get_file_list(constants.PAGES_FOLDER_ID, drive)
    audio_file_list = get_file_list(constants.AUDIO_FOLDER_ID, drive)
    translations_file_list = get_file_list(constants.TRANSLATIONS_FOLDER_ID, drive)

    page_file = f"{page_num}.jpg"
    audio_file = f"{page_num}.mp3"
    translation_file = f"{page_num}.jpeg"

    download_file(page_file, pages_file_list)
    download_file(audio_file, audio_file_list)
    # download_file(translation_file, translations_file_list)

def delete_files(page_num: int):
    for ext in ["jpg", "mp3", "jpeg"]:
        filename = f"{page_num}.{ext}"
        if os.path.exists(filename):
            os.remove(filename)
            print(f"{filename} deleted sucessfully")

    
def authenticate():
    gauth = GoogleAuth()

    # Try to load saved client credentials
    gauth.LoadCredentialsFile("creds.json")
    if gauth.credentials is None:
        # Authenticate if they're not there
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        # Refresh them if expired
        gauth.Refresh()
    else:
        # Initialize the saved creds
        gauth.Authorize()
    # Save the current credentials to a file
    gauth.SaveCredentialsFile("creds.json")

    return GoogleDrive(gauth)


def get_file_list(folder_id: str, drive: GoogleDrive):
    file_list = drive.ListFile(
        {"q": f"'{folder_id}' in parents and trashed=false"}
    ).GetList()
    return file_list


def download_file(file_name: str, file_list):
    for file in file_list: # TODO: better approach here?
        if file_name == file["title"]:
            file.GetContentFile(file_name)
            print(f"File {file_name} has been saved locally")
            return
    #TODO: Send msg alert that file is missing
    
