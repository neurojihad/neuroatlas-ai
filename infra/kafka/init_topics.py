import asyncio
import os

from aiokafka.admin import AIOKafkaAdminClient, NewTopic

from common.core.entities.events import EventStream

_TOPIC_ALREADY_EXISTS = 36


async def main() -> None:
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    admin = AIOKafkaAdminClient(bootstrap_servers=bootstrap)
    await admin.start()
    try:
        new_topics = [
            NewTopic(name=stream.value, num_partitions=3, replication_factor=1) for stream in EventStream.all_streams()
        ]
        response = await admin.create_topics(new_topics, validate_only=False)
        for topic, code, message in response.topic_errors:
            if code == 0:
                print(f"Topic ready: {topic}")
            elif code == _TOPIC_ALREADY_EXISTS:
                print(f"Topic already exists: {topic}")
            else:
                raise RuntimeError(f"Could not create topic {topic} ({code}): {message}")
    finally:
        await admin.close()


if __name__ == "__main__":
    asyncio.run(main())
