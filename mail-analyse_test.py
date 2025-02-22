#!/usr/bin/env python3

import importlib
import pytest

mail_analyse = importlib.import_module("mail-analyse")

def test_get_destinations():
    assert mail_analyse.get_destinations("Test") == [
        mail_analyse.Destination(
            type=mail_analyse.DestinationType.DEFAULT,
            action="Test",
        )
    ]

    assert mail_analyse.get_destinations("[IMP] Test") == [
        mail_analyse.Destination(
            type=mail_analyse.DestinationType.DEFAULT,
            action="[IMP] Test",
        ),
        mail_analyse.Destination(
            type=mail_analyse.DestinationType.NOTIFICATION,
            action="[IMP] Test",
        ),
    ]

    assert mail_analyse.get_destinations("Task: Test") == [
        mail_analyse.Destination(
            type=mail_analyse.DestinationType.DEFAULT,
            action="Task: Test",
        ),
        mail_analyse.Destination(
            type=mail_analyse.DestinationType.TASK,
            action="Test",
            due_date="",
        ),
    ]

    assert mail_analyse.get_destinations("Task: [Due: 2022-12-31] Test") == [
        mail_analyse.Destination(
            type=mail_analyse.DestinationType.DEFAULT,
            action="Task: [Due: 2022-12-31] Test",
        ),
        mail_analyse.Destination(
            type=mail_analyse.DestinationType.TASK,
            action="Test",
            due_date="2022-12-31",
        ),
    ]

    assert mail_analyse.get_destinations("[URG] Task: [Due: 2022-12-31] Test") == [
        mail_analyse.Destination(
            type=mail_analyse.DestinationType.DEFAULT,
            action="[URG] Task: [Due: 2022-12-31] Test",
        ),
        mail_analyse.Destination(
            type=mail_analyse.DestinationType.NOTIFICATION,
            action="[URG] Task: [Due: 2022-12-31] Test",
        ),
        mail_analyse.Destination(
            type=mail_analyse.DestinationType.TASK,
            action="Test",
            due_date="2022-12-31",
        ),
    ]
