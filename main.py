import downloader
import messager
import os
from datetime import datetime
import time


# TODO setup settings.yaml
# TODO setup highlighter
# # TODO friday message + poll reminder
# Salam everyone, a reminder to read surat Al-Kahf as today is Friday and rewards of reading surat Al-Kahf on Friday include:
# - Your sins are forgiven between the two Fridays (the one you read it one and the following one)
# - A light is emitted from beneath your feet to the clouds of the sky, which shines for you on the Day of Resurrection
# - And more
# Here's a recording of surat Al-Kahf, please make sure to read it, it is on page 293 in the Quran.
def main():
    daily_counter = 113

    while daily_counter <= 604:
        now = datetime.now()
        print(now)

        if now.hour == 8 and now.minute == 0:
            # now..strftime("%A")
            try:
                # download daily pages and recording
                downloader.download_files(daily_counter)
                print("\n")
                # send to whatsapp group
                messager.send_messages(daily_counter)
                print("\n")
                # delete pages, recording from local storage
                os.remove(f"{daily_counter+2}.jpg")
                os.remove(f"{daily_counter}.mp3")
                os.remove(f"{daily_counter}.png")

                messager.send_text_message(
                    f"Sent messages for day number {daily_counter}"
                )
                print(f"Day {daily_counter} Complete. See you tomorrow :)")
                daily_counter += 1

                time.sleep(86220)  # 23 hours & 57 mins

            except downloader.AuthenticationError:
                messager.send_text_message("Authentication Error.")
                exit()
            except FileNotFoundError:
                messager.send_text_message(
                    f"Files for day {daily_counter} not in Drive."
                )
                exit()
            except messager.SendingError as e:  # TODO Testme
                messager.send_text_message(f"{e}")
                exit()

        else:
            time.sleep(60)


if __name__ == "__main__":
    main()
