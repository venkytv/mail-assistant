#!/usr/bin/env python3

from conftest import get_test_cases, get_test_cases_for_analysis
import importlib
import pytest

from models import EmailData, HeaderAnalysis, EmailAction, Notification, Task

mail_analyse = importlib.import_module("mail-analyse")

@pytest.mark.llm
@pytest.mark.parametrize("test_case", get_test_cases().items())
def test_mail_analyse(test_case):
    test_name, test_data = test_case
    email_data, expected_analysis, _ = test_data

    m = mail_analyse.MailAnalyseHeaders(model="4o-mini")
    response = m.process(email_data)
    assert isinstance(response, HeaderAnalysis), test_name
    assert response.is_important == expected_analysis.is_important, test_name
    assert response.is_transactional == expected_analysis.is_transactional, test_name
    assert response.needs_analysis == expected_analysis.needs_analysis, f"{test_name} - {response.analysis_reason}"

@pytest.mark.llm
@pytest.mark.parametrize("test_case", get_test_cases_for_analysis().items())
def test_mail_analyse_analysis(test_case):
    test_name, test_data = test_case
    email_data, _, expected_action = test_data

    m = mail_analyse.MailAnalyse(
        model="mlx-community/Llama-3.2-3B-Instruct-4bit",
        model_supports_schemas=False)
    m.add_sample(
        EmailData(
            from_=[ "someone@somwehere.com" ],
            to=[ "me@here.com" ],
            subject="Test email",
            date="2025-02-22T09:07:27+00:00",
            message_id="msg1234567890",
            body="Action due by 2025-02-25",
        ),
        EmailAction(
            action="Do something",
            due_date="2025-02-25",
            is_important=True,
            notify=False,
        )
    )
    response = m.process(email_data)
    assert isinstance(response, EmailAction), test_name
    assert response.due_date == expected_action.due_date, test_name
    assert response.is_important == expected_action.is_important, test_name
    assert response.notify == expected_action.notify, test_name


#Destination = mail_analyse.Destination
#DestinationType = mail_analyse.DestinationType

#def test_get_destinations():
#    assert mail_analyse.get_destinations("Test") == [
#        Destination(
#            type=DestinationType.DEFAULT,
#            action="Test",
#        )
#    ]
#
#    assert mail_analyse.get_destinations("[IMP] Test") == [
#        Destination(
#            type=DestinationType.DEFAULT,
#            action="[IMP] Test",
#        ),
#        Destination(
#            type=DestinationType.NOTIFICATION,
#            action="[IMP] Test",
#        ),
#    ]
#
#    assert mail_analyse.get_destinations("Task: Test (me@example.com, 2025-02-22T09:07:27+00:00)") == [
#        Destination(
#            type=DestinationType.DEFAULT,
#            action="Task: Test (me@example.com, 2025-02-22T09:07:27+00:00)",
#        ),
#        Destination(
#            type=DestinationType.TASK,
#            action="Test",
#            due_date="",
#        ),
#    ]
#
#    assert mail_analyse.get_destinations("Task: [Due: 2022-12-31] Test (me@example.com, 2025-02-22T09:07:27+00:00)") == [
#        Destination(
#            type=DestinationType.DEFAULT,
#            action="Task: [Due: 2022-12-31] Test (me@example.com, 2025-02-22T09:07:27+00:00)"
#        ),
#        Destination(
#            type=DestinationType.TASK,
#            action="Test",
#            due_date="2022-12-31",
#        ),
#    ]
#
#    assert mail_analyse.get_destinations("[URG] Task: [Due: 2022-12-31] Test") == [
#        Destination(
#            type=DestinationType.DEFAULT,
#            action="[URG] Task: [Due: 2022-12-31] Test",
#        ),
#        Destination(
#            type=DestinationType.NOTIFICATION,
#            action="[URG] Task: [Due: 2022-12-31] Test",
#        ),
#        Destination(
#            type=DestinationType.TASK,
#            action="Test",
#            due_date="2022-12-31",
#        ),
#    ]
#
#@pytest.mark.parametrize("destination_type, action, due_date, expected", [
#    (DestinationType.DEFAULT, "Default Test 1", "", b"Default Test 1"),
#    (DestinationType.DEFAULT, "Default Test 2", "today", b"Default Test 2"),
#    (DestinationType.DEFAULT, "[IMP] Default Test 3", "today", b"[IMP] Default Test 3"),
#
#    (DestinationType.NOTIFICATION, "[IMP] Notification Test 1", "",
#        Notification(title="Email Notification", message="[IMP] Notification Test 1").model_dump_json().encode()),
#    (DestinationType.NOTIFICATION, "[URG] Notification Test 2", "2025-02-22",
#        Notification(title="Email Notification", message="[URG] Notification Test 2").model_dump_json().encode()),
#
#    (DestinationType.TASK, "Task Test 1", "", Task(action="Task Test 1").model_dump_json().encode()),
#    (DestinationType.TASK, "Task Test 2", "2025-02-22",
#        Task(action="Task Test 2", due_date="2025-02-22").model_dump_json().encode()),
#])
#def test_destination_content(destination_type, action, due_date, expected):
#    subjects = {
#        DestinationType.DEFAULT: "subject.default",
#        DestinationType.NOTIFICATION: "subject.notification",
#        DestinationType.TASK: "subject.task",
#    }
#    content = mail_analyse.destination_content(subjects)
#
#    destination = Destination(
#        type=destination_type,
#        action=action,
#        due_date=due_date,
#    )
#    subject, body = content(destination)
#    assert subject == subjects[destination_type]
#    assert body == expected
