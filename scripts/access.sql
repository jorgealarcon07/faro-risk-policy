-- Run once as the administrator of the dedicated database, after demo and audit-import.
-- Group roles carry no password. Grant an actual login only the membership its job needs.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='faro_risk_reader') THEN
    CREATE ROLE faro_risk_reader NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='faro_risk_auditor') THEN
    CREATE ROLE faro_risk_auditor NOLOGIN;
  END IF;
END $$;
GRANT USAGE ON SCHEMA faro_risk TO faro_risk_reader;
GRANT SELECT ON faro_risk.review_queue TO faro_risk_reader;
GRANT USAGE ON SCHEMA faro_risk_audit TO faro_risk_auditor;
GRANT SELECT ON faro_risk_audit.historical_accounts TO faro_risk_auditor;
