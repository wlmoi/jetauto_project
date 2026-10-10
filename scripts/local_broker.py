"""MQTT 3.1.1 broker for loopback-only development."""
import asyncio
import logging

from amqtt.broker import Broker

logging.basicConfig(level=logging.WARNING)


async def main():
    broker = Broker({"listeners": {"default": {"type": "tcp", "bind": "127.0.0.1:1883"}}, "plugins": {"amqtt.plugins.authentication.AnonymousAuthPlugin": {"allow_anonymous": True}}})
    await broker.start()
    print("Local MQTT broker ready at 127.0.0.1:1883", flush=True)
    try:
        await asyncio.Event().wait()
    finally:
        await broker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
