# Source-file reference

All application, example, test, and fixture files were copied without code changes from the working VisitReady project. The repository README, configuration example, and ignore rules were prepared for sharing. Original technical notes are in WORKFLOW.md.

## Application and UI

- [app.py](../app.py)
- [caregiver_view.py](../caregiver_view.py)
- [caregiver_response.py](../caregiver_response.py)
- [ui_styles.py](../ui_styles.py)
- [patient_profile.py](../patient_profile.py)
- [parking_view.py](../parking_view.py)
- [pages/1_Staff_Demo.py](../pages/1_Staff_Demo.py)
- [pages/2_Run_History.py](../pages/2_Run_History.py)

## AI roles and configuration

- [api_client.py](../api_client.py)
- [readiness_agent.py](../readiness_agent.py)
- [orchestrator_agent.py](../orchestrator_agent.py)
- [resource_agent.py](../resource_agent.py)
- [communication_agent.py](../communication_agent.py)
- [prompts.py](../prompts.py)

## Workflow, checks, and schemas

- [coordinator.py](../coordinator.py)
- [clinical_gate.py](../clinical_gate.py)
- [policies.py](../policies.py)
- [communication_policy.py](../communication_policy.py)
- [models.py](../models.py)
- [visit_state.py](../visit_state.py)
- [readiness.py](../readiness.py)
- [safe_questions.py](../safe_questions.py)
- [review.py](../review.py)
- [updates.py](../updates.py)

## Tools and storage

- [tools.py](../tools.py)
- [storage.py](../storage.py)
- [staff_tasks.py](../staff_tasks.py)
- [run_history.py](../run_history.py)
- [resource_tools.py](../resource_tools.py)
- [parking_tools.py](../parking_tools.py)

## Examples, evaluation, and launch helpers

- [demo_agent.py](../demo_agent.py)
- [example.py](../example.py)
- [mock_example.py](../mock_example.py)
- [evaluate.py](../evaluate.py)
- [restart_visitready.py](../restart_visitready.py)
- [Restart_VisitReady.cmd](../Restart_VisitReady.cmd)

## Automated tests

- [conftest.py](../conftest.py)
- [test_appointment_parking.py](../test_appointment_parking.py)
- [test_caregiver_response.py](../test_caregiver_response.py)
- [test_clinical_route.py](../test_clinical_route.py)
- [test_communication_agent.py](../test_communication_agent.py)
- [test_communication_policy.py](../test_communication_policy.py)
- [test_coordinator_state.py](../test_coordinator_state.py)
- [test_orchestrator_agent.py](../test_orchestrator_agent.py)
- [test_parking.py](../test_parking.py)
- [test_parking_ui.py](../test_parking_ui.py)
- [test_resource_agent.py](../test_resource_agent.py)
- [test_review.py](../test_review.py)
- [test_review_submission.py](../test_review_submission.py)
- [test_run_history.py](../test_run_history.py)
- [test_scope_denial.py](../test_scope_denial.py)
- [test_staff_summary_flow.py](../test_staff_summary_flow.py)
- [test_staff_summary_ui.py](../test_staff_summary_ui.py)
- [test_staff_tasks.py](../test_staff_tasks.py)
- [test_transportation_escalation.py](../test_transportation_escalation.py)
- [test_ui_flow.py](../test_ui_flow.py)

## Fixtures and configuration

- [.streamlit/config.toml](../.streamlit/config.toml)
- [data/appointment.json](../data/appointment.json)
- [data/evaluation_cases.json](../data/evaluation_cases.json)
- [data/parking_locations.json](../data/parking_locations.json)
- [data/patient_profile.json](../data/patient_profile.json)
- [data/public_guidance.json](../data/public_guidance.json)
- [requirements.txt](../requirements.txt)
