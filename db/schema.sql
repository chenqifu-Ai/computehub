-- ComputeHub Physical Resource Database Schema
-- Version: 1.0.0
-- Description: Stores hardware fingerprints and time-series heartbeats

CREATE TABLE IF NOT EXISTS nodes (
    node_id VARCHAR(255) PRIMARY KEY,
    hardware_fingerprint TEXT NOT NULL,
    os VARCHAR(50),
    gpu_model VARCHAR(100),
    memory_total_mb INTEGER,
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'REGISTERED', -- REGISTERED, ONLINE, OFFLINE, DANGER
    ip_address VARCHAR(45)
);

CREATE TABLE IF NOT EXISTS node_heartbeats (
    id BIGSERIAL PRIMARY KEY,
    node_id VARCHAR(255) REFERENCES nodes(node_id),
    temperature INTEGER,
    utilization INTEGER,
    power_draw FLOAT,
    memory_used_mb INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_node_heartbeats_node_id ON node_heartbeats(node_id);
CREATE INDEX idx_node_heartbeats_timestamp ON node_heartbeats(timestamp);
