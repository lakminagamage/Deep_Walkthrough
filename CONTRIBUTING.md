Contributing
============

Thanks for your interest in contributing. This project is a reference implementation, so clarity, correctness, and observability matter more than micro-optimizations.

How to contribute
-----------------

- Open an issue describing the change and its motivation.
- Keep changes focused and include tests or validation steps when appropriate.
- Follow the design constraints in CLAUDE.MD.

Development setup
-----------------

1. Create a .env file based on .env.example.
2. Start the stack:
   - make up
3. Optional: ingest a document for testing:
   - make ingest file=path/to/doc.pdf
   - make ingest-url url=https://example.com

Pull request checklist
----------------------

- The change aligns with the system constraints in CLAUDE.MD.
- The code is fully async where required and tools return ToolResult on errors.
- The UI remains usable on desktop and mobile.
- Documentation is updated if behavior changes.

Reporting issues
----------------

Include:
- Steps to reproduce
- Expected vs actual behavior
- Logs or relevant screenshots if available
