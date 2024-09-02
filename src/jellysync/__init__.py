#!/usr/bin/env python3
import os
import argparse
import httpx
from email.message import EmailMessage
from rich import print
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    FileSizeColumn,
    TotalFileSizeColumn,
    TransferSpeedColumn,
)


def make_download_url(item, host_url, api_key):
    return f"{host_url}/Items/{item['Id']}/Download?api_key={api_key}"


def parse_filename(content_disposition):
    msg = EmailMessage()
    msg["content-type"] = content_disposition
    params = msg["content-type"].params
    return params["filename"]


def download(url):
    with httpx.stream("GET", url) as resp:
        filename = parse_filename(resp.headers["Content-Disposition"])
        filesize = int(resp.headers["Content-Length"])

        if os.path.isfile(filename):
            existing_filesize = os.stat(filename).st_size
            if filesize == existing_filesize:
                print(f"Skipping {filename}")
                return
            else:
                print(f"Replacing {filename}")
        else:
            print(f"Downloading {filename}")

        with open(filename, "wb") as fp:
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                TextColumn("remaining"),
                FileSizeColumn(),
                TextColumn("of"),
                TotalFileSizeColumn(),
                TextColumn("at"),
                TransferSpeedColumn(),
            ) as progress:
                task = progress.add_task("Downloading", total=filesize)
                for bytes in resp.iter_bytes():
                    progress.update(task, advance=len(bytes))
                    fp.write(bytes)


# Get a list of episodes
def get_episodes(show_id, season_id, host_url, api_key):
    url = f"{host_url}/Shows/{show_id}/Episodes?seasonId={season_id}&api_key={api_key}"
    resp = httpx.get(url)
    data = resp.json()
    return data["Items"]


def download_items(items, host_url, api_key):
    for item in items:
        download_url = make_download_url(item, host_url, api_key)
        download(download_url)


def download_season(args):
    episodes = get_episodes(args.show_id, args.season_id, args.host_url, args.api_key)
    download_items(episodes, args.host_url, args.api_key)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host-url",
        help="The Jellyfin host URL, e.g. https://jellyfin.myhost.com",
        required=True,
    )
    parser.add_argument(
        "--api-key",
        help="The Jellyfin API key, e.g. cab52cae2ffe4683a6a8d61a8c568e32",
        required=True,
    )
    subparsers = parser.add_subparsers(title="subcommands", required=True)
    download_season_parser = subparsers.add_parser("download-season")
    download_season_parser.add_argument(
        "show_id", help="The Jellyfin show ID, e.g. 0b6ce693abb4663e3079cb01330bfd58"
    )
    download_season_parser.add_argument(
        "season_id",
        help="The Jellyfin season ID, e.g. b77ea4639d6b5645891f3ab93cafaaf0",
    )
    download_season_parser.set_defaults(func=download_season)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
