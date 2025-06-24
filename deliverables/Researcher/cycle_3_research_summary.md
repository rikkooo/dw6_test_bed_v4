# Research Summary: Enforcing Test Presence in Validator Stage

**Date:** 2025-06-25

## 1. Objective

This research was conducted to find the best method for programmatically checking if `pytest` has collected any tests, which is essential for enforcing the new `Validator` stage requirements.

## 2. Findings

### Parsing Pytest Output

- **Conclusion:** The most direct way to determine the number of collected tests is to run `pytest` with the `--collect-only` flag and parse its standard output. This avoids running the tests themselves, making the check fast and efficient.
- **Implementation:**
    1.  Run the command: `pytest --collect-only`.
    2.  Capture the output of the command.
    3.  Use a regular expression to find the line that summarizes the collection results. The key line to look for typically matches the pattern `collected (\d+) items` or `(\d+) tests collected`.
    4.  Extract the number from this line. If the number is `0` or the pattern is not found, it means no tests were collected.

### Alternative Methods Considered

- **Pytest Plugins:** While plugins like `pytest-json-report` could provide structured output, adding a new dependency just for this check is overkill and adds unnecessary complexity.
- **Pytest Hooks:** Using `pytest_collection_finish` hooks would require a more complex integration with the `pytest` internals. A simple output-parsing approach is more straightforward and less coupled to the `pytest` API.

## 3. Recommended Implementation Strategy

The implementation plan outlined in the technical specification is confirmed. The `state_manager.py` should execute `pytest --collect-only` as a subprocess and use a regular expression to parse the output. This is the simplest and most robust solution that doesn't introduce new dependencies. The regex `r"collected (\d+) items"` should be sufficient to capture the number of tests found.
