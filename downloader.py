from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import constants

class AuthenticationError(Exception):
    pass


def download_files(counter: int):
    try:
        drive = authenticate()
    except:
        raise AuthenticationError
    
    file_list = get_file_list(constants.DAILY_QURAN_FOLDER_ID, drive)

    image_filename = f"{counter+2}.jpg"
    translation_filename = f"{counter}.png"
    recording_filename = f"{counter}.mp3"

    try:
        download_file(image_filename, file_list)
        download_file(translation_filename, file_list)
        download_file(recording_filename, file_list)
    except:
        raise FileNotFoundError

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

    # for file in file_list:
    #     print("title: {}, id: {}".format(file["title"], file["id"]))

    return file_list


def download_file(file_name: str, file_list):

    for file in file_list:
        if file_name == file["title"]:
            file.GetContentFile(file_name)

            print(f"File {file_name} has been saved locally")
