#!/usr/bin/env python3

import importlib
import pytest

from models import Notification, Task

mail_analyse = importlib.import_module("mail-analyse")
Destination = mail_analyse.Destination
DestinationType = mail_analyse.DestinationType

def test_get_destinations():
    assert mail_analyse.get_destinations("Test") == [
        Destination(
            type=DestinationType.DEFAULT,
            action="Test",
        )
    ]

    assert mail_analyse.get_destinations("[IMP] Test") == [
        Destination(
            type=DestinationType.DEFAULT,
            action="[IMP] Test",
        ),
        Destination(
            type=DestinationType.NOTIFICATION,
            action="[IMP] Test",
        ),
    ]

    assert mail_analyse.get_destinations("Task: Test (me@example.com, 2025-02-22T09:07:27+00:00)") == [
        Destination(
            type=DestinationType.DEFAULT,
            action="Task: Test (me@example.com, 2025-02-22T09:07:27+00:00)",
        ),
        Destination(
            type=DestinationType.TASK,
            action="Test",
            due_date="",
        ),
    ]

    assert mail_analyse.get_destinations("Task: [Due: 2022-12-31] Test (me@example.com, 2025-02-22T09:07:27+00:00)") == [
        Destination(
            type=DestinationType.DEFAULT,
            action="Task: [Due: 2022-12-31] Test (me@example.com, 2025-02-22T09:07:27+00:00)"
        ),
        Destination(
            type=DestinationType.TASK,
            action="Test",
            due_date="2022-12-31",
        ),
    ]

    assert mail_analyse.get_destinations("[URG] Task: [Due: 2022-12-31] Test") == [
        Destination(
            type=DestinationType.DEFAULT,
            action="[URG] Task: [Due: 2022-12-31] Test",
        ),
        Destination(
            type=DestinationType.NOTIFICATION,
            action="[URG] Task: [Due: 2022-12-31] Test",
        ),
        Destination(
            type=DestinationType.TASK,
            action="Test",
            due_date="2022-12-31",
        ),
    ]

@pytest.mark.parametrize("destination_type, action, due_date, expected", [
    (DestinationType.DEFAULT, "Default Test 1", "", b"Default Test 1"),
    (DestinationType.DEFAULT, "Default Test 2", "today", b"Default Test 2"),
    (DestinationType.DEFAULT, "[IMP] Default Test 3", "today", b"[IMP] Default Test 3"),

    (DestinationType.NOTIFICATION, "[IMP] Notification Test 1", "",
        Notification(title="Email Notification", message="[IMP] Notification Test 1").model_dump_json().encode()),
    (DestinationType.NOTIFICATION, "[URG] Notification Test 2", "2025-02-22",
        Notification(title="Email Notification", message="[URG] Notification Test 2").model_dump_json().encode()),

    (DestinationType.TASK, "Task Test 1", "", Task(action="Task Test 1").model_dump_json().encode()),
    (DestinationType.TASK, "Task Test 2", "2025-02-22",
        Task(action="Task Test 2", due_date="2025-02-22").model_dump_json().encode()),
])
def test_destination_content(destination_type, action, due_date, expected):
    subjects = {
        DestinationType.DEFAULT: "subject.default",
        DestinationType.NOTIFICATION: "subject.notification",
        DestinationType.TASK: "subject.task",
    }
    content = mail_analyse.destination_content(subjects)

    destination = Destination(
        type=destination_type,
        action=action,
        due_date=due_date,
    )
    subject, body = content(destination)
    assert subject == subjects[destination_type]
    assert body == expected
