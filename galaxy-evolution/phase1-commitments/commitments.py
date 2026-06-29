#!/usr/bin/env python3
"""
银河进化计划 — Phase 1: 承诺管理系统 (commitments)
==================================================
原理来源: OpenClaw 2026.6.8 commitments 模块
设计哲学: 纯 JSON 文件 + 状态机，零外部依赖

状态机: pending → sent → dismissed → snoozed → expired
存储: ~/.galaxy-evolution/commitments/commitments.json
去重: dedupeKey + scopeKey (agent+session+channel)
过期: 到期后 72h 自动 expired
限流: 每天每 session 最多 3 条
"""

import json
import os
import time
import hashlib
import secrets
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal

# ── 常量 ──

STORE_VERSION = 1
ROLLING_DAY_MS = 1440 * 60 * 1000  # 24h
EXPIRE_AFTER_MS = 4320 * 60 * 1000  # 72h
DEFAULT_MAX_PER_DAY = 3
DEFAULT_CONFIDENCE_THRESHOLD = 0.72
DEFAULT_CARE_CONFIDENCE_THRESHOLD = 0.86

COMMITMENT_KINDS = {"event_check_in", "deadline_check", "care_check_in", "open_loop"}
COMMITMENT_SENSITIVITIES = {"routine", "personal", "care"}
COMMITMENT_SOURCES = {"inferred_user_context", "agent_promise"}
COMMITMENT_STATUSES = {"pending", "sent", "dismissed", "snoozed", "expired"}

# ── 类型 ──

CommitmentStatus = Literal["pending", "sent", "dismissed", "snoozed", "expired"]
CommitmentKind = Literal["event_check_in", "deadline_check", "care_check_in", "open_loop"]
CommitmentSensitivity = Literal["routine", "personal", "care"]
CommitmentSource = Literal["inferred_user_context", "agent_promise"]


# ── 数据结构 ──

class DueWindow:
    """到期时间窗口"""
    def __init__(self, earliest_ms: int, latest_ms: int, timezone: str = "Asia/Shanghai"):
        self.earliest_ms = earliest_ms
        self.latest_ms = latest_ms
        self.timezone = timezone

    def to_dict(self):
        return {
            "earliestMs": self.earliest_ms,
            "latestMs": self.latest_ms,
            "timezone": self.timezone
        }

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            earliest_ms=d.get("earliestMs", 0),
            latest_ms=d.get("latestMs", 0),
            timezone=d.get("timezone", "Asia/Shanghai")
        )


class Commitment:
    """一条承诺记录"""
    def __init__(
        self,
        id: str,
        agent_id: str,
        session_key: str,
        channel: str,
        kind: CommitmentKind,
        sensitivity: CommitmentSensitivity,
        source: CommitmentSource,
        status: CommitmentStatus,
        reason: str,
        suggested_text: str,
        dedupe_key: str,
        confidence: float,
        due_window: DueWindow,
        created_at_ms: int,
        updated_at_ms: int,
        attempts: int = 0,
        account_id: Optional[str] = None,
        to: Optional[str] = None,
        thread_id: Optional[str] = None,
        sender_id: Optional[str] = None,
        source_message_id: Optional[str] = None,
        source_run_id: Optional[str] = None,
        last_attempt_at_ms: Optional[int] = None,
        sent_at_ms: Optional[int] = None,
        dismissed_at_ms: Optional[int] = None,
        snoozed_until_ms: Optional[int] = None,
        expired_at_ms: Optional[int] = None,
    ):
        self.id = id
        self.agent_id = agent_id
        self.session_key = session_key
        self.channel = channel
        self.kind = kind
        self.sensitivity = sensitivity
        self.source = source
        self.status = status
        self.reason = reason
        self.suggested_text = suggested_text
        self.dedupe_key = dedupe_key
        self.confidence = confidence
        self.due_window = due_window
        self.created_at_ms = created_at_ms
        self.updated_at_ms = updated_at_ms
        self.attempts = attempts
        self.account_id = account_id
        self.to = to
        self.thread_id = thread_id
        self.sender_id = sender_id
        self.source_message_id = source_message_id
        self.source_run_id = source_run_id
        self.last_attempt_at_ms = last_attempt_at_ms
        self.sent_at_ms = sent_at_ms
        self.dismissed_at_ms = dismissed_at_ms
        self.snoozed_until_ms = snoozed_until_ms
        self.expired_at_ms = expired_at_ms

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "agentId": self.agent_id,
            "sessionKey": self.session_key,
            "channel": self.channel,
            "kind": self.kind,
            "sensitivity": self.sensitivity,
            "source": self.source,
            "status": self.status,
            "reason": self.reason,
            "suggestedText": self.suggested_text,
            "dedupeKey": self.dedupe_key,
            "confidence": self.confidence,
            "dueWindow": self.due_window.to_dict(),
            "createdAtMs": self.created_at_ms,
            "updatedAtMs": self.updated_at_ms,
            "attempts": self.attempts,
        }
        for k, v in [
            ("accountId", self.account_id),
            ("to", self.to),
            ("threadId", self.thread_id),
            ("senderId", self.sender_id),
            ("sourceMessageId", self.source_message_id),
            ("sourceRunId", self.source_run_id),
            ("lastAttemptAtMs", self.last_attempt_at_ms),
            ("sentAtMs", self.sent_at_ms),
            ("dismissedAtMs", self.dismissed_at_ms),
            ("snoozedUntilMs", self.snoozed_until_ms),
            ("expiredAtMs", self.expired_at_ms),
        ]:
            if v is not None:
                d[k] = v
        return d

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            id=d["id"],
            agent_id=d["agentId"],
            session_key=d["sessionKey"],
            channel=d["channel"],
            kind=d["kind"],
            sensitivity=d["sensitivity"],
            source=d["source"],
            status=d["status"],
            reason=d["reason"],
            suggested_text=d["suggestedText"],
            dedupe_key=d["dedupeKey"],
            confidence=d["confidence"],
            due_window=DueWindow.from_dict(d["dueWindow"]),
            created_at_ms=d["createdAtMs"],
            updated_at_ms=d["updatedAtMs"],
            attempts=d.get("attempts", 0),
            account_id=d.get("accountId"),
            to=d.get("to"),
            thread_id=d.get("threadId"),
            sender_id=d.get("senderId"),
            source_message_id=d.get("sourceMessageId"),
            source_run_id=d.get("sourceRunId"),
            last_attempt_at_ms=d.get("lastAttemptAtMs"),
            sent_at_ms=d.get("sentAtMs"),
            dismissed_at_ms=d.get("dismissedAtMs"),
            snoozed_until_ms=d.get("snoozedUntilMs"),
            expired_at_ms=d.get("expiredAtMs"),
        )

    def is_active(self) -> bool:
        return self.status in ("pending", "snoozed")

    def is_due(self, now_ms: int) -> bool:
        if not self.is_active():
            return False
        if self.status == "snoozed" and self.snoozed_until_ms and self.snoozed_until_ms > now_ms:
            return False
        stale_after = self.due_window.latest_ms + EXPIRE_AFTER_MS
        return self.due_window.earliest_ms <= now_ms and stale_after >= now_ms

    def build_scope_key(self) -> str:
        parts = [self.agent_id or "", self.session_key or "", self.channel or "",
                 self.account_id or "", self.to or "", self.thread_id or "", self.sender_id or ""]
        return "".join(parts)


# ── 存储引擎 ──

class CommitmentStore:
    """承诺存储引擎 — 纯 JSON 文件 + 文件锁"""

    def __init__(self, store_path: Optional[str] = None):
        if store_path:
            self.store_path = Path(store_path)
        else:
            home = Path.home()
            self.store_path = home / ".galaxy-evolution" / "commitments" / "commitments.json"
        self._lock = threading.Lock()
        self._ensure_dir()

    def _ensure_dir(self):
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def _empty_store(self) -> dict:
        return {"version": STORE_VERSION, "commitments": []}

    def _read_store(self) -> dict:
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("version") != STORE_VERSION or not isinstance(data.get("commitments"), list):
                return self._empty_store()
            return data
        except (FileNotFoundError, json.JSONDecodeError):
            return self._empty_store()

    def _write_store(self, store: dict):
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def _generate_id(self, now_ms: int) -> str:
        rand = secrets.token_hex(5)
        return f"cm_{now_ms:x}_{rand}"

    def _expire_stale(self, store: dict, now_ms: int) -> bool:
        changed = False
        for c in store["commitments"]:
            if c["status"] in ("pending", "snoozed"):
                stale_after = c["dueWindow"]["latestMs"] + EXPIRE_AFTER_MS
                if stale_after < now_ms:
                    c["status"] = "expired"
                    c["expiredAtMs"] = now_ms
                    c["updatedAtMs"] = now_ms
                    changed = True
        return changed

    def load(self) -> list[Commitment]:
        """加载所有承诺（自动标记过期）"""
        with self._lock:
            now = self._now_ms()
            store = self._read_store()
            self._expire_stale(store, now)
            self._write_store(store)
            return [Commitment.from_dict(c) for c in store["commitments"]]

    def upsert(self, commitment: Commitment) -> Commitment:
        """插入或更新承诺（去重）"""
        with self._lock:
            now = self._now_ms()
            store = self._read_store()
            self._expire_stale(store, now)

            scope_key = commitment.build_scope_key()
            existing_idx = None
            for i, c in enumerate(store["commitments"]):
                cm = Commitment.from_dict(c)
                if cm.build_scope_key() == scope_key and cm.dedupe_key == commitment.dedupe_key and cm.is_active():
                    existing_idx = i
                    break

            if existing_idx is not None:
                # 更新：合并置信度取 max，更新到期窗口
                existing = store["commitments"][existing_idx]
                existing["reason"] = commitment.reason or existing["reason"]
                existing["suggestedText"] = commitment.suggested_text or existing["suggestedText"]
                existing["confidence"] = max(existing["confidence"], commitment.confidence)
                existing["dueWindow"]["earliestMs"] = min(
                    existing["dueWindow"]["earliestMs"], commitment.due_window.earliest_ms)
                existing["dueWindow"]["latestMs"] = max(
                    existing["dueWindow"]["latestMs"], commitment.due_window.latest_ms)
                existing["updatedAtMs"] = now
                result = Commitment.from_dict(existing)
            else:
                # 新建
                record = commitment.to_dict()
                record["id"] = self._generate_id(now)
                record["createdAtMs"] = now
                record["updatedAtMs"] = now
                record["attempts"] = 0
                store["commitments"].append(record)
                result = Commitment.from_dict(record)

            self._write_store(store)
            return result

    def mark_status(self, commitment_id: str, status: CommitmentStatus) -> bool:
        """更新承诺状态"""
        with self._lock:
            now = self._now_ms()
            store = self._read_store()
            for c in store["commitments"]:
                if c["id"] == commitment_id:
                    c["status"] = status
                    c["updatedAtMs"] = now
                    if status == "sent":
                        c["sentAtMs"] = now
                    elif status == "dismissed":
                        c["dismissedAtMs"] = now
                    elif status == "expired":
                        c["expiredAtMs"] = now
                    self._write_store(store)
                    return True
            return False

    def mark_attempted(self, commitment_id: str):
        """标记已尝试推送"""
        with self._lock:
            now = self._now_ms()
            store = self._read_store()
            for c in store["commitments"]:
                if c["id"] == commitment_id:
                    c["attempts"] = c.get("attempts", 0) + 1
                    c["lastAttemptAtMs"] = now
                    c["updatedAtMs"] = now
                    self._write_store(store)
                    return True
            return False

    def list_pending(self, agent_id: str, session_key: str, channel: str,
                     limit: int = 20) -> list[Commitment]:
        """列出指定 scope 的待处理承诺"""
        now = self._now_ms()
        store = self._read_store()
        self._expire_stale(store, now)

        results = []
        for c in store["commitments"]:
            cm = Commitment.from_dict(c)
            if (cm.agent_id == agent_id and cm.session_key == session_key
                    and cm.channel == channel and cm.is_active()):
                if cm.status == "snoozed" and cm.snoozed_until_ms and cm.snoozed_until_ms > now:
                    continue
                results.append(cm)

        results.sort(key=lambda x: (x.due_window.earliest_ms, x.created_at_ms))
        return results[:limit]

    def list_due(self, agent_id: str, session_key: str, now_ms: Optional[int] = None,
                 limit: int = 3, max_per_day: int = DEFAULT_MAX_PER_DAY) -> list[Commitment]:
        """列出到期的承诺（心跳驱动用）"""
        now = now_ms or self._now_ms()
        store = self._read_store()
        self._expire_stale(store, now)

        # 计算今天已发送数量
        since_ms = now - ROLLING_DAY_MS
        sent_count = sum(1 for c in store["commitments"]
                         if c["agentId"] == agent_id and c["sessionKey"] == session_key
                         and c["status"] == "sent" and (c.get("sentAtMs", 0) or 0) >= since_ms)

        remaining = max_per_day - sent_count
        if remaining <= 0:
            return []

        limit = min(limit, remaining, 3)
        results = []
        for c in store["commitments"]:
            cm = Commitment.from_dict(c)
            if cm.agent_id == agent_id and cm.session_key == session_key and cm.is_due(now):
                results.append(cm)

        results.sort(key=lambda x: (x.due_window.earliest_ms, x.created_at_ms))
        return results[:limit]

    def count(self) -> dict:
        """统计各状态数量"""
        store = self._read_store()
        counts = {"total": len(store["commitments"]), "pending": 0, "sent": 0,
                  "dismissed": 0, "snoozed": 0, "expired": 0}
        for c in store["commitments"]:
            s = c.get("status", "unknown")
            if s in counts:
                counts[s] += 1
        return counts


# ── 便捷创建函数 ──

def make_commitment(
    agent_id: str,
    session_key: str,
    channel: str,
    kind: CommitmentKind,
    reason: str,
    suggested_text: str,
    due_in_seconds: int = 3600,
    sensitivity: CommitmentSensitivity = "routine",
    confidence: float = 0.8,
    dedupe_key: Optional[str] = None,
) -> Commitment:
    """快速创建一条承诺"""
    now = int(time.time() * 1000)
    if dedupe_key is None:
        dedupe_key = hashlib.md5(reason.encode()).hexdigest()[:16]

    return Commitment(
        id="",  # 由 store 生成
        agent_id=agent_id,
        session_key=session_key,
        channel=channel,
        kind=kind,
        sensitivity=sensitivity,
        source="inferred_user_context",
        status="pending",
        reason=reason,
        suggested_text=suggested_text,
        dedupe_key=dedupe_key,
        confidence=confidence,
        due_window=DueWindow(
            earliest_ms=now,
            latest_ms=now + due_in_seconds * 1000,
        ),
        created_at_ms=now,
        updated_at_ms=now,
    )


# ── CLI 入口 ──

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="银河进化计划 — 承诺管理系统")
    sub = parser.add_subparsers(dest="command")

    # list
    p_list = sub.add_parser("list", help="列出承诺")
    p_list.add_argument("--agent", default="main", help="Agent ID")
    p_list.add_argument("--session", default="main", help="Session Key")
    p_list.add_argument("--channel", default="webchat", help="Channel")
    p_list.add_argument("--due", action="store_true", help="仅列出到期承诺")
    p_list.add_argument("--json", action="store_true", help="JSON 输出")

    # add
    p_add = sub.add_parser("add", help="添加承诺")
    p_add.add_argument("--agent", default="main")
    p_add.add_argument("--session", default="main")
    p_add.add_argument("--channel", default="webchat")
    p_add.add_argument("--kind", default="deadline_check",
                       choices=list(COMMITMENT_KINDS))
    p_add.add_argument("--reason", required=True, help="承诺原因")
    p_add.add_argument("--text", required=True, help="建议文本")
    p_add.add_argument("--due-in", type=int, default=3600, help="到期时间（秒）")
    p_add.add_argument("--sensitivity", default="routine",
                       choices=list(COMMITMENT_SENSITIVITIES))
    p_add.add_argument("--confidence", type=float, default=0.8)

    # dismiss
    p_dismiss = sub.add_parser("dismiss", help="取消承诺")
    p_dismiss.add_argument("id", help="承诺 ID")

    # status
    p_status = sub.add_parser("status", help="查看统计")

    args = parser.parse_args()
    store = CommitmentStore()

    if args.command == "list":
        if args.due:
            items = store.list_due(args.agent, args.session)
        else:
            items = store.list_pending(args.agent, args.session, args.channel)
        if args.json:
            print(json.dumps([c.to_dict() for c in items], ensure_ascii=False, indent=2))
        else:
            if not items:
                print("📭 没有待处理的承诺")
            for c in items:
                due_str = datetime.fromtimestamp(c.due_window.earliest_ms / 1000,
                                                  tz=timezone(timedelta(hours=8))).strftime("%m-%d %H:%M")
                print(f"  [{c.id[:20]}..] {c.kind} | {c.reason[:40]} | 到期: {due_str} | 置信度: {c.confidence:.2f}")

    elif args.command == "add":
        cm = make_commitment(
            agent_id=args.agent,
            session_key=args.session,
            channel=args.channel,
            kind=args.kind,
            reason=args.reason,
            suggested_text=args.text,
            due_in_seconds=args.due_in,
            sensitivity=args.sensitivity,
            confidence=args.confidence,
        )
        result = store.upsert(cm)
        print(f"✅ 承诺已创建: {result.id}")

    elif args.command == "dismiss":
        if store.mark_status(args.id, "dismissed"):
            print(f"✅ 承诺已取消: {args.id}")
        else:
            print(f"❌ 未找到承诺: {args.id}")

    elif args.command == "status":
        counts = store.count()
        print(f"📊 承诺统计:")
        print(f"  总计: {counts['total']}")
        print(f"  ⏳ 待处理: {counts['pending']}")
        print(f"  ✅ 已发送: {counts['sent']}")
        print(f"  ❌ 已取消: {counts['dismissed']}")
        print(f"  😴 已延后: {counts['snoozed']}")
        print(f"  ⌛ 已过期: {counts['expired']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
