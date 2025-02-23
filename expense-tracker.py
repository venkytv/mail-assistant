#!/usr/bin/env python3

import argparse
import asyncio
import logging
import nats
import os

async def main():
    default_nats = os.environ.get("NATS", "nats://localhost:4222")
    default_expenses_file = os.path.expanduser("~/Documents/expenses.txt")

    parser = argparse.ArgumentParser(description="Expense tracker",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--nats", default=default_nats, help="NATS server URL")
    parser.add_argument("--nats-stream", default="email_actions",
                        help="NATS stream to subscribe to")
    parser.add_argument("--nats-consumer", default="expense-tracker",
                        help="NATS consumer name")
    parser.add_argument("--expenses-file", default=default_expenses_file,
                        help="File to store expenses in")
    parser.add_argument("--timeout", type=int, default=2,
                        help="Timeout for message fetch")
    parser.add_argument("--limit", type=int, default=50,
                        help="Number of messages to process")
    parser.add_argument("--debug", action=argparse.BooleanOptionalAction,
                        help="Enable debug logging")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    async def error_handler(e):
        logging.error("Error: %s", e)
        sys.exit(1)

    logging.debug("Connecting to NATS server %s", args.nats)
    nc = await nats.connect(args.nats, error_cb=error_handler)
    js = nc.jetstream()

    logging.debug("Subscribing to stream %s", args.nats_stream)
    psub = await js.pull_subscribe("", stream=args.nats_stream,
                                   durable=args.nats_consumer)

    while True:
        acks = []
        try:
            logging.debug("Fetching %d messages with timeout %d",
                          args.limit, args.timeout)
            msgs = await psub.fetch(batch=args.limit, timeout=args.timeout)
            if not msgs:
                logging.debug("No messages to process")
                break

            with open(args.expenses_file, "a") as f:
                for msg in msgs:
                    acks.append(msg.ack())

                    raw_data = msg.data.decode("utf-8")
                    logging.debug("Processing message %s", raw_data)
                    if "Expense:" not in raw_data:
                        logging.debug("Skipping message %s", msg)
                        continue

                    # Process the message
                    logging.debug("Writing message to %s", args.expenses_file)
                    f.write(raw_data)
                    f.write("\n")

        except nats.errors.TimeoutError:
            logging.debug("Timeout waiting for messages")
            break
        finally:
            # Acknowledge all messages
            if acks:
                logging.debug("Waiting for message acknowledgements")
                await asyncio.gather(*acks)

    logging.debug("Closing NATS connection")
    await nc.close()

if __name__ == "__main__":
    asyncio.run(main())
