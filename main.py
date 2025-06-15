import argparse
from downloader import download_files
from messager import send_daily_messages

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--Page", help="Page Number")
    args = parser.parse_args()

    download_files(int(args.Page))
    send_daily_messages(int(args.Page))
    # send_text_message("test")

if __name__ == "__main__":
    main()
