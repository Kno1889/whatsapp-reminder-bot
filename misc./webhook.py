import json
from datetime import datetime
import constants

from whatsapp_api_client_python import API

green_API = API.GreenApi(constants.ACCOUNT_ID, constants.TOKEN_INSTANCE)


def main():
    green_API.webhooks.startReceivingNotifications(onEvent)


def onEvent(typeWebhook, body):
    if typeWebhook == "incomingMessageReceived":
        onIncomingMessageReceived(body)


def onIncomingMessageReceived(body):
    idMessage = body["idMessage"]
    eventDate = datetime.fromtimestamp(body["timestamp"])
    senderData = body["senderData"]
    messageData = body["messageData"]
    print(body)
    print(
        idMessage
        + ": "
        + "At "
        + str(eventDate)
        + " Incoming from "
        + json.dumps(senderData, ensure_ascii=False)
        + " message = "
        + json.dumps(messageData, ensure_ascii=False)
    )


# main()

class Exception1(Exception):
    pass

class Exception2(Exception):
    pass


def test():
    #  print(((23 * 60) + 57) * 60)
    try:
        foo1()
        foo2()
    except Exception1 as e:
        print(e)
    except Exception2 as e:
        print(e)

    return 0


def foo1():
    x = 11

    if x < 0:
        raise Exception1("Negative Number")

    return 0

def foo2():
    x = 1

    if x > 0:
        raise Exception2("Positive Number")

    return 0

test()


# 2023-09-11 22:48:02.441375
# INFO:oauth2client.client:access_token is expired. Now: 2023-09-12 02:48:02.442549, token_expiry: 2023-08-31 05:30:09
# INFO:oauth2client.client:Refreshing access_token
# INFO:oauth2client.client:Failed to retrieve access token: {
#   "error": "invalid_grant",
#   "error_description": "Token has been expired or revoked."
# }