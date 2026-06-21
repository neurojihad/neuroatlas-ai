import os
import subprocess

from common.core.entities.events import EventStream


def main() -> None:
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    for stream in EventStream.all_streams():
        subprocess.run(
            [
                "kafka-topics.sh",
                "--bootstrap-server",
                bootstrap,
                "--create",
                "--if-not-exists",
                "--topic",
                stream,
                "--partitions",
                "3",
                "--replication-factor",
                "1",
            ],
            check=True,
        )
        print(f"Topic ready: {stream}")


if __name__ == "__main__":
    main()
