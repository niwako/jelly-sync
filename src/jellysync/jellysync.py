#!/usr/bin/env python3
import httpx
import os
from dataclasses import dataclass
from pathvalidate import sanitize_filepath
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
from rich.text import Text


@dataclass
class JellySync:
    host_url: str
    api_key: str
    media_dir: str
    dry_run: bool

    def __post_init__(self):
        os.chdir(self.media_dir)

    def download_season(self, show_id: str, season_id: str):
        episodes = self.get_episodes(show_id, season_id)
        self.download_items(episodes)

    def get_auth_header(self) -> dict[str, str]:
        return {
            "Authorization": f'MediaBrowser Client="jelly-sync", Token="{self.api_key}"'
        }

    def get_episodes(self, show_id: str, season_id: str):
        url = f"{self.host_url}/Shows/{show_id}/Episodes?seasonId={season_id}"
        resp = httpx.get(url, headers=self.get_auth_header())
        data = resp.json()
        return data["Items"]

    def download_items(self, items):
        for item in items:
            download_url = self.make_download_url(item)
            output_path = self.make_file_path(item)
            self.download(download_url, output_path)

    def make_download_url(self, item):
        return f"{self.host_url}/Items/{item['Id']}/Download"

    def download(self, url: str, filename: str):
        with httpx.stream("GET", url, headers=self.get_auth_header()) as resp:
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

            if self.dry_run:
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

    def make_file_path(self, item):
        # TODO: Handle movies
        series = item["SeriesName"]
        episode_id = f"S{item['ParentIndexNumber']:02d}E{item['IndexNumber']:02d}"
        title = item["Name"]
        ext = item["Container"]
        return sanitize_filepath(
            os.path.join(
                "Shows",
                series,
                f"Season {item['ParentIndexNumber']:02d}",
                f"{series} - {episode_id} - {title}.{ext}",
            )
        )