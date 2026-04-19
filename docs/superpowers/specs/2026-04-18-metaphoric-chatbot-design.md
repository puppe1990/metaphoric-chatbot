# Metaphoric Chatbot MVP Design

## Summary

Build a web app that helps users either receive a metaphorical response about a personal issue or learn to construct their own metaphors through guided chat. The MVP will be a text-only web app backed by a Python agent service using Deep Agents, Groq as the initial model provider, SQLite for persistence, and anonymous sessions addressable by unique links.

The product should feel intentional and emotionally intelligent without drifting into mystical vagueness or heavy-handed therapeutic posturing. The app is not a clinical therapy product. It is a metaphor-centered reflection and coaching tool inspired by Ericksonian indirect language, Bandler-style sensory structure, and therapeutic metaphor patterns discussed in the selected books.

For the "Receive a Metaphor" path specifically, the experience should optimize for speed and a sense of magic rather than overt analysis. The user should feel that the product "got it" quickly and answered with precision, not that it walked them through a therapeutic intake form.

## Product Goals

- Provide a low-friction guided chat experience for metaphor generation and metaphor training.
- Use metaphor as a practical tool for reflection, reframing, and symbolic insight.
- Support two distinct user outcomes through one shared engine:
  - Receive a metaphor crafted from the user's input.
  - Learn how to build a stronger metaphor through guided coaching.
- Keep the provider layer swappable so Groq can be replaced or complemented later.
- Persist chat sessions without requiring authentication.

## Non-Goals

- No voice or audio in the MVP.
- No Telegram integration in the MVP.
- No long-term cross-session memory or profile learning in the MVP.
- No diagnosis, treatment claims, or simulation of licensed psychotherapy.
- No multi-user collaboration or social sharing features.

## Core User Modes

### Mode 1: Receive a Metaphor

The user describes a problem in one simple sentence. The system should infer as much as possible internally, ask at most one short clarifying question only when ambiguity would materially change the output, and then return three short metaphor options for the user to choose from. After the user chooses one, the system refines only that direction.

### Mode 2: Build My Metaphor

The user describes a problem and is guided step by step to convert abstraction into image, mechanism, scene, object, or process. The system acts as a coach rather than a generator-first assistant. It asks short questions, critiques weak metaphors, and helps the user rewrite toward a stronger version.

## Experience Principles

- Chat-first, but guided rather than fully open-ended.
- Always push from abstract description toward concrete image or symbolic mechanism.
- Prefer short prompts and short assistant turns.
- Do not over-explain the metaphor unless the user asks.
- Avoid explicit moral-of-the-story framing.
- Keep the tone calm, precise, and slightly evocative.
- Treat metaphor as a structured transformation tool, not decorative language.
- In the "Receive a Metaphor" path, hide internal reasoning and symbolic analysis by default.
- Favor immediate output over multi-step collection when a good answer can be inferred.
- Make the first payoff concrete: the user should receive options to pick from, not a diagnostic summary.

## Source-Informed Behavioral Principles

The system prompt and coaching logic should reflect these ideas:

- From Ericksonian influence:
  - indirectness can reduce resistance
  - stories can work without explicit explanation
  - suggestion should feel permissive rather than authoritarian
- From Bandler-style influence:
  - metaphorical language often maps to sensory structure
  - shifts in internal representation can alter felt experience
  - user language should be treated as process clues, not just content
- From therapeutic metaphor traditions:
  - the symptom or problem can be reframed as a symbolic pattern
  - a metaphor should include tension, movement, and reorganization
  - a useful metaphor is concrete, memorable, and structurally relevant

These are product design influences, not truth claims about psychology.

## Primary User Flow

### Entry

The landing page presents two clear choices:

- Receive a metaphor
- Build my metaphor

Each option includes a one-sentence explanation and a short example.

### Session Creation

When the user starts, the app creates an anonymous persisted session and assigns a unique link such as `/c/<token>`. The frontend also stores the session token locally so the same browser can restore recent work without requiring the user to manually save the link.

### Guided Chat

The chat UI presents a focused guided experience. Messages appear conversationally, but the app keeps internal state and does not allow the conversation to drift into arbitrary free chat unless later versions deliberately support that.

### Output and Refinement

The user receives a final metaphor, short story, symbolic mapping, or coached rewrite. The user can then refine the result through lightweight actions such as:

- make it softer
- make it deeper
- make it more concrete
- make it shorter
- give me three versions
- explain why this works

## Receive a Metaphor Flow Redesign

This flow is the main place where "Deep Agents" can be overused in a way that hurts the product. The user-facing experience should be minimal, while the internal agentic work happens behind the scenes.

### Product Goal for This Flow

- Deliver the first useful result in one turn whenever possible.
- Make the result feel specific rather than generically poetic.
- Let the user choose among options instead of forcing the system to overcommit to one interpretation too early.
- Preserve refinement depth after the initial moment of magic.

### User-Facing Flow

1. Entry prompt:
   `Descreva o problema em uma frase simples.`
2. System attempts immediate generation from that input.
3. If and only if the input is materially ambiguous, ask one short style or direction question such as:
   - `Você quer algo mais direto ou mais poético?`
   - `Você quer algo mais calmo ou mais firme?`
4. Return three short metaphor options labeled `A`, `B`, and `C`.
5. Ask the user to choose the one that fits best.
6. After selection, allow lightweight refinement of the chosen option only.

### Explicitly Rejected UX Pattern

Do not expose an intermediate "symbolic structure extracted from your input" panel in the default path. It slows the experience, feels inflated, and reduces the sense of precision. Internal extraction can still exist for orchestration and evaluation, but it should remain hidden unless a future debug or teaching mode needs it.

### Example UX Contract

Assistant first payoff:

`Escolha a que mais encaixa em você agora.`

- `A. ...`
- `B. ...`
- `C. ...`

Refinement options after selection:

- `mais curta`
- `mais concreta`
- `mais profunda`
- `mais poética`
- `mais direta`

## State Model

The conversation is driven by an explicit state machine. This prevents the assistant from becoming vague and makes provider-swapping safer.

### Receive a Metaphor States

- `intake_problem`
- `optional_clarifier`
- `generate_candidates`
- `present_choices`
- `refine_selected`

### Build My Metaphor States

- `intake_problem`
- `identify_core_conflict`
- `offer_symbolic_fields`
- `user_selects_symbol`
- `user_attempt`
- `coach_feedback`
- `rewrite_together`

The state machine is persisted in the database and returned in API responses so the frontend can render progress consistently.

### Receive a Metaphor State Semantics

- `intake_problem`
  - collect the user's initial one-sentence description
- `optional_clarifier`
  - ask one short question only if ambiguity is high and materially affects output quality
- `generate_candidates`
  - run hidden extraction and produce several internal candidates, then rank and select three
- `present_choices`
  - return exactly three user-facing options that are distinct in image and phrasing
- `refine_selected`
  - refine only the chosen option based on user taste signals

## Functional Requirements

### Frontend

- Render a landing page with the two modes.
- Create or resume an anonymous session.
- Display a chat interface with message history and a clear current mode.
- Show lightweight progress labels based on the current state.
- Render structured assistant outputs cleanly when relevant:
  - metaphor choices
  - critique
  - refinement actions
- Allow the user to revisit a session through a unique link.
- For the "Receive a Metaphor" path, render choice chips or buttons for `A`, `B`, and `C` to reinforce fast selection.
- Preserve a text-first fallback so the same contract works in non-enhanced chat clients.

### Backend API

- Create session
- Append user message to session
- Run orchestration for the current state and mode
- Persist structured extraction and outputs
- Return next assistant turn plus updated state
- Support provider/model configuration for the default runtime

### Agent Service

- Orchestrate stateful guided conversation
- Extract symbolic structure from user input
- Generate metaphorical responses
- Coach users on building stronger metaphors
- Apply tone and safety constraints
- Expose a stable interface to the web app
- For the "Receive a Metaphor" path, generate more candidates internally than are shown to the user, then rank for brevity, specificity, emotional fit, and distinctness before returning three.

## Technical Architecture

### High-Level Components

- `Next.js web app`
  - landing page
  - chat UI
  - session restoration by unique link
- `Python API service`
  - FastAPI or equivalent
  - Deep Agents / LangGraph orchestration
  - provider abstraction
- `SQLite database`
  - sessions
  - messages
  - structured extraction
  - generated artifacts
  - settings

### Why Split Web App and Agent Service

Deep Agents is better suited to a Python runtime. Keeping the agentic logic separate from the Next.js app produces a cleaner architecture:

- frontend stays focused on user experience
- agent service owns orchestration and symbolic logic
- provider changes remain isolated
- future channels such as Telegram can reuse the same backend

## Model Provider Strategy

The MVP starts with Groq. The backend must not assume Groq-specific request or response shapes at the product logic layer.

Create a provider adapter interface with capabilities such as:

- `invoke_chat`
- `invoke_structured`
- `stream_chat` if later needed
- model metadata lookup

Future providers can implement the same adapter with minimal changes to orchestration logic.

## Deep Agents Usage

Deep Agents should be used as the runtime harness for agentic orchestration, not as a fully unconstrained general-purpose assistant. The system should define controlled agent roles and tool boundaries.

### Planned Agent Roles

- `MetaphorGeneratorAgent`
  - converts user input and extracted symbolic structure into metaphorical output
- `MetaphorCoachAgent`
  - critiques and improves user-created metaphors
- `ConversationOrchestrator`
  - chooses state transitions and which specialized agent to call

For the "Receive a Metaphor" path, agentic depth should be spent on hidden candidate exploration and ranking, not on asking many user-visible questions or narrating internal structure.

The orchestrator may itself be implemented using LangGraph state transitions with Deep Agents where useful, but the UX contract remains deterministic at the state-machine level.

### Constraints

- Do not expose broad filesystem or shell tools in the user-facing runtime unless there is a clear product need.
- Keep tools narrow and app-specific.
- Prefer structured extraction over freeform hidden reasoning.

## Prompt Architecture

Prompts should be versioned and stored as first-class product assets.

### Prompt Families

- `extractor`
  - derive core conflict, emotional valence, symbolic candidates, degree of ambiguity, and likely directional shift
- `generator`
  - produce multiple short metaphor candidates from extracted structure
- `coach`
  - critique abstraction, cliche, moralizing, weak imagery, and missing movement
- `refiner`
  - rewrite the result in different tones or levels of depth
- `ranker`
  - score generated candidates for brevity, specificity, emotional fit, usefulness, and distinctness

### Prompt Constraints

- no diagnosis
- no claims of clinical efficacy
- no coercive hypnotic framing
- no explicit manipulation tactics
- no overconfident interpretation of the user's unconscious
- use concrete images and mechanisms
- preserve room for user interpretation
- do not expose hidden extraction or chain-of-thought style analysis in the default UX
- make the initial user-facing output short enough to scan instantly
- avoid cliche-heavy symbolic imagery unless directly justified by the user's wording

### Candidate Quality Heuristics

Each candidate in the "Receive a Metaphor" path should be scored against:

- brevity
- specificity
- emotional resonance
- practical usefulness
- memorability
- non-cliche imagery
- distinctness from sibling options

If the top three are too similar, regenerate with an explicit diversity penalty rather than returning variations of the same image.

## Data Model

### sessions

- `id`
- `token`
- `mode`
- `state`
- `title`
- `provider`
- `model`
- `created_at`
- `updated_at`

### messages

- `id`
- `session_id`
- `role`
- `content`
- `step`
- `created_at`

### extractions

- `id`
- `session_id`
- `core_conflict`
- `dominant_emotion`
- `symbolic_field`
- `block_pattern`
- `desired_shift`
- `transformation_type`
- `created_at`
- `updated_at`

### artifacts

- `id`
- `session_id`
- `artifact_type`
- `content`
- `metadata_json`
- `created_at`

### prompt_versions

- `id`
- `name`
- `version`
- `content`
- `is_active`
- `created_at`

### settings

- `id`
- `key`
- `value`
- `updated_at`

### Candidate Metadata

The backend should store lightweight candidate metadata for evaluation and iteration, even if only three options are shown to the user. This metadata can live in `artifacts.metadata_json` in the MVP and should include:

- internal candidate count
- ranking scores
- selected option label
- whether a clarifying question was asked

## Session Strategy

Sessions are anonymous but persisted. Each session has a unique, high-entropy token used in a shareable link. The browser also stores recent session references locally for convenience.

### Requirements

- No login required in the MVP.
- A user can reopen a session via unique link.
- A user on the same browser can resume recent sessions without entering the link.
- Tokens must be hard to guess.
- If a token leaks, anyone with the link can access that session.

This trade-off is acceptable for MVP simplicity, but should be explicit in product language.

## Safety and Product Boundaries

The app should include clear framing that it is a reflective and creative coaching tool, not therapy or crisis support.

### Required Guardrails

- avoid diagnosing mental health conditions
- avoid instructions that intensify distress or encourage dependency
- if the user expresses acute self-harm or crisis content, stop metaphor generation and show a crisis-oriented support response
- avoid positioning the assistant as a licensed therapist
- avoid false claims about hidden meaning or certainty

### Tone Guardrails

- reflective, not mystical
- evocative, not grandiose
- supportive, not clingy
- specific, not pseudo-deep
- concise, not ceremonious

### Cliche Avoidance Guardrail

Avoid overused images by default, especially:

- forest
- fog
- lake
- ocean
- bridge
- labyrinth
- storm
- lighthouse
- mountain
- garden
- flight
- mirror
- river
- horizon

These are not banned absolutely, but the generator should use them only when strongly supported by the user's language or context.

## UI Design Direction

The design should sit in the middle:

- warmer than a utilitarian productivity tool
- cleaner and less mystical than a “healing app”

Visual direction:

- expressive but restrained typography
- symbolic visual cues without occult aesthetics
- soft motion and layered backgrounds
- clear distinction between user text, symbolic extraction, and final metaphor

## MVP Scope

Included:

- landing page
- two guided chat modes
- Groq integration
- Deep Agents backend
- SQLite persistence
- anonymous unique-link sessions
- result refinement actions
- fast choice-based "Receive a Metaphor" flow with 3 options

Excluded:

- auth
- voice
- Telegram
- long-term memory
- user accounts
- advanced analytics dashboard
- symbolic preference learning across sessions

## Testing Strategy

### Unit Tests

- state transition rules
- provider adapter behavior
- token generation
- database persistence logic

### Integration Tests

- start session and complete flow in each mode
- resume session by unique link
- persist structured extraction and artifacts
- provider failure fallback behavior

### Prompt and Output Evaluation

Create a small evaluation set of example inputs to manually review:

- vague problem input
- emotionally loaded but non-crisis input
- abstract input that needs concretization
- user-created weak metaphor that should receive strong coaching

Review outputs for:

- concreteness
- symbolic coherence
- lack of moralizing
- lack of unsafe therapeutic claims
- distinctness between options A/B/C
- perceived immediacy of the first payoff
- low cliche rate

### Product Metrics for This Flow

Track at minimum:

- time to first metaphor response
- percentage of sessions where no clarifier was needed
- option selection rate for A/B/C
- percentage of sessions where the user says none fit
- refinement rate after selection

## Deployment Notes

- Web app can be deployed separately from the Python agent service.
- SQLite is acceptable for the MVP if deployment environment supports persistent disk or mounted storage.
- If the target hosting environment does not support durable SQLite storage well, move to Postgres without changing the product design.

## Open Decisions Resolved

- product tone: middle ground
- primary channel: web app first
- interaction style: guided chat
- output modality: text only
- storage: SQLite
- runtime: Deep Agents
- provider strategy: Groq first, provider-agnostic architecture
- session model: anonymous unique-link sessions with local browser restoration

## Recommended Next Step

Write the implementation plan for:

- repo structure
- frontend app shell
- Python agent service
- SQLite schema
- provider adapter
- chat orchestration
- prompt asset organization
- MVP UI implementation
