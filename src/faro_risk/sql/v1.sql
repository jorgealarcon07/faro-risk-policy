CREATE SCHEMA IF NOT EXISTS faro_risk;
CREATE TABLE IF NOT EXISTS faro_risk.snapshot (
  namespace text NOT NULL, as_of date NOT NULL, feature_snapshot_id char(64) NOT NULL,
  model_version text NOT NULL, data_kind text NOT NULL, run_id text NOT NULL,
  accounts integer NOT NULL CHECK(accounts>0), published_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(namespace,as_of),
  CHECK ((namespace='uci_tw_credit_2005' AND data_kind='real_public' AND as_of=DATE '2005-09-30')
    OR (namespace='credit_simulated_v1' AND data_kind='synthetic'))
);
CREATE TABLE IF NOT EXISTS faro_risk.score (
  namespace text NOT NULL, as_of date NOT NULL, account_id bigint NOT NULL CHECK(account_id>0),
  score double precision NOT NULL CHECK(score BETWEEN 0 AND 1), tie_key char(64) COLLATE "C" NOT NULL,
  PRIMARY KEY(namespace,as_of,account_id),
  FOREIGN KEY(namespace,as_of) REFERENCES faro_risk.snapshot(namespace,as_of)
);
CREATE INDEX IF NOT EXISTS queue_order ON faro_risk.score(namespace,as_of,score DESC,tie_key);
CREATE OR REPLACE VIEW faro_risk.review_queue AS
 SELECT namespace,as_of,account_id,score,model_version,feature_snapshot_id,data_kind,position
 FROM (
   SELECT s.*, b.model_version,b.feature_snapshot_id,b.data_kind,b.accounts,
     row_number() OVER (PARTITION BY s.namespace,s.as_of ORDER BY s.score DESC,s.tie_key) AS position
   FROM faro_risk.score s JOIN faro_risk.snapshot b USING(namespace,as_of)
 ) ranked WHERE position <= accounts::bigint * 5 / 100;
