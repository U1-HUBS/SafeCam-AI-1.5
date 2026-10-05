# PRD — AI CCTV Central Monitoring & Violence Incident Management System

**Working Name:** CCTV Sentinel

**Document Version:** 0.1

**Date:** October 5, 2026

**Status:** Draft / Product Definition

---

## 1. Product Overview

CCTV Sentinel is a centralized monitoring system for multiple CCTV cameras that uses an AI violence-detection engine to identify potentially violent incidents such as fighting or physical altercations.

The system continuously receives CCTV streams, analyzes sampled video frames, aggregates AI predictions over time, and creates a **suspected violence incident** when detection conditions are met. When an incident is created, the system preserves a video clip containing footage from **before, during, and after** the detected event.

Operators can immediately see the affected camera, inspect the live feed and incident clip, acknowledge the alert, and classify the AI result as **Confirmed Violence**, **False Positive / Not Violence**, or **Needs Review**. All reviewed incidents are retained in a searchable history for reporting and investigation.

### Core product goals

1. Monitor multiple CCTV cameras from one central dashboard.
2. Detect possible fighting/violence automatically.
3. Generate visible and audible alerts for high-confidence events.
4. Automatically save incident clips with pre-event and post-event footage.
5. Maintain a searchable history of violence detections.
6. Allow human reviewers to reject detections as not violence.
7. Build a feedback dataset from false positives and confirmed incidents for future model improvement.

---

## 2. Problem Statement

Traditional CCTV systems primarily provide recording and manual viewing. Security personnel may need to watch many feeds simultaneously, which makes it easy to miss short violent incidents.

CCTV Sentinel reduces this monitoring burden by turning raw CCTV video into actionable events. Instead of requiring an operator to continuously watch every camera, the system raises an alert when the AI detects a sustained pattern associated with violence.

The system is **decision support**, not an autonomous authority. AI detections must be treated as suspected incidents until reviewed by an authorized human operator.

---

## 3. Reference AI Engine

The initial AI integration is based on the open-source repository:

**sukhitashvili/violence-detection**

The current repository uses OpenAI CLIP with the `ViT-B/32` model, performs image-level prediction, calculates similarity between the image and configured text labels, and returns a top label plus confidence. Its default configuration uses a `0.23` prediction threshold and CPU inference. The label list is configurable and includes examples such as `fight on a street`, `street violence`, and `violence in office`. The repository also notes future work around batch processing, multiple suggestions, and threshold tuning. 

### Important engineering implication

The repository's `Model.predict()` accepts an image and returns a single prediction. It does **not** natively produce a temporal event such as “a fight occurred from 10:32:15 to 10:32:24.” Therefore, CCTV Sentinel will place a dedicated **Temporal Event Aggregator** around the model.

### Initial AI flow

```text
CCTV RTSP Stream
      ↓
Frame / Segment Ingestion
      ↓
Frame Sampling
      ↓
AI Frame Classification
      ↓
Label + Confidence
      ↓
Temporal Event Aggregator
      ↓
Violence Score / Event State
      ↓
Alert Trigger
      ↓
Incident Recorder / Clip Builder
      ↓
Incident Database + Video Storage
      ↓
Operator Review
      ↓
Confirmed / False Positive / Needs Review
```

---

## 4. Scope

### In Scope — MVP

- CCTV camera registration and management
- RTSP stream support
- Central live camera wall
- Camera online/offline status
- AI processing status per camera
- Frame sampling and model inference
- Temporal aggregation of frame predictions
- Fight / suspected violence detection
- Configurable detection threshold
- Alert creation
- On-screen alert queue
- Audible alert for new high-priority incidents
- Automatic incident clip creation
- Pre-event recording buffer
- Post-event recording window
- Incident review screen
- False-positive / not-violence flagging
- Incident notes
- Incident history
- Search, filtering, and date-based reporting
- Role-based access
- Audit trail for incident review
- Video retention settings

### Out of Scope — MVP

- Facial recognition
- Automatic identification of students/persons
- Automatic disciplinary action
- Automatic police/emergency dispatch
- Weapon identification
- Audio-based violence detection
- Crowd identity tracking
- Fully autonomous determination that a person is a bully
- Cloud-only video processing

These can be evaluated in later phases.

---

## 5. Users and Roles

### 5.1 System Administrator

Can configure cameras, AI settings, storage, users, retention, and system-wide behavior.

### 5.2 Security / Monitoring Operator

Monitors the CCTV wall, receives alerts, opens incident clips, acknowledges incidents, and submits review results.

### 5.3 Supervisor / Investigator

Reviews incident history, confirms or rejects incidents, adds notes, exports reports, and audits prior decisions.

### 5.4 Viewer / Read-Only User

Can view live feeds and approved incident records but cannot alter incident classification.

---

## 6. User Stories

### Monitoring

- As a monitoring operator, I want to see all active cameras on one screen so I can quickly understand the current environment.
- As an operator, I want a camera to visually indicate when AI detects a possible violent event so I can immediately investigate it.
- As an operator, I want to open the affected camera in a larger view without leaving the monitoring screen.

### Detection

- As the system, I want to sample frames from each camera so that continuous video can be analyzed without running inference on every frame.
- As the system, I want to combine multiple consecutive predictions so that one incorrect frame does not immediately create an incident.
- As an administrator, I want to configure sensitivity per camera so that areas with frequent motion do not create excessive false alerts.

### Incident clipping

- As the system, I want to retain footage from several seconds before the first detection so the incident has useful context.
- As the system, I want to continue recording after the last detection so the operator can see what happened after the altercation.
- As an operator, I want the incident clip to be available from the alert screen.

### Review

- As a reviewer, I want to mark an AI detection as false positive / not violence.
- As a reviewer, I want to confirm a detection as violence.
- As a reviewer, I want to mark an incident as needing further review.
- As a reviewer, I want to add notes explaining why an alert was accepted or rejected.

### Reporting

- As a supervisor, I want to search previous incidents by date, camera, status, and classification.
- As a supervisor, I want to see how many suspected and confirmed incidents occurred over a selected period.
- As an administrator, I want false positives preserved as feedback so the detection system can be improved later.

---

## 7. Functional Requirements

### FR-01 — Camera Management

The system shall allow an administrator to:

- Add a camera.
- Edit camera name and location.
- Configure RTSP stream URL.
- Enable or disable AI processing.
- Set per-camera detection sensitivity.
- Set per-camera sampling rate.
- Set recording buffer duration.
- Set post-event recording duration.
- Test camera connectivity.
- View last-seen timestamp and connection status.

Each camera shall have a unique internal camera ID.

### FR-02 — Live CCTV Wall

The monitoring dashboard shall display cameras in a grid layout.

Each camera tile shall show:

- Camera name
- Location
- Live video
- Connection state
- AI processing state
- Latest AI status
- Optional FPS / processing health
- Alert indicator
- Last detected event time

A camera with an active incident shall be visually highlighted.

### FR-03 — CCTV Stream Ingestion

The system shall ingest camera feeds using RTSP or another supported network-video source.

The ingestion service shall maintain a rolling recording buffer independently from AI inference so that an event can include footage that occurred before detection.

Recommended initial architecture:

```text
RTSP Camera
   ├──→ Live Stream / Browser Playback
   ├──→ Rolling Buffer
   └──→ AI Frame Sampler
```

The system shall detect stream failures and expose camera health to operators.

### FR-04 — Frame Sampling

The AI processing service shall not be required to infer on every camera frame.

Per-camera sampling should be configurable, for example:

- 1 frame/second
- 2 frames/second
- 4 frames/second
- Custom value

The final sampling rate shall be selected using measured accuracy and hardware benchmarks.

### FR-05 — AI Prediction

For each sampled frame, the AI service shall produce at minimum:

- Camera ID
- Timestamp
- Predicted label
- Confidence/similarity score
- Model version

The system shall preserve raw frame predictions for diagnostics, but the UI shall primarily present aggregated event information.

### FR-06 — Violence Event Aggregation

The system shall prevent a single anomalous frame from creating a high-priority incident.

A configurable event rule should use a combination of:

- Minimum confidence
- Number of positive predictions
- Percentage of positive predictions within a time window
- Minimum event duration
- Cooldown period

Example initial rule:

```text
Within a rolling 6-second window:

If >= 60% of sampled frames are classified as a violence-related label
AND
at least 3 positive predictions occur
AND
average confidence >= configured threshold

→ Create Suspected Violence Incident
```

This rule is an initial product specification and must be tuned using the actual CCTV environment.

### FR-07 — Detection Categories

The product shall use normalized incident categories rather than directly exposing every raw model prompt.

Suggested normalized categories:

| Category | Meaning |
|---|---|
| Suspected Fight | Physical altercation / fighting-like scene |
| Suspected Physical Violence | Possible assault or harmful physical interaction |
| Suspected Bullying | Possible repeated/aggressive physical interaction in a school context |
| Other Violence | Violence-related model output not mapped to the main categories |
| Non-Violent | Normal scene / no violence detected |
| Unknown | Model confidence is too low or scene is ambiguous |

Important: **Bullying shall not be treated as reliably detected solely because the model outputs “fight.”** Bullying generally requires context that a single frame cannot establish. The MVP should therefore call these incidents **Suspected Violence** or **Suspected Bullying** until human review confirms the classification.

### FR-08 — Alert Creation

When the event aggregator crosses the configured trigger condition, the system shall create an incident alert containing:

- Incident ID
- Camera
- Location
- Detection start time
- Detection end time when known
- Trigger label
- Peak confidence
- Average confidence
- Severity
- Incident status
- Clip generation status

### FR-09 — Alert Severity

Initial severity levels:

| Severity | Meaning |
|---|---|
| Critical | Strong, sustained violence detection |
| High | Strong suspected violence |
| Medium | Possible violence requiring review |
| Low | Weak/ambiguous detection |

The MVP may initially generate alerts only for Medium and above.

### FR-10 — Alert Notification

A new alert shall produce:

- Visual alert on dashboard
- Camera tile highlight
- Alert sound for configured severity
- Notification entry in the alert queue

Optional future notifications:

- Email
- SMS
- Push notification
- Messaging integrations

### FR-11 — Automatic Video Clipping

Every triggered incident shall attempt to generate an incident clip.

The clip shall contain:

```text
[PRE-EVENT BUFFER] + [DETECTED EVENT] + [POST-EVENT BUFFER]
```

Recommended initial values:

- Pre-event: 10 seconds
- Post-event: 10 seconds

These values must be configurable per system or camera.

The clip should preserve the native CCTV timestamp where available and include a generated incident timestamp in metadata.

### FR-12 — Clip Generation State

The incident shall expose clip status:

- Pending
- Processing
- Ready
- Failed
- Deleted due to retention policy

If clip generation fails, the incident record shall remain available for investigation and the failure shall be logged.

### FR-13 — Incident Review

The incident review screen shall display:

- Incident clip
- Camera name and location
- Date/time
- Detection category
- Confidence information
- Timeline of AI predictions
- Incident severity
- Operator/reviewer status
- Notes
- Review history

### FR-14 — Human Classification

An authorized reviewer shall be able to classify an incident as:

1. **Confirmed Violence**
2. **False Positive / Not Violence**
3. **Needs Review**

The system shall require a review reason or optional note for false positives and confirmed incidents according to administrator configuration.

### FR-15 — False Positive Flagging

The system shall explicitly support false-positive feedback.

When the reviewer selects **False Positive / Not Violence**, the system shall store:

- Review result
- Reviewer
- Review timestamp
- Reason/category
- Optional notes
- Incident clip reference
- AI label(s)
- AI confidence values
- Model version

Suggested false-positive reasons:

- Sports / playful physical activity
- Hugging / horseplay
- Crowd movement
- Camera blur
- Lighting issue
- Occlusion
- Sudden camera movement
- Non-violent scene misclassified
- Other

### FR-16 — Confirmed Violence Review

For a confirmed incident, the reviewer may optionally record:

- Incident type
- Approximate number of people involved
- Location subtype
- Whether immediate intervention occurred
- Whether further investigation is required
- Notes

The system must not require the operator to identify individuals in the MVP.

### FR-17 — Incident History

The system shall maintain historical incident records.

The history page shall support:

- Date range filtering
- Camera filtering
- Location filtering
- Incident status filtering
- Severity filtering
- Review classification filtering
- Search by incident ID
- Sorting by newest/oldest/highest severity

### FR-18 — Incident Timeline

Each incident shall show a chronological timeline containing:

- AI detection started
- Alert created
- Clip generation started
- Clip became available
- Alert acknowledged
- Incident classified
- Notes added
- Incident closed

### FR-19 — Reports

The system shall provide summary reports for a selected date range.

Initial report metrics:

- Total AI alerts
- Confirmed violence
- False positives
- Needs review
- Alerts by camera
- Alerts by date
- Alerts by severity
- Average confidence of confirmed incidents
- False-positive rate
- Detection volume over time

### FR-20 — Export

Authorized users shall be able to export incident metadata in CSV/PDF format.

Video clips shall remain separate files and may be downloaded by authorized users.

### FR-21 — Audit Trail

The system shall record who performed important actions, including:

- Camera changes
- AI configuration changes
- Incident acknowledgment
- Incident classification
- Incident note changes
- Clip deletion
- User/role changes

### FR-22 — Video Retention

The administrator shall configure retention policies separately for:

- Rolling raw CCTV buffer
- Incident clips
- False-positive clips
- Confirmed incident clips

Incident clips should have a longer retention period than ordinary rolling footage.

### FR-23 — System Health

The dashboard shall expose:

- Camera online/offline state
- AI worker status
- Queue backlog
- Average inference latency
- Clip generation backlog
- Storage usage
- Database health
- Last successful frame received per camera

---

## 8. Dashboard Requirements

### 8.1 Main Monitoring Dashboard

Suggested layout:

```text
┌────────────────────────────────────────────────────────────────────┐
│ CCTV SENTINEL      Cameras: 12   Alerts: 2   AI: Healthy   Storage │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│ ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│ │ CAMERA 01     │  │ CAMERA 02     │  │ CAMERA 03     │           │
│ │ [LIVE VIDEO]  │  │ [LIVE VIDEO]  │  │ [LIVE VIDEO]  │           │
│ │ Normal        │  │ !! VIOLENCE   │  │ Normal        │           │
│ └───────────────┘  └───────────────┘  └───────────────┘           │
│                                                                    │
│ ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│ │ CAMERA 04     │  │ CAMERA 05     │  │ CAMERA 06     │           │
│ │ [LIVE VIDEO]  │  │ [LIVE VIDEO]  │  │ [OFFLINE]     │           │
│ │ Normal        │  │ Normal        │  │ Connection err│           │
│ └───────────────┘  └───────────────┘  └───────────────┘           │
│                                                                    │
├──────────────────────── ACTIVE ALERTS ─────────────────────────────┤
│ 11:42:18  CAMERA 02  Suspected Fight  High  [OPEN] [ACKNOWLEDGE] │
│ 11:37:02  CAMERA 09  Violence        Med   [OPEN] [ACKNOWLEDGE] │
└────────────────────────────────────────────────────────────────────┘
```

### 8.2 Incident Review Screen

```text
┌─────────────────────────────────────────────────────────────┐
│ Incident #INC-2026-00128                                   │
├──────────────────────────────┬──────────────────────────────┤
│                              │ Camera: Hallway 2            │
│      [ INCIDENT CLIP ]       │ Location: Building A         │
│                              │ Severity: HIGH               │
│                              │ AI: Suspected Fight          │
│                              │ Peak: 0.79                   │
│                              │ Status: Awaiting Review      │
│                              │                              │
│                              │ [CONFIRMED VIOLENCE]         │
│                              │ [FALSE POSITIVE]             │
│                              │ [NEEDS REVIEW]               │
├──────────────────────────────┴──────────────────────────────┤
│ AI Timeline                                                 │
│ 11:42:12  Normal  0.19                                      │
│ 11:42:14  Fight   0.51                                      │
│ 11:42:16  Fight   0.68                                      │
│ 11:42:18  Fight   0.79  ← EVENT                             │
│ 11:42:20  Fight   0.72                                      │
│ 11:42:22  Normal  0.24                                      │
├─────────────────────────────────────────────────────────────┤
│ Review Notes: [__________________________________________]   │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Incident State Machine

```text
                 ┌──────────────┐
                 │ AI DETECTED  │
                 └──────┬───────┘
                        ↓
                ┌───────────────┐
                │ ALERT CREATED │
                └──────┬────────┘
                       ↓
              ┌──────────────────┐
              │ CLIP PROCESSING  │
              └────────┬─────────┘
                       ↓
               ┌─────────────┐
               │ AWAIT REVIEW│
               └──────┬──────┘
          ┌────────────┼─────────────┐
          ↓            ↓             ↓
 ┌────────────────┐ ┌──────────────┐ ┌───────────────┐
 │CONFIRMED       │ │FALSE POSITIVE│ │NEEDS REVIEW   │
 │VIOLENCE        │ │/NOT VIOLENCE │ │               │
 └────────────────┘ └──────────────┘ └───────┬───────┘
                                             ↓
                                      Final classification
```

---

## 10. Technical Architecture

### 10.1 Recommended High-Level Architecture

```text
                         ┌───────────────────────┐
                         │      CCTV Cameras     │
                         │      RTSP Streams     │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │   Video Ingestion     │
                         │ FFmpeg / OpenCV       │
                         └───────┬─────────┬─────┘
                                 │         │
                      Live/Buffer │         │ Sampled Frames
                                 │         │
                                 ▼         ▼
                       ┌─────────────┐  ┌───────────────┐
                       │ Rolling     │  │ AI Inference  │
                       │ Video Buffer│  │ Service       │
                       └──────┬──────┘  │ Python        │
                              │         │ CLIP baseline │
                              │         └───────┬───────┘
                              │                 │
                              │                 ▼
                              │       ┌──────────────────┐
                              │       │ Temporal Event   │
                              │       │ Aggregator       │
                              │       └────────┬─────────┘
                              │                │
                              ▼                ▼
                       ┌────────────────────────────┐
                       │ Incident / Clip Service   │
                       └──────────────┬─────────────┘
                                      │
                 ┌────────────────────┼───────────────────┐
                 ▼                    ▼                   ▼
         ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
         │ PostgreSQL   │    │ Video Storage│    │ Redis / Queue│
         │ Metadata     │    │ Clips/Buffers│    │ Jobs/Events  │
         └──────┬───────┘    └──────────────┘    └──────────────┘
                │
                ▼
         ┌─────────────────────────────────┐
         │ Central Monitoring Web App      │
         │ Dashboard / Alerts / Reports    │
         └─────────────────────────────────┘
```

### 10.2 Suggested Application Stack

#### Frontend

- Next.js / React
- TypeScript
- Tailwind CSS
- Real-time dashboard updates through WebSocket/SSE

#### Backend / Application API

- Python 3.x
- Flask
- SQLAlchemy
- Flask-Migrate / Alembic
- Flask-JWT-Extended
- Flask-SocketIO
- PostgreSQL
- Redis

#### AI / Video Processing

- Python
- PyTorch
- OpenAI CLIP / repository model
- OpenCV
- FFmpeg
- RTSP camera streams

The Flask backend manages cameras, incidents, alerts, users, reports, and system configuration. Long-running camera inference and clip-generation workers should run as separate processes/services and communicate through Redis so video processing does not block the API.


#### Storage

- Local disk for MVP, or NAS/object storage for multi-camera deployments
- PostgreSQL for metadata only
- Video clips stored outside the database

### 10.3 Service Boundaries

The AI service should be separated from the main web application.

Reasons:

- AI inference has different CPU/GPU requirements.
- AI workers may scale independently.
- A model crash should not bring down the central dashboard.
- Model versions can be upgraded independently.
- Different AI implementations can be tested against the same event API.

---

## 11. Suggested Database Model

### cameras

- id
- name
- location
- stream_url_encrypted
- enabled
- ai_enabled
- sampling_rate
- sensitivity
- pre_buffer_seconds
- post_buffer_seconds
- status
- last_seen_at
- created_at
- updated_at

### ai_models

- id
- name
- version
- runtime
- configuration_json
- active
- created_at

### ai_predictions

- id
- camera_id
- ai_model_id
- captured_at
- label
- normalized_category
- confidence
- processing_latency_ms
- created_at

### incidents

- id
- public_id
- camera_id
- ai_model_id
- category
- raw_ai_label
- severity
- peak_confidence
- average_confidence
- started_at
- detected_at
- ended_at
- status
- clip_status
- clip_path
- thumbnail_path
- acknowledged_at
- acknowledged_by
- created_at
- updated_at

### incident_reviews

- id
- incident_id
- reviewer_id
- classification
- reason
- notes
- reviewed_at

### incident_events

- id
- incident_id
- event_type
- event_at
- metadata_json
- actor_id
- created_at

### users

- id
- name
- email
- password_hash
- role
- active
- created_at
- updated_at

### audit_logs

- id
- user_id
- action
- entity_type
- entity_id
- metadata_json
- created_at

### system_settings

- id
- key
- value_json
- updated_by
- updated_at

---

## 12. AI Detection Logic

### 12.1 Baseline Model Integration

The existing model uses text prompts as candidate labels and returns the highest-similarity label if similarity meets the configured threshold; otherwise it returns `Unknown`.

For the school/CCTV use case, the baseline configuration should be replaced or extended with environment-specific labels.

Example labels for a school deployment:

```yaml
labels:
  - "students walking in a school hallway"
  - "students talking in a school hallway"
  - "students playing"
  - "students running"
  - "students wrestling or fighting"
  - "a physical fight between students"
  - "physical violence in a school hallway"
  - "physical assault in a school area"
  - "bullying involving physical aggression"
  - "crowd of students"
  - "empty hallway"
```

These prompts are **not a guarantee that the base model can accurately recognize bullying**. They are a starting point for experimentation and must be validated against local CCTV footage.

### 12.2 Temporal Aggregation

The event engine should maintain a per-camera rolling state.

Example:

```text
Camera 04

11:42:10  normal              0.21
11:42:12  fight               0.43
11:42:14  fight               0.62
11:42:16  fight               0.75  ← crossing trigger
11:42:18  fight               0.71
11:42:20  fight               0.69
11:42:22  normal              0.23

                ↓

Event start = 11:42:12
Event peak  = 11:42:16
Event end   = 11:42:22
```

The incident clip should therefore include footage beginning before 11:42:12 and ending after 11:42:22.

### 12.3 Hysteresis / Cooldown

To reduce alert spam:

- Trigger when confidence/activity crosses the positive threshold.
- Keep the incident active while positive predictions continue.
- Close the event only after a negative period.
- Do not create a second incident during a configurable cooldown unless a new event is sufficiently separated in time.

Suggested MVP defaults:

- Trigger window: 6 seconds
- Positive ratio: 60%
- Minimum positive predictions: 3
- Post-detection quiet period: 5 seconds
- Duplicate-event cooldown: 30 seconds

These values are tunable and should be treated as starting configuration rather than validated accuracy claims.

---

## 13. Video Buffering and Clip Generation

### Recommended implementation

Each camera should maintain a rolling buffer using short video segments, for example:

```text
Camera 01

[10:00:00–10:00:05]
[10:00:05–10:00:10]
[10:00:10–10:00:15]
[10:00:15–10:00:20]  ← detection occurs here
[10:00:20–10:00:25]
[10:00:25–10:00:30]
```

When an event begins, the clip service should combine:

```text
Previous segments
      +
Event segments
      +
Post-event segments
      ↓
Incident clip
```

### Why a rolling buffer is required

If the system begins recording only after the AI detects violence, the first seconds of the incident can be lost because detection occurs after the action has already started.

---

## 14. Real-Time Alert Workflow

```text
1. Camera sends RTSP stream.
2. Ingestion service receives frames.
3. Rolling recorder continuously stores short segments.
4. AI worker samples frames.
5. AI worker returns label + confidence.
6. Temporal aggregator updates camera state.
7. Trigger condition is crossed.
8. Incident record is created.
9. Active alert is broadcast to dashboard.
10. Clip service gathers pre-event buffer.
11. Clip service waits for post-event window.
12. Clip is finalized.
13. Operator acknowledges alert.
14. Reviewer watches the clip.
15. Reviewer selects classification.
16. System saves review + audit event.
17. Incident becomes part of history/reporting.
```

---

## 15. False Positive / Feedback Workflow

False-positive handling is a first-class part of the product.

```text
AI Alert
   ↓
Operator Review
   ↓
Is this violence?
  /          \\
YES           NO
 ↓             ↓
Confirmed      False Positive
 ↓             ↓
Store case     Store feedback
               + reason
               + clip
               + model output
```

False-positive records should remain searchable rather than being deleted, because they are useful for evaluating and improving the model.

### Future model-learning dataset

The system may later support an export pipeline:

```text
Confirmed violence clips
          ├── Positive dataset
          │
          └── Model training/evaluation

False-positive clips
          └── Hard-negative dataset
```

This allows the actual deployment environment to become the source of model improvement.

---

## 16. Reporting and Analytics

### Main report dashboard

Suggested KPIs:

```text
┌────────────────┬────────────────┬────────────────┬────────────────┐
│ Total Alerts   │ Confirmed      │ False Positive │ Needs Review  │
│     128        │       41       │       73       │      14        │
└────────────────┴────────────────┴────────────────┴────────────────┘
```

Charts:

- Incidents by day
- Incidents by hour
- Incidents by camera
- Incidents by category
- Incidents by severity
- Confirmed vs false positive
- Detection confidence distribution
- Camera availability / downtime

The reports page should make it easy to identify cameras that generate unusually high false-positive rates.

---

## 17. Non-Functional Requirements

### Performance

- Dashboard should update active alerts in near real time.
- Alert creation should not depend on page refresh.
- AI processing should run asynchronously from the web request cycle.
- Clip generation should run as a background job.

### Reliability

- Camera disconnection must not crash the system.
- AI worker failure must be visible to operators.
- Clip generation failure must not delete the incident record.
- Queued processing shall recover after worker restart where feasible.

### Scalability

The system should be designed so that additional AI workers can be added when camera count increases.

```text
10 Cameras
   ↓
1–2 AI Workers

50 Cameras
   ↓
Multiple AI Workers
```

The exact worker count must be based on measured inference throughput for the selected hardware and model.

### Security

- Authentication required for management and incident review.
- Role-based permissions.
- RTSP credentials encrypted at rest.
- HTTPS for web access.
- Audit logs for sensitive operations.
- Video files protected from public access.
- Signed/authorized clip URLs or application-mediated downloads.

### Privacy

The system should collect only data needed for security and incident review.

The MVP should avoid automatic face recognition or identity matching. Incident reports should refer to the camera/location/time rather than automatically naming people.

Retention and access policies should follow the deploying institution's privacy, security, and legal requirements.

---

## 18. Camera Health Monitoring

Each camera shall have a health state:

```text
ONLINE
DEGRADED
OFFLINE
DISABLED
```

Health checks should monitor:

- RTSP connectivity
- Last frame received
- Frame rate
- Stream decode errors
- AI worker assignment
- AI processing latency

An offline camera must be clearly differentiated from a camera that is online but not being analyzed by AI.

---

## 19. Configuration Requirements

Global settings:

- Default AI threshold
- Default sampling rate
- Default pre-event buffer
- Default post-event buffer
- Default cooldown
- Alert sound enabled/disabled
- Notification policy
- Storage retention
- Maximum storage usage
- Time zone

Per-camera overrides:

- AI enabled
- Detection sensitivity
- Sampling rate
- Labels/profile
- Pre-event buffer
- Post-event buffer
- Alert severity threshold

---

## 20. API Requirements

### Camera APIs

```text
GET    /api/cameras
POST   /api/cameras
GET    /api/cameras/{id}
PUT    /api/cameras/{id}
DELETE /api/cameras/{id}
POST   /api/cameras/{id}/test
```

### Incident APIs

```text
GET    /api/incidents
GET    /api/incidents/{id}
POST   /api/incidents/{id}/acknowledge
POST   /api/incidents/{id}/review
GET    /api/incidents/{id}/clip
GET    /api/incidents/{id}/timeline
```

### Report APIs

```text
GET /api/reports/incidents
GET /api/reports/summary
GET /api/reports/cameras
GET /api/reports/false-positives
```

### AI service APIs

```text
GET  /health
GET  /models
POST /predict
POST /predict/batch
POST /workers/register
```

The exact interface can change during implementation, but the web application should not need direct knowledge of the AI model internals.

---

## 21. Real-Time Event Contract

Suggested WebSocket/SSE event:

```json
{
  "type": "incident.created",
  "incident_id": "INC-2026-00128",
  "camera_id": 4,
  "camera_name": "Hallway 2",
  "category": "suspected_fight",
  "severity": "high",
  "confidence": 0.79,
  "detected_at": "2026-10-05T11:42:18+08:00"
}
```

Additional event types:

```text
camera.online
camera.offline
incident.created
incident.updated
incident.acknowledged
incident.clip_ready
incident.reviewed
ai.worker.online
ai.worker.offline
```

---

## 22. MVP Acceptance Criteria

The MVP is considered functional when all of the following are demonstrated:

### Camera

- At least 4 RTSP cameras can be configured.
- The dashboard shows all configured cameras.
- Camera status changes to offline when the stream is unavailable.

### AI

- The AI worker can receive frames from a configured camera.
- The configured model returns a label and confidence.
- The system stores prediction timestamps.
- Multiple predictions are aggregated into an incident decision.

### Alerts

- A sustained violence pattern creates exactly one incident instead of repeated alerts every frame.
- The dashboard displays the alert without requiring refresh.
- A new alert produces an audible/visual notification when enabled.

### Video clipping

- The system preserves a pre-event buffer.
- The system records post-event footage.
- A triggered incident produces a playable clip.
- Clip creation status is visible.

### Review

- Reviewer can mark an event as Confirmed Violence.
- Reviewer can mark an event as False Positive / Not Violence.
- Reviewer can choose a false-positive reason.
- Reviewer can add notes.
- Review action is recorded in the audit log.

### History

- Reviewed incidents appear in incident history.
- Users can filter by camera and date.
- Reports show confirmed vs false-positive events.

---

## 23. Suggested Development Phases

### Phase 1 — CCTV Connectivity

- Camera CRUD
- RTSP test
- Multi-camera ingestion
- Camera health
- Basic live wall

### Phase 2 — AI Integration

- Python AI service
- Model wrapper
- Frame sampler
- Prediction storage
- Per-camera model configuration

### Phase 3 — Event Detection

- Temporal aggregation
- Trigger thresholds
- Hysteresis
- Incident creation
- Real-time dashboard alerts

### Phase 4 — Video Evidence

- Rolling buffers
- Clip extraction
- Post-event recording
- Clip storage
- Incident playback

### Phase 5 — Review and History

- Incident review
- Confirmed / false-positive workflow
- Notes
- Search/filter
- Reports
- Audit logs

### Phase 6 — Model Improvement

- Feedback dataset
- False-positive analysis
- Environment-specific labels
- Threshold calibration
- Benchmarking
- Replacement/upgrade of baseline model if necessary

---

## 24. Risks and Mitigations

### Risk: False positives

**Cause:** Normal activities may look violent in a single frame.

**Mitigation:** Temporal aggregation, camera-specific thresholds, human review, and false-positive feedback collection.

### Risk: False negatives

**Cause:** Camera angle, occlusion, low resolution, motion blur, or unusual behavior may prevent detection.

**Mitigation:** Multiple-camera coverage, model evaluation using local footage, better camera placement, and future temporal models.

### Risk: Bullying cannot be reliably inferred from one frame

**Cause:** Bullying is contextual and can involve repeated behavior, power imbalance, duration, and interactions that a frame-level model cannot establish.

**Mitigation:** Treat AI output as a suspicion signal. Use incident review and, in later versions, investigate temporal person/action tracking and multi-event context.

### Risk: High CPU/GPU load

**Cause:** Multiple concurrent video streams are expensive to decode and analyze.

**Mitigation:** Sample frames rather than process every frame, separate ingestion from inference, batch work where supported, and scale AI workers based on benchmarks.

### Risk: Lost pre-event footage

**Cause:** AI detection happens after an event has begun.

**Mitigation:** Continuous rolling video buffer per camera.

### Risk: Storage growth

**Cause:** Continuous CCTV recording and incident clips consume large amounts of storage.

**Mitigation:** Short rolling segments, configurable retention, incident-only long-term retention, and storage monitoring.

---

## 25. Model Evaluation Plan

Before production deployment, the team shall create a validation set using the actual CCTV environment.

The evaluation set should contain:

- Normal school activity
- Walking
- Running
- Sports
- Playful physical contact
- Crowds
- Hallway congestion
- Actual fights/violent events
- Different lighting conditions
- Camera angles
- Low-resolution footage
- Partial occlusion

The model should be evaluated using at least:

- Precision
- Recall
- F1 score
- False-positive rate
- False-negative rate
- Detection latency
- Per-camera performance

### Key product metric

For the MVP, a major operational metric should be:

**False alerts per camera per hour**

A system that detects everything but generates unusable alert volume should not be considered successful.

---

## 26. Future Enhancements

### AI / Computer Vision

- Temporal violence model instead of frame-only classification
- Object/person detection
- Person tracking
- Action recognition
- Pose estimation
- Automatic event localization within the frame
- Multi-camera incident correlation
- Improved bullying-context analysis
- Model ensembles
- Hardware acceleration

### Monitoring

- Map view of cameras
- PTZ camera controls
- Automatic camera focus on active incident
- Alarm panel integration
- Mobile monitoring application

### Notifications

- SMS
- Email
- Push notifications
- Local siren / alarm integration
- Messaging platforms

### Investigation

- Bookmark moments within clips
- Add multiple review notes
- Attach documents
- Case management
- Evidence export package
- Incident relationships

### Analytics

- Heatmap of incident locations
- Time-of-day patterns
- Recurring false-positive zones
- Camera performance scoring
- AI confidence calibration dashboard

---

## 27. Product Principle

The central design principle is:

> **AI detects; humans decide.**

The system should aggressively reduce the amount of CCTV footage that operators must watch while keeping final incident classification under authorized human review.

The product should therefore preserve both sides of the record:

```text
AI says:      POSSIBLE VIOLENCE
Human says:   CONFIRMED VIOLENCE

or

AI says:      POSSIBLE VIOLENCE
Human says:   FALSE POSITIVE / NOT VIOLENCE
```

Both outcomes are valuable because confirmed events support security operations while false positives improve future model performance.

---

## 28. Initial MVP Definition

The first working release should focus on one practical loop:

```text
RTSP Camera
   ↓
Frame Sampling
   ↓
Violence AI
   ↓
Temporal Aggregation
   ↓
Alert
   ↓
Pre + Post Event Clip
   ↓
Human Review
   ↓
Confirmed / False Positive
   ↓
Incident History
```

Once this loop is stable for a small number of cameras, the system can be expanded to more cameras, stronger models, richer reports, and more advanced bullying analysis.
