"""Stream website activity logs into Neo4j and explain threats with Gemini.

Configuration is read from environment variables. This module is safe to import
when Neo4j or Gemini is not configured; connection errors are reported by the
 dashboard instead of preventing the website from starting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

try:
    from neo4j import GraphDatabase
except ImportError:  # Optional until the detector is used.
    GraphDatabase = None

try:
    import google.generativeai as genai
except ImportError:  # Optional until Gemini explanations are requested.
    genai = None

LOG_FILE_PATH = Path(os.getenv("LOG_FILE_PATH", str(BASE_DIR / "log.log")))
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
THREAT_THRESHOLD = float(os.getenv("THREAT_THRESHOLD", "0.75"))

ATTACK_EVENT_TYPES = {
    "sql_injection_indicator": "SQL Injection",
    "brute_force_login": "Brute-Force Login",
    "malicious_file_upload": "Malicious File Upload",
    "reconnaissance_scan": "Reconnaissance / Directory Scan",
}


class SecurityStore:
    """Neo4j-backed storage and analysis for website security events."""

    def __init__(self) -> None:
        self._driver: Any = None

    def connect(self) -> None:
        if self._driver is not None:
            return
        if GraphDatabase is None:
            raise RuntimeError("Neo4j dependency is missing. Run: pip install neo4j")
        if not NEO4J_PASSWORD:
            raise RuntimeError("NEO4J_PASSWORD is not configured")
        self._driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )
        self._driver.verify_connectivity()

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    @staticmethod
    def event_id(log_data: dict[str, Any]) -> str:
        canonical = json.dumps(log_data, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def attack_type(log_data: dict[str, Any]) -> str:
        event_type = str(log_data.get("event_type", ""))
        if event_type in ATTACK_EVENT_TYPES:
            return ATTACK_EVENT_TYPES[event_type]
        if str(log_data.get("status_code", "")).startswith(("4", "5")):
            return "Suspicious HTTP Activity"
        return "Normal Activity"

    def store_log(self, log_data: dict[str, Any]) -> None:
        self.connect()
        source_ip = str(log_data.get("source_ip", "unknown"))
        endpoint = str(log_data.get("path", "unknown"))
        event_type = str(log_data.get("event_type", "http_request"))
        status_code = int(log_data.get("status_code", 200) or 200)
        event_id = self.event_id(log_data)
        threat_type = self.attack_type(log_data)
        is_attack = threat_type != "Normal Activity"

        query = """
        MERGE (ip:IPAddress {value: $source_ip})
        MERGE (endpoint:Endpoint {value: $endpoint})
        MERGE (event:SecurityEvent {event_id: $event_id})
        SET event.event_type = $event_type,
            event.threat_type = $threat_type,
            event.status_code = $status_code,
            event.timestamp = $timestamp,
            event.method = $method,
            event.user_agent = $user_agent
        MERGE (ip)-[:GENERATED]->(event)
        MERGE (event)-[:TARGETED]->(endpoint)
        """
        relationship_query = """
        MATCH (ip:IPAddress {value: $source_ip}), (endpoint:Endpoint {value: $endpoint})
        MERGE (ip)-[r:%s {event_id: $event_id}]->(endpoint)
        SET r.timestamp = $timestamp, r.status_code = $status_code, r.event_type = $event_type
        """ % ("ATTEMPTED" if is_attack else "ACCESSED")
        params = {
            "source_ip": source_ip,
            "endpoint": endpoint,
            "event_id": event_id,
            "event_type": event_type,
            "threat_type": threat_type,
            "status_code": status_code,
            "timestamp": str(log_data.get("timestamp", "unknown")),
            "method": str(log_data.get("method", "unknown")),
            "user_agent": str(log_data.get("user_agent", "unknown")),
        }
        with self._driver.session(database=NEO4J_DATABASE) as session:
            session.run(query, **params).consume()
            session.run(relationship_query, **params).consume()

    def threat_score(self, source_ip: str) -> float:
        self.connect()
        query = """
        MATCH (:IPAddress {value: $source_ip})-[r:ATTEMPTED]->()
        RETURN count(r) AS risk_count
        """
        with self._driver.session(database=NEO4J_DATABASE) as session:
            record = session.run(query, source_ip=source_ip).single()
        count = int(record["risk_count"]) if record else 0
        return min(1.0, count * 0.15)

    def summary(self) -> dict[str, Any]:
        self.connect()
        query = """
        OPTIONAL MATCH (ip:IPAddress)
        WITH count(ip) AS source_ips
        OPTIONAL MATCH (endpoint:Endpoint)
        WITH source_ips, count(endpoint) AS endpoints
        OPTIONAL MATCH (event:SecurityEvent)
        RETURN source_ips, endpoints, count(event) AS total_events,
               sum(CASE WHEN event.threat_type <> 'Normal Activity' THEN 1 ELSE 0 END) AS threat_events
        """
        top_query = """
        MATCH (ip:IPAddress)-[:GENERATED]->(event:SecurityEvent)
        WHERE event.threat_type <> 'Normal Activity'
        RETURN ip.value AS source_ip, count(event) AS threats,
               max(event.timestamp) AS last_seen
        ORDER BY threats DESC LIMIT 10
        """
        with self._driver.session(database=NEO4J_DATABASE) as session:
            stats = session.run(query).single()
            top_ips = [record.data() for record in session.run(top_query)]
        return {
            "source_ips": int(stats["source_ips"] or 0) if stats else 0,
            "endpoints": int(stats["endpoints"] or 0) if stats else 0,
            "total_events": int(stats["total_events"] or 0) if stats else 0,
            "threat_events": int(stats["threat_events"] or 0) if stats else 0,
            "top_ips": top_ips,
            "threshold": THREAT_THRESHOLD,
        }

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        self.connect()
        query = """
        MATCH (event:SecurityEvent)-[:TARGETED]->(endpoint:Endpoint)
        MATCH (ip:IPAddress)-[:GENERATED]->(event)
        RETURN event.timestamp AS timestamp, ip.value AS source_ip,
               endpoint.value AS path, event.event_type AS event_type,
               event.threat_type AS threat_type, event.status_code AS status_code
        ORDER BY event.timestamp DESC LIMIT $limit
        """
        with self._driver.session(database=NEO4J_DATABASE) as session:
            return [record.data() for record in session.run(query, limit=max(1, min(limit, 200)))]

    def explain_ip(self, source_ip: str) -> str:
        self.connect()
        query = """
        MATCH (ip:IPAddress {value: $source_ip})-[:GENERATED]->(event:SecurityEvent)-[:TARGETED]->(endpoint:Endpoint)
        RETURN event.timestamp AS timestamp, endpoint.value AS path,
               event.event_type AS event_type, event.threat_type AS threat_type,
               event.status_code AS status_code
        ORDER BY event.timestamp DESC LIMIT 50
        """
        with self._driver.session(database=NEO4J_DATABASE) as session:
            context = [record.data() for record in session.run(query, source_ip=source_ip)]
        score = self.threat_score(source_ip)
        if genai is None:
            raise RuntimeError("Gemini dependency is missing. Run: pip install google-generativeai")
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        genai.configure(api_key=GEMINI_API_KEY)
        prompt = (
            "You are a defensive cybersecurity analyst. Explain this threat using only "
            "the supplied evidence. Identify attack type, likely source, timeline, "
            "confidence, and practical containment steps. Do not claim an attack that "
            "is not present. Threat score: %s. Evidence: %s"
            % (score, json.dumps(context, ensure_ascii=True))
        )
        response = genai.GenerativeModel("gemini-1.5-flash").generate_content(
            prompt,
            generation_config={"temperature": 0.2},
        )
        return response.text


def read_log_line(line: str) -> dict[str, Any] | None:
    try:
        data = json.loads(line.strip())
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def monitor(follow: bool = True, from_start: bool = False) -> None:
    store = SecurityStore()
    print(f"[START] Monitoring {LOG_FILE_PATH}")
    LOG_FILE_PATH.touch(exist_ok=True)
    try:
        with LOG_FILE_PATH.open("r", encoding="utf-8") as stream:
            if not from_start:
                stream.seek(0, os.SEEK_END)
            while True:
                line = stream.readline()
                if not line:
                    if not follow:
                        break
                    time.sleep(0.2)
                    continue
                record = read_log_line(line)
                if record is None or not record.get("source_ip"):
                    continue
                try:
                    store.store_log(record)
                    score = store.threat_score(str(record["source_ip"]))
                    print(f"[INGESTED] {record.get('event_type')} from {record['source_ip']} | score={score:.2f}")
                except Exception as error:
                    print(f"[STORE ERROR] {error}")
    finally:
        store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor website logs and store them in Neo4j")
    parser.add_argument("--once", action="store_true", help="Process existing log entries and exit")
    parser.add_argument("--from-start", action="store_true", help="Read from the beginning of the log")
    args = parser.parse_args()
    monitor(follow=not args.once, from_start=args.from_start)


if __name__ == "__main__":
    main()
