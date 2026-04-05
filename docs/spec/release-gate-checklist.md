# Release Gate Checklist

Last updated: 2026-04-07

The MVP is pilot-ready only when all items below are visible and checkable:

1. Import -> compile -> Passport generation completes in one local session.
2. The Passport manifest includes active focus and representative postcards.
3. Topic-level Visa issuance and revocation both work.
4. External AI writeback creates review candidates only; there is no silent merge path.
5. Postcards and Passport outputs expose evidence links.
6. Review candidates trace back to a concrete mount session.
7. Export and restore have both been exercised successfully.
8. A real-user feedback loop has collected fit, trust, and friction data.

Reference implementation:

- `app/review/ops.py`
- `scripts/pilot_flow.py`
