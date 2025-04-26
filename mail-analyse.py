import abc
import argparse
import asyncio
from collections.abc import Callable
from enum import Enum
import json
import llm
import logging
import nats
import os
import pydantic
import re
import sys
from typing import Any
import yaml

from mail_analysis import MailAnalyse, MailAnalyseCloud
from models import EmailData, HeaderAnalysis, EmailAction, Notification, Task

sample_email_data = EmailData(
    from_=[ "someone@somwehere.com" ],
    to=[ "me@here.com" ],
    subject="Test email",
    date="2025-02-22T09:07:27+00:00",
    message_id="msg1234567890",
    body="Action due by 2025-02-25",
)
sample_email_action = EmailAction(
    action="Do something",
    due_date="2025-02-25",
    is_important=False,
    notify=False,
)

class DestinationType(str, Enum):
    NOTIFICATION = "Email Notification"
    TASK = "Email Task"
    DEFAULT = "Default"

class Destination(pydantic.BaseModel):
    type: DestinationType
    action: str
    due_date: str = ""

def get_destinations(action: EmailAction) -> list[Destination]:
    """Determine the NATS destinations based on the action"""
    destinations = []

    # Check if the action is important or urgent
    if action.is_important or action.notify:
        destinations.append(
            Destination(
                type=DestinationType.NOTIFICATION,
                action=action.action,
            ))

    # Check if the action is a task
    if action.due_date:
        destinations.append(
            Destination(
                type=DestinationType.TASK,
                action=action.action,
                due_date=action.due_date,
            ))

    return destinations

async def main():
    default_model = os.environ.get("MODEL",
                                   "mlx-community/Llama-3.2-3B-Instruct-4bit")
    default_nats = os.environ.get("NATS", "nats://localhost:4222")

    parser = argparse.ArgumentParser(
        description="Analyse emails",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--model", default=default_model,
                        help="Model to use for analysis")
    parser.add_argument("--nats", default=default_nats,
                        help="NATS server URL")
    parser.add_argument("--nats-stream", default="emails_for_analysis",
                        help="NATS stream to subscribe to")
    parser.add_argument("--nats-consumer", default="email-analyser",
                        help="NATS consumer name")
    parser.add_argument("--nats-subject", default="email.action",
                        help="NATS subject to publish actions to")
    parser.add_argument("--nats-task-subject", default="tasks.email.action",
                        help="NATS subject to publish tasks to")
    parser.add_argument("--nats-notification-subject",
                        default="notifications.email.action",
                        help="NATS subject to publish notifications to")
    parser.add_argument("--limit", type=int, default=50,
                        help="Number of messages to process (-1 for all)")
    parser.add_argument("--debug", action=argparse.BooleanOptionalAction,
                        help="Enable debug logging")
    parser.add_argument("--debug-skip-ack", action=argparse.BooleanOptionalAction,
                        help="Skip acking messages for debugging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s")

    async def error_handler(e):
        logging.error("Error: %s", e)
        sys.exit(1)

    logging.debug("Connecting to NATS server at %s", args.nats)
    nc = await nats.connect(args.nats,
                            error_cb=error_handler)
    js = nc.jetstream()

    # Set up a pull consumer for the stream
    logging.debug("Subscribing to stream %s", args.nats_stream)
    psub = await js.pull_subscribe("", stream=args.nats_stream,
                                   durable=args.nats_consumer)

    logging.debug(f"Creating mail analyser with model %s", args.model)
    analyser = MailAnalyse(model=args.model, model_supports_schemas=False)
    analyser.add_sample(sample_email_data, sample_email_action)

    count = args.limit
    while count > 0:
        count -= 1

        try:
            msgs = await psub.fetch(batch=1, timeout=10)
            if not msgs:
                logging.debug("No messages received, exiting")
                break

            for msg in msgs:
                if not args.debug_skip_ack:
                    await msg.ack()

                raw_data = msg.data.decode()
                logging.debug("Received message: %s", raw_data)

                try:
                    email = EmailData.model_validate_json(raw_data)
                except pydantic.ValidationError as e:
                    logging.error("Error validating email: %s: %s", e, raw_data)
                    continue

                try:
                    action = analyser.process(email)
                    logging.info(action)

                    destinations = get_destinations(action)
                    for destination in destinations:
                        if destination.type == DestinationType.TASK:
                            subject = args.nats_task_subject
                            body = action.model_dump_json()
                        elif destination.type == DestinationType.NOTIFICATION:
                            subject = args.nats_notification_subject
                            body = Notification(
                                title=destination.type.value,
                                message=destination.action).model_dump_json()

                        logging.debug("Publishing action to %s (%s)", subject, body)
                        await nc.publish(subject, body.encode())
                except pydantic.ValidationError as e:
                    logging.error("Error analysing email: %s: %s", e, email.model_dump_json())
                    continue

        except nats.errors.TimeoutError:
            logging.debug("Timeout waiting for messages, exiting")
            break

    await nc.close()

if __name__ == '__main__':
    asyncio.run(main())
