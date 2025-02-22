#!/usr/bin/env python3

import argparse
import asyncio
import logging
import nats
import os
import subprocess
import sys

from models import Task

logger = logging.getLogger(__name__)

handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)

logger.setLevel(logging.INFO)

# Uses the `reminders` command from https://github.com/keith/reminders-cli
async def add_reminder(task: Task, reminder_list: str):
    logger.info("Adding reminder for task %s to list %s", task, reminder_list)

    # Add the task to the reminder list
    args = ["reminders", "add", reminder_list, task.action]
    if task.due_date:
        args.extend(["--due-date", task.due_date])

    logger.debug("Running command: %s", " ".join(args))
    try:
        result = await asyncio.create_subprocess_exec(*args,
                                                      stdout=subprocess.PIPE,
                                                      stderr=subprocess.PIPE)
        stdout, stderr = await result.communicate()
        if result.returncode != 0:
            logger.error("Error adding reminder: %s", stderr.decode())
        else:
            logger.debug("Reminder added: %s", stdout.decode())
    except FileNotFoundError:
        logger.error("command not found: %s", args[0])

async def main():
    default_nats = os.environ.get("NATS", "nats://localhost:4222")

    parser = argparse.ArgumentParser(
        description="Add reminders for tasks from emails",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--nats", default=default_nats,
                        help="NATS server URL")
    parser.add_argument("--nats-stream", default="tasks",
                        help="NATS stream to subscribe to")
    parser.add_argument("--nats-consumer", default="task-reminder",
                        help="NATS consumer name")
    parser.add_argument("--reminder-list", default="Automatic",
                        help="List to add reminders to")
    parser.add_argument("--limit", type=int, default=-1,
                        help="Number of messages to process (-1 for all)")
    parser.add_argument("--debug", action=argparse.BooleanOptionalAction,
                        help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    logger.debug("Connecting to NATS server at %s", args.nats)
    nc = await nats.connect(args.nats)
    js = nc.jetstream()

    # Set up a pull consumer for the stream
    logger.debug("Subscribing to stream %s", args.nats_stream)
    psub = await js.pull_subscribe("", stream=args.nats_stream,
                                   durable=args.nats_consumer)

    count = args.limit
    while count != 0:
        count -= 1

        try:
            msgs = await psub.fetch(batch=1, timeout=2)
            if not msgs:
                logger.debug("No messages available, exiting")
                break

            for msg in msgs:
                await msg.ack()

                task = Task.model_validate_json(msg.data.decode())
                logger.debug("Received task %s", task)

                await add_reminder(task, args.reminder_list)

        except nats.errors.TimeoutError:
            logger.debug("Timeout waiting for messages, exiting")
            break

    await nc.close()

if __name__ == "__main__":
    asyncio.run(main())
