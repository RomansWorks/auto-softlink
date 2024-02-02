import argparse
import logging
import os
import yaml
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dataclasses import dataclass
import subprocess


def parse_args():
    parser = argparse.ArgumentParser(description="Watch directories for changes.")
    parser.add_argument(
        "config_path",
        metavar="CONFIG",
        type=str,
        help="Path to config file in a YAML format",
    )
    parser.add_argument(
        "--sources", metavar="SRC", nargs="*", help="Directories to watch"
    )
    parser.add_argument(
        "--targets",
        metavar="TGT",
        nargs="*",
        help="Directories to soflink the files to",
    )
    parser.add_argument(
        "--rm-broken-links",
        action="store_true",
        help="Remove broken links in the target folders",
    )
    parser.add_argument(
        "--verify-no-dangerous-paths",
        action="store_true",
        help="Verify that no dangerous paths are being watched (e.g. /)",
    )
    parser.add_argument(
        "--verify-no-regular-files-in-target",
        action="store_true",
        help="Verify that no regular files are in the target folders",
    )
    parser.add_argument(
        "--max-files-in-sources",
        type=int,
        default=-1,
        help="Verify that the sources folders do not contain more than this number of files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not actually sync or remove anything",
    )

    return parser.parse_args()


@dataclass
class Config:
    sources: list[str]
    targets: list[str]

    @classmethod
    def from_file(cls, path: str):
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        return cls(**data)


class FileTreeSyncer(FileSystemEventHandler):
    def __init__(
        self,
        source_folders,
        target_folders,
        rm_broken_links=True,
        # verify_no_dangerous_paths=True,
        verify_no_regular_files_in_target=True,
        max_files_in_source=1000,
        dry_run=False,
    ) -> None:
        super().__init__()
        self.source_folders = source_folders
        self.target_folders = target_folders
        self.rm_broken_links = rm_broken_links
        # self.verify_no_dangerous_paths = verify_no_dangerous_paths
        self.verify_no_regular_files_in_target = verify_no_regular_files_in_target
        self.max_files_in_source = max_files_in_source
        self.dry_run = dry_run

    def on_modified(self, event):
        pass

    def on_created(self, event):
        logging.info(f"Created: {event.src_path}")
        self._sync_trees()

    def on_deleted(self, event):
        logging.info(f"Deleted: {event.src_path}")
        self._sync_trees()

    def _sync_trees(
        self,
    ):
        # Verify that there are no dangerous paths
        if self.verify_no_dangerous_paths:
            self._verify_no_dangerous_paths()

        # Verify that there are no regular (non softlink) files in the target folders
        if self.verify_no_regular_files_in_target:
            self._verify_no_regular_files_in_target()

        # Verify that there are not too many files in the source folder trees (to avoid accidental listing large trees)
        if self.max_files_in_source > -1:
            self._verify_max_files_in_source(self.max_files_in_source)

        # Sync the folders using rsync
        for source_folder in self.source_folders:
            for target_folder in self.target_folders:
                logging.info(f"Syncing {source_folder} to {target_folder}")
                rsync_cmd = ["rsync", "-al", source_folder, target_folder]
                if self.dry_run:
                    rsync_cmd.append("--dry-run")
                subprocess.call(rsync_cmd)

        # Clean any links which are no longer pointing to a file
        if self.rm_broken_links:
            self._rm_broken_links()

    def _rm_broken_links(self):
        # Clean any links which are no longer pointing to a file
        for target_folder in self.target_folders:
            rm_cmd = "rm" if not self.dry_run else "echo rm"
            cmd = [
                "find",
                target_folder,
                "-type",
                "l",
                "-xtype",
                "l",
                "-exec",
                rm_cmd,
                "{}",
                ";",
            ]
            subprocess.call(cmd)

    # def _verify_no_dangerous_paths(self):
    #     for path in self.source_folders + self.target_folders:
    #         if path == "/":
    #             raise ValueError(
    #                 "Cannot watch the root file system or use it as a target"
    #             )

    def _verify_no_regular_files_in_target(self):
        for target_folder in self.target_folders:
            for root, dirs, files in os.walk(target_folder):
                for file in files:
                    if os.path.isfile(os.path.join(root, file)):
                        raise ValueError(
                            f"Target folder {target_folder} contains regular files"
                        )

    def _verify_max_files_in_source(self, max_files_in_source):
        count = 0
        for source_folder in self.source_folders:
            for root, dirs, files in os.walk(source_folder):
                count += len(files)
                if count > max_files_in_source:
                    raise ValueError(
                        f"Source folder {source_folder} contains more than {max_files_in_source} files"
                    )


def args_to_config(args):
    if args.sources and args.targets:
        return Config(args.sources, args.targets)
    elif args.config_path:
        return Config.from_file(args.config_path)
    else:
        raise ValueError(
            "No config provided via args (as file or as source and target folder lists)"
        )


if __name__ == "__main__":
    # Load command line args
    args = parse_args()
    # Load config from args (either from file or from args)
    config = args_to_config(args.config)
    # Validate that there is no accidental listing of the root file system or any other dangerous paths
    for path in config.sources + config.targets:
        if path == "/":
            raise ValueError("Cannot watch the root file system or use it as a target")

    logging.basicConfig(level=logging.INFO)

    event_handler = FileTreeSyncer(config.sources, config.targets)

    observer = Observer()
    for source in config.sources:
        observer.schedule(event_handler, path=source, recursive=False)

    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
