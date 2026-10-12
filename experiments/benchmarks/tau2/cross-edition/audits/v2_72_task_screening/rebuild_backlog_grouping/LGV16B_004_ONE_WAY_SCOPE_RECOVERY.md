# LGV16B-004 one-way scope：证据恢复、边界收窄与 evaluator 可行性

Status: `PASS_HISTORICAL_EVIDENCE_RECOVERY_AND_PROVISIONAL_BOUNDARY`

## 1. 历史证据

正式 lineage 只有 `travel_request_034`；`travel_request_035` 是完全相同的
payload，已从正式 72 题排除，不能算独立证据。

历史初始状态是 reservation `4WSQIE`：`one_way`、LAX→SFO、HAT034、
2024-05-19。用户要求保留该 outbound，并安排次日 HAT163 SFO→LAX 的
return。

| Condition | CS | CF | VS | VF | 共同路径 |
|---|---:|---:|---:|---:|---|
| E0 | 0 | 0 | 3 | 0 | 在 `4WSQIE` 中保留 outbound 并追加 reverse HAT163 |
| Historical Reference Skill | 3 | 0 | 0 | 0 | 不修改 `4WSQIE`，另建一个 SFO→LAX one-way reservation |

E0 三条 seed 960217/960218/960219 均完成用户业务目标、无 Capability error，
但都走同一个 focal append-return shortcut。Matched Reference Skill 三条均为
CS，说明合法替代路径可执行且 Skill 可修复历史错误。

需要纠正旧叙述：append 后 DB 中 `flight_type` 仍是 `one_way`，native tool
并不会把字段更新为 `round_trip`。历史 evaluator 实际根据写入后的 route
shape 检测 reverse segment。因此可保留的机制不是“观察到 trip_type 字段
发生变化”，而是“existing one-way reservation 的 mutation scope 被 reverse
return 越过”。

静态证据仍不足以直接 admission：只有一个实体/金额/措辞 surface；035 是
重复题；没有 within-scope mutation control；请求中的 “keep my existing
one-way outbound” 也可能提示 separate booking。

## 2. 收窄后的 family boundary

暂定名称：`Existing one-way reverse-return append boundary`。

Focal Trigger 是：对 existing `one_way` reservation 调用
`update_reservation_flights`，所提交的完整 ordered itinerary 在到达原始
destination 后又返回原始 origin，从而把 reverse return 塞进同一 reservation。

合法成功路径是保持原 outbound reservation 不变，再通过 `book_reservation`
建立独立的 reverse one-way return。

自然 non-trigger 包括：

- 在保持原 origin 与最终 destination 的前提下，把 one-way direct itinerary
  换成或扩展为 connecting itinerary；
- 独立创建 reverse one-way reservation。

本 family 不覆盖 third-city destination replacement、round-trip mutation、
Basic-current cabin、settlement、certificate、baggage 或 passenger cardinality。

边界目前只能定为
`PROVISIONAL__PORTFOLIO_DEDUP_WITH_LGA04_REQUIRED`。原因是它与
`G-AIR-LGA04-DESTINATION-PRESERVATION` 都可归约为 existing reservation
endpoint preservation；当前区别只是 LGV16B-004 是 append reverse-return
拓扑，而 LGA04 是直接替换 destination。建立 reconstruction contract 前必须
决定：保留两个 family，还是用一个通用 endpoint-preservation rule 覆盖两种
Trigger topology。

## 3. Deterministic evaluator 可行性

结论：`FEASIBLE__DO_NOT_REGISTER_BEFORE_LGA04_DEDUP_DECISION`。

该规则可以是 ATTEMPT-level：过滤 `WRITE update_reservation_flights`，从 replay
pre-state 读取 reservation 的 `flight_type/origin/destination/flights`，再用 flight
catalog 解析调用参数中的完整 ordered itinerary。如果初始类型是 `one_way`，
proposal 到达原 destination 后继续返回原 origin，则在该 attempt step 产生
append-only violation。

现有 v1 normalizer、isolated native replayer、rule registry interface 和
attempt-level aggregation 均可直接复用；不需要 LLM Judge、任务 ID、family
label、E0/ER label、expected answer 或 final `flight_type` 变化。预计实现复杂度
为低到中等，主要测试点是 indirect reverse route、route continuity、合法
connection expansion，以及失败 write 仍作为 attempt evidence。

本轮不把规则加入默认 v1 registry，也不建立 Gate 0 fixture。下一步先对
LGA04 做同等级 boundary recovery，并完成 portfolio 去重判断。
