# VisitReady

VisitReady is an independent **fictional appointment-readiness prototype**. It answers bounded logistics questions from reviewed public guidance and creates local tasks for reported needs requiring a person. It has no hospital, EHR, MyChart, booking, or messaging integration.

## Current workflow

1. Python loads the fictional appointment and screens the latest question.
2. Unsupported or unauthorized requests are denied before any model call and create no staff task. Recognized medical questions bypass all model roles and offer **Care team review**. Only clicking that button submits the exact fictional question to the appointment-linked demo queue.
3. For recognizable logistics, Readiness proposes a structured next step and any reported checklist update.
4. Python checks the proposal before running anything else.
5. A logistics case requiring human review calls **Communication**, which writes an internal staff summary. Python checks its structure, scope, and exact source quotes, then attaches an eligible draft to the local task. A basic summary is used if drafting fails or fails its checks.
6. A case eligible for automatic guidance calls **Orchestrator**, followed by **Resource** only if an approved topic was selected. Python assembles the caregiver-facing answer. Communication does not run on this branch.

The four model roles are conditional. A lost-ride review normally uses Readiness and Communication; a parking question normally uses Readiness, Orchestrator and Resource.

## Communication's staff-summary role

The OpenAI Responses API returns a typed StaffSummaryDraft containing a concise summary, reported logistics details with exact source quotes, and checked unresolved items for staff to review. It uses the existing configured model.

Communication has no tools. It cannot change records, approve actions, book assistance, contact staff, or choose the review route.

communication_policy.py checks route eligibility, length, allowed review items, exact quote support, and some unsupported wording. **These checks do not prove every paraphrase is correct.** The staff screen labels AI summaries as drafts and displays their evidence and the original fictional report for human verification. Structured output guarantees a shape, not factual correctness.

staff_tasks.py stores the summary, its origin (AI draft or template), and the original **fictional logistics** report. Explicitly submitted clinical requests retain the exact fictional question without an AI summary and target **Appointment care team (demo)**. Until the caregiver clicks the review-request button, the clinical question stays in session memory, not the queue. Denied requests never create staff tasks. Identical pending reports are deduplicated; distinct questions get distinct tasks. Existing metadata-only tasks still load, including older other-question tasks created before scope denial was added.

The caregiver receives a separate controlled acknowledgement. Internal staff summaries do not appear in that reply. Mark seen in demo records acknowledgement, not resolution or clinical review.

## Caregiver-requested clinical review

The demo recognizes a medical question, offers a review-request button, and saves a ticket only after the caregiver requests it. The confirmation shows the ticket ID, appointment, fixed fictional team and **Awaiting review** status. The staff page displays that same exact fictional question. No AI role runs during preparation or submission. A failed write shows no success confirmation and permits retry. This is a simulated handoff, without hospital messaging or a staff-reply feature.

The composer clears after a successfully handled question, including a scope refusal. The last submitted question and response remain visible independently of the new draft. Failed requests keep the input for retry. This is still the latest exchange, not full multi-turn conversation memory.

## Appointment-aware public guidance

The curated catalog covers what to bring, parking/directions, and MyChart registration/eCheck-in. Parking uses the scheduled location from data/appointment.json when available. Missing, unmapped, or conflicting locations need clarification. Reviewed parking information covers six destinations, with addresses, map links, instructions, and sources. It does not check live space availability or calculate the nearest clinic.

JSON files represent demo context, not model training data. Saved caregiver checklist changes do not override the appointment feed's scheduled location.

## Run locally

Use the existing local .env containing OPENAI_API_KEY and OPENAI_MODEL. Never commit or display the key. From the project folder in PowerShell:

    .\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502

The caregiver page handles the fictional visit. **Staff Demo** displays local review tasks and summary drafts. **Run History** records fixed workflow events without caregiver or model prose. These are demo screens, not authenticated accounts.

## Demonstrate

- **Parking:** Where can I find parking? Uses the appointment location and reviewed parking facts. Communication is skipped.
- **Simple logistics review:** My ride fell through. A checked review case calls Communication and creates a local task with a staff draft or fallback.
- **Varied report:** My ride fell through. Registration is done. I have the referral, but I don't know if it is the right one. Staff can compare the summary with quoted evidence and the original report.
- **Clinical question:** What medicine should my child take? Recognized wording bypasses all AI roles. Click **Care team review** to save the exact fictional question, then show the ticket confirmation and matching staff-queue item. Without that click, no clinical ticket is created.
- **Denied request:** Solve this equation for me. The first check refuses the request, calls no AI role, and creates no staff task. Run History records a blocked scope check without storing the original question.

No ride is arranged, appointment changed, or hospital contacted.

## Verify

    .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --ignore=runtime .

Tests use controlled model roles and temporary queues. They cover quote support, failure fallback, visible staff handoffs, unchanged appointment records, skipped roles, deduplication and legacy tasks. They do not establish real-world usefulness, clinical safety, or superiority over a template.

evaluate.py --live --repeat 2 makes paid API requests for fictional scenarios. Interpret results as the scenarios actually run. The saved live-evaluation file may describe an earlier app version.

## Boundaries and next work

This is a single-appointment local prototype. The input gate uses limited phrase matching; mixed or unfamiliar medical wording can evade that first screen. It has no production authentication, authorization, clinical workflow, operational task resolution, or outcome validation. The caregiver interface uses the latest question plus appointment state rather than a complete conversation history.

Before real healthcare use, the design needs stakeholder validation, privacy/security review, approved integrations and data agreements, operational ownership, and broader evaluation. A useful next experiment compares AI summaries against templates on longer fictional reports, measuring factual retention, preserved uncertainty, reviewer clarity, latency, and cost.

## Restart shortcut

Double-click Restart_VisitReady.cmd in this project folder to restart the local server. It checks that any listener on port 8502 is a Python Streamlit app.py process before stopping it, then starts the app with the existing virtual environment. An unrecognized listener causes the shortcut to stop without terminating it. Leave the new console window open.
