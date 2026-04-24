## ADDED Requirements

### Requirement: Core happy-path flows covered

The UI suite SHALL cover, at minimum, the following core flows against the web review UI (Flask backend + Vite frontend):

1. **Upload flow** — drag-drop or file-picker upload of a fixture audio file, verifying the POST `/api/v1/import` succeeds and the UI navigates to the analyze screen.
2. **Analyze flow** — clicking the Analyze button triggers backend analysis and the UI renders the analyze screen with section/beat data populated.
3. **View flow** — navigating the analyze screen's beat and section views verifies that rendered content matches backend data (assertion: beat count in UI equals beat count in analysis JSON).
4. **Export flow** — clicking Export produces a downloadable `.xsq` file and the filename contains the fixture's base name.

Additional flows MAY be added over time. Each flow SHALL live in `tests/ui/flows/test_<flow>.py` and use the Playwright + pytest fixtures provided by the suite.

#### Scenario: Upload flow completes end-to-end

- **WHEN** the upload flow test uploads a fixture audio file via the UI
- **THEN** the test SHALL observe a POST to `/api/v1/import` returning 200
- **AND** the test SHALL observe the analyze screen rendered with the fixture's title visible

#### Scenario: UI data matches backend data

- **WHEN** the view flow test loads an analyzed fixture
- **THEN** the number of beats displayed in the UI SHALL match the beat count in the backend's `_analysis.json`
- **AND** the number of sections displayed SHALL match the backend's section count

### Requirement: Three-strike retry for UI flakes

The UI suite SHALL retry each failing flow test up to 3 times. A test SHALL be considered passing if any of the 3 attempts succeed. A test SHALL be considered failing only if all 3 attempts fail.

Retries SHALL apply only to the UI suite. The analyzer and generator suites SHALL NOT retry; a failure there indicates a tolerance bug, not a flake.

#### Scenario: Flaky UI test passes on second attempt

- **WHEN** a UI flow test fails on its first attempt due to a timing flake but passes on its second
- **THEN** the suite SHALL report PASS for that flow
- **AND** the JSON report SHALL record that 1 retry was used

#### Scenario: UI test fails consistently

- **WHEN** a UI flow test fails all 3 attempts
- **THEN** the suite SHALL report FAIL for that flow
- **AND** the gate SHALL exit with code `6`

### Requirement: UI tests run against locally-spawned servers

The UI suite SHALL spawn its own Flask backend and Vite dev server as pytest fixtures and SHALL NOT rely on any manually-started server. Ports SHALL be selected dynamically to avoid collisions on shared CI runners. Servers SHALL be torn down after the test session ends, even on failure.

#### Scenario: Tests run on a runner with no pre-started servers

- **WHEN** the UI suite runs on a fresh GitHub-hosted runner
- **THEN** the suite's pytest fixtures SHALL spawn Flask and Vite dev servers automatically
- **AND** the tests SHALL connect to them at the fixtures' chosen ports
- **AND** all server processes SHALL be terminated at session teardown

### Requirement: Visual regression via sectioned screenshots (optional, advisory)

The UI suite MAY capture sectioned screenshots of the analyze and library screens using `openwolf designqc` conventions and store them under `tests/golden/ui/`. Screenshot comparison SHALL be advisory-only for this change — a pixel diff above threshold SHALL log a warning but SHALL NOT fail the gate. Promoting screenshots to a hard-fail requirement is deferred to a future change once the UI has stabilized.

#### Scenario: Screenshot diff exceeds threshold

- **WHEN** a UI flow captures a screenshot that differs from the golden by more than the threshold
- **THEN** the suite SHALL log a WARNING
- **AND** the suite SHALL NOT fail the gate on that warning
