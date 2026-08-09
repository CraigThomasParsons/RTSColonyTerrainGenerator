# Verification Report: <Component>

<!-- One per verified component; lives in the slice's Spec Pack. Honesty over polish:
     the "Not Proved" and "Assumptions" sections are the point of this document. -->

## Requirement

What behaviour is being protected, and which requirement/contract sections it comes from.

## Specification Files

The `.dfy` files under `specs/` that carry this component, and the verification level
(A: executable model, B: verified reference, C: compiled) per `docs/adr/0002`.

## Properties Proved

The exact guarantees, one per line, phrased as the lemma/ensures states them — not a
paraphrase that sounds stronger.

## Preconditions

The assumptions callers must satisfy (`requires` clauses). Note where each is enforced
in C# (value-object constructor, guard, validator).

## Assumptions and Axioms

Every `assume`, `{:axiom}`, or admitted lemma, each with: why it is necessary, who
owns it, how it is tested or monitored, and how it could later be removed. Empty is
the goal; if not empty, it needed explicit approval.

## Not Proved

Important exclusions — properties a reader might assume are covered but are not
(e.g. optimality, performance, visual quality, behaviour outside the preconditions).

## Production Relationship

Whether the Dafny artifact is an independent model, a reference implementation
producing canonical fixture outputs, or a compiled component — and how the C# code is
held to it.

## Test Relationship

How C# tests connect to this specification: which property tests encode which
lemmas, which compatibility tests compare against reference outputs, and which Golden
Jobs are involved.

## Verification Status

Date, Dafny version, command (`dafny verify specs/...`), result, and any timeouts or
instability observed (instability must be reported, not retried into silence).
