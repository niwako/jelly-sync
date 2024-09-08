#!/usr/bin/env python3
import argparse
from .jellysync import JellySync


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
    download_season_parser.set_defaults(cmd="download-season")
    download_season_parser.add_argument(
        "show_id", help="The Jellyfin show ID, e.g. 0b6ce693abb4663e3079cb01330bfd58"
    )
    download_season_parser.add_argument(
        "season_id",
        help="The Jellyfin season ID, e.g. b77ea4639d6b5645891f3ab93cafaaf0",
    )
    args = parser.parse_args()

    jelly_sync = JellySync(
        args.host_url,
        args.api_key,
        args.media_dir,
        args.dry_run,
    )

    if args.cmd == "download-season":
        jelly_sync.download_season(args.show_id, args.season_id)


if __name__ == "__main__":
    main()
