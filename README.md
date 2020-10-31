# Bitbucket automator

This script automatically submits, approves and merges the pull requests between specific branches in a specific order.

I wrote this tool because in my company we didn't like the built-in automatic branch merging feature.

## How it works

Let `MERGING_SEQUENCE` be A,B,C,D

1. Clone the repository to a separate directory, to avoid interfering with your work
2. Fetch open pull requests
3. If a pull request from A to B exists, approve it and merge it
4. If it doesn't, checkout B and try to merge A
5. If there are no conflicts and B is not already up to date, submit a pull request
6. Repeat from step 3 for branches B and C, then for C and D

## Usage

Copy `.env.example` to `.env` and set appropriate values.

The script exits after going through the branches once. To automate it further, schedule a cron job / launch agent or setup a hook.

## Future improvements

- [ ] Notify the user when conflicts are detected
- [ ] Optimize Git operations: shallow clone, better conflict and up-to-dateness detection
