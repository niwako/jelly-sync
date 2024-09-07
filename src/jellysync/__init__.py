#!/usr/bin/env python3
import os
import argparse
import httpx
from pathvalidate import sanitize_filepath
from email.message import EmailMessage
from rich import print
from rich.text import Text
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


def make_file_path(item, media_dir):
    # TODO: Handle movies
    series = item["SeriesName"]
    episode_id = f"S{item['ParentIndexNumber']:02d}E{item['IndexNumber']:02d}"
    title = item["Name"]
    ext = item["Container"]
    return sanitize_filepath(
        os.path.join(
            media_dir,
            "Shows",
            series,
            f"Season {item['ParentIndexNumber']:02d}",
            f"{series} - {episode_id} - {title}.{ext}",
        )
    )


def parse_filename(content_disposition):
    msg = EmailMessage()
    msg["content-type"] = content_disposition
    params = msg["content-type"].params
    return params["filename"]


def download(url, filename, dry_run):
    with httpx.stream("GET", url) as resp:
        filesize = int(resp.headers["Content-Length"])

        if os.path.isfile(filename):
            existing_filesize = os.stat(filename).st_size
            if filesize == existing_filesize:
                text = Text()
                text.append("Skipping ", style="bold red")
                text.append(filename, style="bold")
                text.append(" because file already exists", style="bold blue")
                print(text)
                return

        if dry_run:
            text = Text()
            text.append("Skipping ", style="bold red")
            text.append(filename, style="bold")
            text.append(" because dry-run flag is set", style="bold blue")
            print(text)
            return

        text = Text()
        text.append("Downloading ", style="bold green")
        text.append(filename, style="bold")
        print(text)

        folder = os.path.dirname(filename)
        os.makedirs(folder, exist_ok=True)

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


def download_items(items, host_url, api_key, media_dir, dry_run):
    for item in items:
        download_url = make_download_url(item, host_url, api_key)
        output_path = make_file_path(item, media_dir)
        download(download_url, output_path, dry_run)


def download_season(args):
    episodes = get_episodes(args.show_id, args.season_id, args.host_url, args.api_key)
    download_items(episodes, args.host_url, args.api_key, args.media_dir, args.dry_run)


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
    parser.add_argument(
        "--media-dir",
        help="The destinatin media folder, e.g. /mnt/media",
        required=True,
    )
    parser.add_argument(
        "--dry-run",
        help="Do a dry run without downloading",
        action="store_true",
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
