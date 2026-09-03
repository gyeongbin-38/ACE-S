# Trust and Security Architecture Protocol

Use only when a trust decision can change boundaries, state access, deployment, or interfaces.

## 1. Model authorization explicitly

For each material operation identify:

`principal → credential/capability → action → resource → authorization decision → enforcement point`

Authentication answers who/what is acting. Authorization answers whether that principal may perform this action on this resource. Do not collapse the two.

## 2. Put enforcement near authority

A gateway/UI check may improve ergonomics but must not be the only protection for authoritative state or privileged operations when requests can reach the owner through another path.

Prefer enforcement at the component that owns the protected resource/invariant, with upstream checks as defense in depth when useful.

## 3. Trust boundaries need mechanics

A diagram line is not a boundary until it specifies:
- principals on each side;
- allowed interface/capabilities;
- authentication/authorization mechanism;
- least-privilege scope;
- secret/credential ownership and rotation;
- audit requirements when material;
- failure/compromise blast radius.

## 4. Tenant/resource isolation

When isolation is an ASR, state the required level rather than saying "multi-tenant secure":
- logical authorization boundary;
- storage namespace/database/account isolation;
- process/runtime isolation;
- network isolation;
- regional/legal isolation.

Choose the least costly level that satisfies the threat/regulatory scenario. Stronger isolation raises operational cost and can increase boundary distance.

## 5. Compromise scenarios

For critical trust boundaries attack at least the plausible high-impact cases:
- stolen user/service credential;
- compromised public-facing component;
- confused-deputy or privilege escalation;
- cross-tenant identifier manipulation;
- secret leakage;
- replay of privileged request;
- dependency/provider compromise if material.

Ask what the attacker can read/write next and where enforcement stops them.

## 6. Capability and secret scope

Prefer credentials/capabilities scoped to the minimum resource/action/time required. Avoid architectural designs where many components share a broad database/admin credential unless a hard constraint forces it and the blast radius is explicitly accepted.

Secrets require an owner, distribution mechanism, rotation/revocation path, and behavior during rotation failure when material.

## 7. Trust vs cohesion conflict

Security/regulatory isolation may force distance even when business/state cohesion is high. Do not erase the cohesion pressure; load BOUNDARY/STATE as needed and define how invariants/contracts work across the required boundary.

## 8. Fitness checks

Examples when applicable:
- tenant-crossing negative tests;
- authorization policy tests;
- privilege/capability scope assertions;
- secret-rotation drill;
- replay-resistance test;
- audit-event completeness check;
- dependency/security boundary policy lint.

Threat modeling may require deeper domain-specific security expertise; this protocol only establishes architecture-level trust obligations.
