CREATE SCHEMA IF NOT EXISTS faro_risk_audit;
REVOKE ALL ON SCHEMA faro_risk_audit FROM PUBLIC;
CREATE TABLE IF NOT EXISTS faro_risk_audit.historical_accounts (
  account_id bigint PRIMARY KEY, sex_code integer NOT NULL, education_code integer NOT NULL,
  marriage_code integer NOT NULL, age_years integer NOT NULL,
  source_sha256 char(64) NOT NULL
);
REVOKE ALL ON faro_risk_audit.historical_accounts FROM PUBLIC;
