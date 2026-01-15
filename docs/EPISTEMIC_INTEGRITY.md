# Epistemic Integrity: The Hierarchy of Truth

## Status Levels
- **Level 0: Shadow**: Intent only. No implementation.
- **Level 1: Claim**: AI-generated code. Unverified.
- **Level 2: Witnessed**: AI-generated, passed Docker/Nix build.
- **Level 3: Endorsed**: Human-accepted. This is the "Master" version.
- **Level 4: Fossil**: An old version of an Endorsed atom kept for "Time-Travel" debugging.

## The Sentinel's Duty
The Sentinel Daemon constantly compares **Level 3 Atoms** against their **Portals**. If a Portal (e.g., a Nix-provided header) changes, the Atom is demoted to **Level 1 (Claim)** and requires a new Witness pass.
