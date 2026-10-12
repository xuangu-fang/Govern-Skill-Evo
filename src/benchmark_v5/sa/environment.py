"""Deterministic service with explicit public projections and replayable calls."""
from copy import deepcopy
import hashlib
import inspect
import json

from . import VERSION
from .rules import World


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class ToolError(ValueError):
    pass


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def schema(properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


STRING = {"type": "string", "minLength": 1}
ALLOCATIONS = {"type": "object", "minProperties": 1,
               "additionalProperties": {"type": "integer", "minimum": 1}}
PARAMS = {
    "read_status": {}, "read_recipes": {}, "read_log": {},
    "draft_batch": {"batch_id": STRING, "allocations": ALLOCATIONS},
    "cancel_batch": {"batch_id": STRING}, "start_batch": {"batch_id": STRING},
    "advance": {}, "wait_until": {"minute": {"type": "integer", "minimum": 0}},
    "finish": {"receipt": {"type": "object", "additionalProperties": {
        "type": "object", "properties": {"quantity": {"type": "integer"},
        "completed_at": {"type": "integer"}}, "required": ["quantity", "completed_at"],
        "additionalProperties": False}}},
}
READS = {"read_status", "read_recipes", "read_log"}


class Environment:
    def __init__(self, case, world=None):
        self.case = deepcopy(case)
        self.world = world or World()
        self._validate_case()
        self.orders = {o["id"]: o for o in self.case["orders"]}
        self.state = dict(now=0, setting=list(case["initial"]), batches={}, active=None,
                          previous_batch=False, completed={k: [] for k in self.orders},
                          log=[], closed=False, receipt=None, end_reason=None)
        self._timing = None
        self.operations = {}
        self.events = []

    def _validate_case(self):
        c = self.case
        if c.get("world_version") != "sa-synthetic-v1":
            raise ValueError("WORLD_VERSION_MISMATCH")
        if c.get("split") not in ("engineering_train", "engineering_dev"):
            raise ValueError("ONLY_ENGINEERING_SPLITS_SUPPORTED")
        if not c.get("id") or not integer(c.get("capacity"), 1) or not integer(c.get("shift_end"), 1):
            raise ValueError("INVALID_CASE")
        self._setting(c["initial"])
        ids = set()
        for o in c["orders"]:
            if not isinstance(o["id"], str) or not o["id"] or o["id"] in ids:
                raise ValueError("INVALID_ORDER_ID")
            ids.add(o["id"])
            self._setting([o["fixture"], o["profile"]])
            if not all(integer(o[k], 1 if k == "quantity" else 0)
                       for k in ("quantity", "release", "due")) or o["release"] > o["due"]:
                raise ValueError("INVALID_ORDER")
        if not ids:
            raise ValueError("EMPTY_CASE")

    @staticmethod
    def _setting(setting):
        if len(setting) != 2 or setting[0] not in ("flat", "hanging") or setting[1] not in ("low", "high"):
            raise ValueError("INVALID_SETTING")

    def request(self):
        return dict(case_id=self.case["id"], world_version=self.case["world_version"],
            goal="按每单公开交期，完成全部指定载盘并准确回执；不要求最优顺序或最少批次。",
            service="合成的新接入批式固化服务；Agent仅调度已批准配方，不能改变安全配方。",
            policy="同工装同配方才可合批；容量公开，允许拆批。没有可靠总工时预测服务。"
                   "工艺段时长公开，额外装卸及换型周转初始未标定，同世界固定。"
                   "草稿可编辑取消；设置完成后可取消并保留实际新设置。"
                   "加工为不可暂停的合格工艺循环；未开始草稿仍可取消。"
                   "班内设备保持最近设置，无故障、漂移或其他资源。"
                   "查询/草稿/思考不推进模拟时间。只有advance与空闲时wait_until推进时间。"
                   "开始时不预报结束时刻；advance到下一实际设置或加工完成事件。"
                   "班末中断在途工序且该批无合格产出，过去时间不回滚。"
                   "写操作需operation_id；同号同载荷幂等，不同载荷拒绝。"
                   "finish只收录回执不反馈评分，所有截止时刻包含等号。",
            recipes=self.read_recipes(), status=self.read_status(),
            receipt_format="订单ID -> {quantity: 实际完成总量, completed_at: 最后完成时刻}，仅填已完订单。")

    def catalog(self):
        descriptions = {
            "read_status": "读取订单、实际设备状态、草稿与已完成数量；不返回未来完工时间。",
            "read_recipes": "读取全部批准组合、每批公开工艺段和容量；不能修改安全配置。",
            "read_log": "读取已经发生的设置、加工、等待与中断日志，不包含未来事件。",
            "draft_batch": "创建或修改未开始草稿，allocations为订单ID到载盘数；不耗时。",
            "cancel_batch": "取消草稿或完成设置尚未加工的批次；不退回时间，保留设置。",
            "start_batch": "空闲时开始已释放的草稿设置；不预报时长。",
            "advance": "推进当前设置至完成；或对READY批次执行一次不可暂停的加工循环。",
            "wait_until": "设备空闲时等待到指定模拟分钟，不得超过班末。",
            "finish": "结束服务，提交实际完成订单的回执；不返回正确性或评分。",
        }
        return [dict(name=k, description=descriptions[k], parameters=schema(
            v if k in READS else {**v, "operation_id": STRING})) for k, v in PARAMS.items()]

    def read_recipes(self):
        return dict(capacity=self.case["capacity"], unit="carrier", recipe_minutes=6,
                    allowed_fixtures=["flat", "hanging"], allowed_profiles=["low", "high"],
                    compatibility="all listed fixture/profile combinations certified; mix only identical settings")

    def read_status(self):
        return deepcopy({k: self.state[k] for k in ("now", "setting", "batches", "active", "completed", "closed")} | {
            "orders": self.case["orders"], "capacity": self.case["capacity"],
            "shift_end": self.case["shift_end"]})

    def read_log(self):
        return deepcopy(self.state["log"])

    def _batch(self, batch_id):
        if not isinstance(batch_id, str) or batch_id not in self.state["batches"]:
            raise ToolError("UNKNOWN_BATCH")
        return self.state["batches"][batch_id]

    def draft_batch(self, batch_id, allocations):
        if not isinstance(batch_id, str) or not batch_id:
            raise ToolError("INVALID_BATCH_ID")
        if batch_id in self.state["batches"] and self._batch(batch_id)["phase"] != "DRAFT":
            raise ToolError("ONLY_DRAFT_EDITABLE")
        if not isinstance(allocations, dict) or not allocations:
            raise ToolError("INVALID_ALLOCATIONS")
        if any(k not in self.orders or not integer(q, 1) for k, q in allocations.items()):
            raise ToolError("INVALID_ALLOCATIONS")
        if sum(allocations.values()) > self.case["capacity"]:
            raise ToolError("CAPACITY_EXCEEDED")
        settings = {(self.orders[k]["fixture"], self.orders[k]["profile"]) for k in allocations}
        if len(settings) != 1:
            raise ToolError("INCOMPATIBLE_SETTINGS")
        for key, qty in allocations.items():
            used = sum(x["quantity"] for x in self.state["completed"][key])
            reserved = sum(b["allocations"].get(key, 0) for bid, b in self.state["batches"].items()
                           if bid != batch_id and b["phase"] in ("DRAFT", "SETUP", "READY"))
            if used + reserved + qty > self.orders[key]["quantity"]:
                raise ToolError("QUANTITY_ALREADY_COMPLETED_OR_RESERVED")
        self.state["batches"][batch_id] = dict(phase="DRAFT", allocations=deepcopy(allocations),
                                                     setting=list(next(iter(settings))))
        return dict(batch_id=batch_id, phase="DRAFT")

    def cancel_batch(self, batch_id):
        batch = self._batch(batch_id)
        if batch["phase"] not in ("DRAFT", "READY"):
            raise ToolError("CANCEL_AT_SAFE_BOUNDARY_ONLY")
        batch["phase"] = "CANCELLED"
        if self.state["active"] == batch_id:
            self.state["active"] = None
            self._timing = None
        return dict(batch_id=batch_id, phase="CANCELLED", at=self.state["now"])

    def start_batch(self, batch_id):
        batch = self._batch(batch_id)
        if self.state["active"] or batch["phase"] != "DRAFT":
            raise ToolError("RESOURCE_BUSY_OR_NOT_DRAFT")
        if self.state["now"] >= self.case["shift_end"]:
            raise ToolError("SHIFT_ENDED")
        if any(self.orders[k]["release"] > self.state["now"] for k in batch["allocations"]):
            raise ToolError("MATERIAL_NOT_RELEASED")
        quantity = sum(batch["allocations"].values())
        setup, processing = self.world.durations(self.state["setting"], batch["setting"],
                                                quantity, self.state["previous_batch"], 6)
        self._timing = dict(start=self.state["now"], before=list(self.state["setting"]),
                            setup=setup, processing=processing)
        batch["phase"] = "SETUP" if setup else "READY"
        self.state["active"] = batch_id
        if not setup:
            self._log_setup(batch_id, self.state["now"], complete=True)
        return dict(batch_id=batch_id, phase=batch["phase"], started_at=self.state["now"])

    def _log_setup(self, batch_id, end, complete):
        batch = self._batch(batch_id)
        self.state["log"].append(dict(kind="setup" if complete else "setup_interrupted",
            batch_id=batch_id, start=self._timing["start"], end=end,
            before=self._timing["before"], after=list(batch["setting"]),
            previous_batch=self.state["previous_batch"]))
        if complete:
            self.state["setting"] = list(batch["setting"])

    def advance(self):
        batch_id = self.state["active"]
        if batch_id is None:
            raise ToolError("NO_ACTIVE_BATCH")
        batch = self._batch(batch_id)
        setup_phase = batch["phase"] == "SETUP"
        start = self.state["now"]
        target = start + self._timing["setup" if setup_phase else "processing"]
        end = min(target, self.case["shift_end"])
        interrupted = target > end
        self.state["now"] = end
        if setup_phase:
            self._log_setup(batch_id, end, complete=not interrupted)
            batch["phase"] = "READY"
        else:
            self.state["log"].append(dict(kind="processing_interrupted" if interrupted else "processing",
                batch_id=batch_id, start=start, end=end, setting=list(batch["setting"]),
                allocations=deepcopy(batch["allocations"]), recipe_minutes=6,
                quality="NO_OUTPUT" if interrupted else "PASS"))
            if not interrupted:
                for key, qty in batch["allocations"].items():
                    self.state["completed"][key].append(dict(quantity=qty, at=end,
                        batch_id=batch_id, setting=list(batch["setting"]), quality="PASS"))
                self.state["previous_batch"] = True
            batch["phase"] = "DONE"
            self.state["active"] = None
            self._timing = None
        if interrupted:
            batch["phase"] = "INTERRUPTED"
            self.state["active"] = None
            self._timing = None
        return dict(batch_id=batch_id, phase=batch["phase"], at=end)

    def wait_until(self, minute):
        if self.state["active"]:
            raise ToolError("RESOURCE_ACTIVE_USE_ADVANCE")
        if not integer(minute) or not self.state["now"] <= minute <= self.case["shift_end"]:
            raise ToolError("INVALID_WAIT")
        self.state["log"].append(dict(kind="wait", start=self.state["now"], end=minute))
        self.state["now"] = minute
        return dict(at=minute)

    def finish(self, receipt):
        if not isinstance(receipt, dict):
            raise ToolError("INVALID_RECEIPT_FORMAT")
        for row in receipt.values():
            if not isinstance(row, dict) or set(row) != {"quantity", "completed_at"} or not all(
                    integer(row[k]) for k in row):
                raise ToolError("INVALID_RECEIPT_FORMAT")
        self.state.update(closed=True, receipt=deepcopy(receipt), end_reason="finish")
        return dict(closed=True)

    def call(self, name, arguments):
        """Only this allowlist boundary is to be exposed to an execution Agent."""
        before = digest(self.state)
        args = deepcopy(arguments)
        saved = deepcopy((self.state, self._timing, self.operations))
        try:
            if name not in PARAMS or not isinstance(args, dict):
                raise ToolError("UNKNOWN_TOOL_OR_INVALID_ARGUMENTS")
            op = None if name in READS else args.pop("operation_id", None)
            if name not in READS and (not isinstance(op, str) or not op):
                raise ToolError("OPERATION_ID_REQUIRED")
            try:
                inspect.signature(getattr(self, name)).bind(**args)
            except TypeError as exc:
                raise ToolError("INVALID_ARGUMENTS") from exc
            if op is not None and op in self.operations:
                prior = self.operations[op]
                if prior["name"] != name or prior["arguments"] != args:
                    raise ToolError("OPERATION_ID_PAYLOAD_MISMATCH")
                result = deepcopy(prior["result"])
            else:
                if self.state["closed"] and name not in READS:
                    raise ToolError("EPISODE_CLOSED")
                result = getattr(self, name)(**args)
                if op is not None:
                    self.operations[op] = dict(name=name, arguments=args, result=deepcopy(result))
        except ToolError as exc:
            self.state, self._timing, self.operations = saved
            result = dict(error=str(exc))
        self.events.append(dict(index=len(self.events), tool=name, arguments=deepcopy(arguments),
                                result=deepcopy(result), before=before, after=digest(self.state)))
        return deepcopy(result)

    def audit(self):
        return deepcopy(dict(version=VERSION, case=self.case, world=self.world.record(),
                             events=self.events, final=self.state))


def replay(audit):
    if audit["version"] != VERSION:
        raise ValueError("VERSION_MISMATCH")
    env = Environment(audit["case"], World(**audit["world"]))
    for event in audit["events"]:
        env.call(event["tool"], event["arguments"])
        if env.events[-1] != event:
            raise ValueError("REPLAY_EVENT_MISMATCH")
    if env.audit() != audit:
        raise ValueError("REPLAY_FINAL_MISMATCH")
    return env
