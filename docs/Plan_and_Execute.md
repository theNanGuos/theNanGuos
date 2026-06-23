```markdown
# Task Plan 与 LangGraph 执行关系说明

## 1. task_plan 是什么

`task_plan` 是由 `ConductorAgent` 生成的结构化执行计划。

它的作用是描述：

- 本次任务要完成什么目标。
- 任务被拆成哪些步骤。
- 每一步由哪个 agent 或 tool 执行。
- 每一步需要哪些输入。
- 每一步会产生什么输出。
- 步骤之间有什么依赖关系。

示例：

```json
{
  "goal": "Generate a 90-second Chinese lo-fi pop song for Suno",
  "steps": [
    {
      "id": "lyrics",
      "actor": "LyricsAgent",
      "task": "Generate sectioned Chinese lyrics",
      "input_keys": ["song_spec"],
      "output_key": "lyrics_result",
      "depends_on": ["song_spec"]
    },
    {
      "id": "music_plan",
      "actor": "MusicPlannerAgent",
      "task": "Plan structure, BPM, key, chords, melody intent",
      "input_keys": ["song_spec", "lyrics_result"],
      "output_key": "music_plan_result",
      "depends_on": ["lyrics"]
    },
    {
      "id": "arrangement",
      "actor": "ArrangementAgent",
      "task": "Generate instrumentation and Suno style prompt",
      "input_keys": ["song_spec", "music_plan_result"],
      "output_key": "arrangement_result",
      "depends_on": ["music_plan"]
    }
  ]
}
```

## 2. task_plan 是 LangGraph 内置格式吗

不是。

`task_plan` 是我们自己定义的数据结构，不是 LangGraph 内置格式。

LangGraph 不会天然理解：

```json
{
  "steps": [...]
}
```

也不会自动根据 `task_plan` 执行里面的步骤。

LangGraph 只负责：

1. 保存和传递 `state`。
2. 执行我们定义好的 node。
3. 根据我们定义好的边或条件边决定下一个 node。
4. 把每个 node 返回的内容合并回 `state`。

所以，`task_plan` 必须由我们在 node 函数或 conditional edge 函数里主动读取和使用。

## 3. LangGraph 怎么读取 task_plan

LangGraph 的每个节点函数都会接收一个 `state`。

例如：

```python
def lyrics_node(state):
    ...
```

这个 `state` 可以理解为当前任务的共享工作记忆。

里面可能包含：

```python
{
    "song_spec": {...},
    "task_plan": {...},
    "lyrics_result": None
}
```

节点函数可以从 `state` 中读取 `task_plan`：

```python
step = find_step(state["task_plan"], "lyrics")
```

这句话的意思是：

从 `task_plan` 里找到 id 为 `"lyrics"` 的那一步。

## 4. find_step 是 LangGraph 内置函数吗

不是。

`find_step` 不是 LangGraph 内置函数，而是我们自己写的普通辅助函数。

例如：

```python
def find_step(task_plan: dict, step_id: str) -> dict:
    for step in task_plan["steps"]:
        if step["id"] == step_id:
            return step
    raise ValueError(f"Step not found: {step_id}")
```

它的作用只是：

```text
从 task_plan.steps 中找到 id 等于 step_id 的步骤。
```

例如：

```python
step = find_step(state["task_plan"], "lyrics")
```

如果 `task_plan` 是：

```json
{
  "steps": [
    {
      "id": "lyrics",
      "task": "Generate sectioned Chinese lyrics"
    }
  ]
}
```

那么 `step` 就是：

```python
{
    "id": "lyrics",
    "task": "Generate sectioned Chinese lyrics"
}
```

## 5. 字段一定要叫 steps 吗

不一定。

`steps` 不是 LangGraph 要求的字段名，而是我们自己设计的字段名。

也可以叫：

```json
{
  "tasks": [...]
}
```

或者：

```json
{
  "plan_items": [...]
}
```

如果字段叫 `tasks`，辅助函数就要改成：

```python
def find_task(task_plan: dict, task_id: str) -> dict:
    for task in task_plan["tasks"]:
        if task["id"] == task_id:
            return task
    raise ValueError(f"Task not found: {task_id}")
```

所以核心规则是：

```text
字段名由我们自己决定。
但代码读取方式必须和字段名一致。
```

如果代码写的是：

```python
state["task_plan"]["steps"]
```

那 `task_plan` 里就必须有 `steps`。

如果代码写的是：

```python
state["task_plan"]["tasks"]
```

那 `task_plan` 里就必须有 `tasks`。

## 6. lyrics_node 示例解释

示例代码：

```python
def lyrics_node(state):
    step = find_step(state["task_plan"], "lyrics")
    result = lyrics_agent.run(
        song_spec=state["song_spec"],
        instruction=step["task"],
    )
    return {"lyrics_result": result}
```

逐行解释：

### 1. 定义 LangGraph 节点

```python
def lyrics_node(state):
```

定义一个 LangGraph 节点函数。

`state` 是 LangGraph 传入的共享状态。

### 2. 从计划中找到歌词任务

```python
step = find_step(state["task_plan"], "lyrics")
```

从 `task_plan` 中找到 id 为 `"lyrics"` 的任务步骤。

### 3. 调用 LyricsAgent

```python
result = lyrics_agent.run(
    song_spec=state["song_spec"],
    instruction=step["task"],
)
```

调用 `LyricsAgent` 生成歌词。

传入两个信息：

- `song_spec`：歌曲规格，例如语言、风格、情绪、曲式。
- `instruction`：`task_plan` 中对歌词任务的说明。

### 4. 把结果写回 state

```python
return {"lyrics_result": result}
```

LangGraph 会把这个返回值合并回原来的 `state`。

原来的状态可能是：

```python
{
    "song_spec": {...},
    "task_plan": {...}
}
```

执行后变成：

```python
{
    "song_spec": {...},
    "task_plan": {...},
    "lyrics_result": {...}
}
```

后续节点，例如 `music_planner_node`，就可以读取 `lyrics_result`。

## 7. 推荐执行方式

本项目 MVP 推荐使用固定图，而不是动态图。

### 推荐方案：固定 LangGraph + task_plan 作为解释性计划

流程：

```text
ConductorAgent 生成 task_plan
-> LangGraph 按固定节点执行
-> 每个节点从 task_plan 读取自己的任务说明
-> collaboration_log.json 记录 task_plan 和实际执行结果
```

固定图示例：

```text
conductor_node
  -> lyrics_node
  -> music_planner_node
  -> arrangement_node
  -> validate_node
  -> build_suno_request_node
  -> submit_or_skip_node
  -> poll_suno_node
```

这种方式的优点：

- 实现简单。
- 流程稳定。
- 容易测试。
- 仍然能体现 agent 的规划能力。
- 不会让 LLM 动态决定不存在的节点。

## 8. 不推荐 MVP 使用完全动态图

另一种方式是让 LangGraph 根据 `task_plan` 动态决定下一个节点：

```python
def route_next(state):
    next_step = state["task_plan"]["steps"][state["current_step_index"]]
    return next_step["id"]
```

然后通过条件边映射：

```python
graph.add_conditional_edges(
    "planner_node",
    route_next,
    {
        "lyrics": "lyrics_node",
        "music_plan": "music_planner_node",
        "arrangement": "arrangement_node"
    }
)
```

但这种方式有额外复杂度：

- 仍然要提前注册所有可执行节点。
- 需要处理 LLM 生成非法 actor 的情况。
- 需要维护 `current_step_index`、`completed_steps` 等状态。
- 对本项目 MVP 来说收益不大。

所以不建议作为第一版实现。

## 9. 最终结论

`task_plan` 是：

```text
ConductorAgent 生成的结构化任务计划。
```

LangGraph 是：

```text
执行节点和管理状态的编排框架。
```

二者关系是：

```text
task_plan 存在 GraphState 中。
LangGraph 不会自动理解 task_plan。
我们在 node 函数或条件边函数中读取 task_plan。
节点根据 task_plan 中的任务说明执行对应 agent。
执行结果再写回 GraphState。
```

推荐设计：

```text
固定 LangGraph 节点流程 + task_plan 作为规划说明和日志依据
```

这样既能满足作业中“agent 推理/规划”的要求，也能保持系统实现简单、稳定、可测试。
```