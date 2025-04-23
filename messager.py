from whatsapp_api_client_python import API
import constants


greenAPI = API.GreenApi(constants.ACCOUNT_ID, constants.TOKEN_INSTANCE)


class SendingError(Exception):
    pass


def send_messages(counter: int):
    # send_media("Test.png")

    send_media(f"{counter+2}.jpg")
    print("Daily Page Sent")

    send_media(f"{counter}.png")
    print("Translation Sent")

    send_media(f"{counter}.mp3")
    print("Audio Sent")


def send_media(filename: str):
    response = greenAPI.sending.sendFileByUpload(constants.MAIN_GROUP_ID, filename)
    # response = greenAPI.sending.sendFileByUpload(constants.TEST_GROUP_ID, filename)
    # response = greenAPI.sending.sendFileByUpload(constants.MY_NUM, filename)

    if response.code != 200:
        raise SendingError(
            f"Failed to send. Error code: {response.code}. More info here: {response.error}"
        )


def send_text_message(text: str):
    msg_response = greenAPI.sending.sendMessage(constants.TEST_GROUP_ID, f"{text}")

    if msg_response.code != 200:
        print(msg_response.error)
