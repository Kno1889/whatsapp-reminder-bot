import argparse
from downloader import download_files

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--Page", help="Page Number")
    args = parser.parse_args()

    download_files(int(args.Page))

if __name__ == "__main__":
    main()
