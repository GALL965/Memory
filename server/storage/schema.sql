CREATE TABLE IF NOT EXISTS games (
  game_id UUID PRIMARY KEY,
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  rows INT NOT NULL,
  cols INT NOT NULL,
  max_players INT NOT NULL,
  mismatch_hide_delay_ms INT NOT NULL,
  finished BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS game_players (
  game_id UUID NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
  player_id UUID NOT NULL,
  name TEXT NOT NULL,
  score INT NOT NULL DEFAULT 0,
  moves INT NOT NULL DEFAULT 0,
  avg_response_ms DOUBLE PRECISION NOT NULL DEFAULT 0,
  total_response_ms DOUBLE PRECISION NOT NULL DEFAULT 0,
  PRIMARY KEY (game_id, player_id)
);

CREATE TABLE IF NOT EXISTS moves (
  id BIGSERIAL PRIMARY KEY,
  game_id UUID NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
  player_id UUID NOT NULL,
  seq BIGINT NOT NULL,
  row INT NOT NULL,
  col INT NOT NULL,
  selection_index INT NOT NULL,
  result TEXT NOT NULL,
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS moves_game_id_idx ON moves(game_id);

CREATE TABLE IF NOT EXISTS turns (
  id BIGSERIAL PRIMARY KEY,
  game_id UUID NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
  player_id UUID NOT NULL,
  turn_no INT NOT NULL,
  response_ms DOUBLE PRECISION NOT NULL,
  matched BOOLEAN NOT NULL,
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS turns_game_id_idx ON turns(game_id);
