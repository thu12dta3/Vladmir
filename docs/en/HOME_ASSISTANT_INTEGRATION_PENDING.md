# Home Assistant integration — pending proposal

**Status:** proposed; not implemented or tested. This page turns the need for the assistant to understand current home state without sending every sensor into model context into a project requirement.

## Problem

A Home Assistant installation may contain many sensors and entities. Adding every state to each message consumes context, increases cost/latency, and can hide the information needed to answer the question. Readings may also be stale, unavailable, or incomplete.

## Desired outcome

When asked about the home, Vladmir should query only the data needed for that question and produce a concise, verifiable, current answer. For example, a question about the living room should query relevant entities in that area rather than attaching the entire inventory.

## Proposed architecture

1. **Explicit local connector:** operator-configured connection to a selected Home Assistant instance. Use a supported official API (REST or WebSocket, to be confirmed during implementation) and store its token outside the repository, in the system secret store when available or a local file with restrictive permissions.
2. **Lightweight catalog:** load areas, names, domains, and entity IDs; do not send every sensor value to the model by default.
3. **On-demand query:** map the question to filters by area, entity type, name, and time period. Fetch only the current states needed and query history only when a trend or comparison is requested.
4. **Compact summary:** group results by room/category, discard attributes unrelated to the question, and enforce item/token limits. A short-lived cache may reduce calls; every displayed datum must retain its read timestamp.
5. **Traceable answer:** state in natural language which areas/entities were queried, the timestamp, and whether an entity was unavailable or stale. Do not claim the state is complete when a query fails.
6. **Separate actions:** first version is read-only. Any service that changes state (lights, locks, climate, alarm, etc.) must require a specific permission and user confirmation; a question about status does not authorize an action.

## Privacy and security

- Disabled by default; no automatic discovery or cloud data transfer.
- Restrict connection to the explicitly configured endpoint. Since Home Assistant is commonly on a private network, implement a dedicated connector with allowlisting and destination validation; do not weaken SSRF protections in general web browsing.
- Keep the token out of Git, prompts, logs, URLs, and error messages.
- Expose separate least-privilege scopes: inventory, current state, and history. Do not request control access for the read-only version.
- Treat entity names, states, and attributes as untrusted data, not instructions to the model or tools.
- Bound entity count, attribute size, history window, timeout, query frequency, and concurrent requests.
- Allow the operator to remove configuration, cache, and associated local data.

## Acceptance criteria

- [ ] The user can configure/disable the local integration; the secret is not versioned or exposed in logs.
- [ ] A room query fetches only relevant entities, and the model request contains a bounded summary rather than the full inventory.
- [ ] A trend query uses a bounded history window and reports the period used.
- [ ] The answer identifies timestamps, unavailable/stale states, and integration failures without inventing readings.
- [ ] Entity names/attributes that look like instructions cannot redirect assistant behavior or trigger tools.
- [ ] Tests cover timeout, invalid token, removed entity, unavailable value, oversized payload, malformed response, and disallowed destination attempts.
- [ ] The first version does not execute control services. If control is added later, each operation has its own scope, clear preview, and confirmation.
- [ ] Integration testing uses a lab instance and synthetic entities before residential use.

## Suggested phases

1. Investigate supported Home Assistant API versions and choose REST or WebSocket based on pagination, history, and events.
2. Implement a read-only connector and configuration/diagnostics UI.
3. Create a lightweight local catalog and selective query by area/domain.
4. Add bounded history, timestamps, and stale-data indicators.
5. Evaluate token budget, latency, and accuracy with synthetic scenarios containing many entities.
6. Discuss device automation only after permission and confirmation review.

## Outside this proposal

- This is not a feature currently available in Vladmir.
- It does not imply unrestricted local-network access or device discovery.
- It does not send the entire home state to the model in every conversation.
- It does not enable home control in the first version.
- It does not promise compatibility with every Home Assistant installation, add-on, integration, or entity.
