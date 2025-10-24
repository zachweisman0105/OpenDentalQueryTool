# Quickstart Guide

This quickstart walks you through installing, configuring, and running your first query.

## 1. Install

- Python 3.11+ required
- Create and activate a virtual environment
- Install the package in editable mode

## 2. Initialize Vault

- Run `opendental-query vault-init`
- Set a strong master password (20+ chars)

## 3. Add Offices

- Run `opendental-query vault-add-office`
- Add at least one office with CustomerKey

## 4. Configure (optional)

- `opendental-query config set network.verify_ssl true`
- `opendental-query config set query.timeout_seconds 30`

## 5. Run a Query

- `Query "SELECT PatNum, LName, FName FROM patient LIMIT 5"` (alias for `opendental-query query`)

## 6. Export to CSV

- `Query --export --output ./results.csv "SELECT * FROM patient LIMIT 100"`

## 7. Audit Logs

- Audit logs are stored at `~/.opendental-query/audit.jsonl`

For more, see README.md and SECURITY.md.
