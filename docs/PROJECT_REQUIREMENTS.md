# Project Requirements: DW6 Protocol Refinement

This project aims to harden the DW6 protocol by addressing critical flaws identified during initial setup and testing. The goal is to create a robust, fully automated, and user-friendly development workflow.

## 1. Requirement: Robust Environment and Dependency Management

-   **Problem:** The initial project setup fails to reliably create a Python virtual environment (`venv`) and install the necessary dependencies from `pyproject.toml`. This is a critical failure that makes the project unusable from the start.
-   **Goal:** The DW6 setup process must be 100% reliable.
-   **Acceptance Criteria:**
    -   A `venv` directory must be successfully created in the project root.
    -   All project and test dependencies listed in `pyproject.toml` must be successfully installed into the `venv`.
    -   The setup script must provide clear, explicit feedback, confirming the successful creation of the environment and installation of dependencies.
    -   The script must halt with a clear error message if any part of this process fails.

## 2. Requirement: Seamless, Programmatic GitHub Integration

-   **Problem:** The workflow repeatedly triggers UI-based prompts for GitHub authentication, breaking the command-line experience and preventing automation. The system also fails to detect existing Git repository information.
-   **Goal:** All Git and GitHub operations must be handled programmatically without manual UI intervention.
-   **Acceptance Criteria:**
    -   The DW6 engine must automatically detect the remote repository URL from the local `.git/config` file.
    -   The system must use a `GITHUB_TOKEN` from a `.env` file for all `git push` and other GitHub API operations.
    -   The setup workflow must guide the user in creating a `.env` file with the required `GITHUB_TOKEN` if one does not exist.
    -   No UI-based authentication prompts should appear during any part of the workflow.

## 3. Requirement: Automated Coder Deliverable Generation

-   **Problem:** The `Coder` stage lacks a formal, automated deliverable, making it difficult to track and review the exact changes implemented.
-   **Goal:** Automatically generate a `coder_deliverable.md` file that summarizes all code changes made during the `Coder` stage.
-   **Acceptance Criteria:**
    -   When the `Coder` stage is approved, a `coder_deliverable.md` file is automatically created.
    -   The deliverable must contain a list of all modified files.
    -   The deliverable must include the full `git diff` from the start of the `Coder` stage to the end.

## 4. Requirement: Enforce Test Presence in Validator Stage

-   **Problem:** The `Validator` stage can be approved even if the `tests` directory is empty or contains no actual tests, allowing code to pass without verification.
-   **Goal:** Ensure that the `Validator` stage fails if no tests are found and executed.
-   **Acceptance Criteria:**
    -   The `state_manager` must check for the existence of test files (e.g., `tests/test_*.py`) before running `pytest`.
    -   If no test files are found, the `Validator` stage approval must fail with a clear error message.
    -   The `pytest` output must be analyzed to confirm that at least one test was collected and run.
    -   If `pytest` runs but collects zero tests, the approval must fail.

## 5. Requirement: Automated Push to Remote Repository

-   **Problem:** The workflow does not automatically push committed changes and tags to the remote GitHub repository, requiring a manual step that can be forgotten.
-   **Goal:** Automate the push to the remote repository after a successful deployment validation.
-   **Acceptance Criteria:**
    -   After the `Deployer` stage is successfully validated and approved, the `state_manager` must automatically call the `git_handler.push_to_remote` function.
    -   The push must include all committed changes and any new tags.
    -   The workflow must provide clear feedback indicating whether the push was successful or not.
