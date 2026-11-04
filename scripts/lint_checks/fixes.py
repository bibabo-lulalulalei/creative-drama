"""分镜关键路径检查码的修法卡（build_lint_contract --code 的 fix 字段唯一来源）。

为什么存在：
  --code 以前只给源码坐标，模型为修一个 error 去通读 .py 源码（实测 1.4MB）。
  修法卡把「改哪个字段 / 跑哪条命令 / 读哪节教学」直接给出，让修 lint 不读源码。

卡片结构（每个码一张，字段刻意只保留四项 + hint）：
  what    一句话说明这码为什么报、修的方向是什么
  fields  涉及的文件/JSON 字段（rhythm_input.* 指 rhythm_input_ep_N.json）
  command 可直接运行的修复命令；纯创作设计类修复没有命令，用 None，照 doc 定点补教学
  doc     定点教学读取命令（read_reference --file/--section，不带 --render）
  hint    进入 drama_lint issues[].hint 的最短动作；各调用点 hint= 必须与此字面值一致
          （tests/test_lint_fixes.py 做 AST 一致性校验，防止双源漂移）

扩卡政策：
  P0 覆盖分镜关键路径码（漂移/时间输入/源覆盖/盖章/SEG 设计字段/因果/台账/状态门）。
  未覆盖码在 --code 输出 fix.available=false 并标注「修法待补」，回退源码坐标——
  严禁为没验证过修法的码编造卡片。新增卡片时同步给该码全部 issue() 调用点补 hint=。
"""
from __future__ import annotations

ALLOCATE = ("python scripts/rhythm_engine.py allocate --project-root <项目根> "
            "--input episodes/ep_N/02_分镜/rhythm_input_ep_N.json "
            "--storyboard episodes/ep_N/02_分镜/storyboard_ep_N.json --write")
PACK = ALLOCATE.replace("allocate", "pack")
LINT = "python scripts/drama_lint.py <skill根> --project-root <项目根> --stage storyboard"
STAMP_CHECK = "python scripts/stamp_review.py --project-root <项目根> --episode ep_N"
STAMP = STAMP_CHECK + " --i-did-the-review"

SB_SCHEMA = 'python scripts/read_reference.py --file references/manifests/storyboard.md --section "### storyboard_ep_N.json"'
RI_SCHEMA = 'python scripts/read_reference.py --file references/manifests/storyboard.md --section "### rhythm_input_ep_N.json"'
PIPELINE = 'python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"'
TAIL = 'python scripts/read_reference.py --file references/storyboard.md --section "### 尾态选择算法"'
REVIEW = 'python scripts/read_reference.py --file references/storyboard.md --section "### 分镜内容人工复核"'
ONE_TAKE = 'python scripts/read_reference.py --file references/storyboard.md --section "### 真正一镜到底的场面调度算法"'
REF_PLAN = 'python scripts/read_reference.py --file references/storyboard.md --section "### 视频参考输入计划"'
CAUSAL_SHOT = 'python scripts/read_reference.py --file references/storyboard.md --section "## 单镜因果检查"'
CAUSAL_LEDGER = 'python scripts/read_reference.py --file references/storyboard.md --section "### 因果链台账（causal_ledger）"'
BEAT = 'python scripts/read_reference.py --file references/storyboard.md --section "### 转换差异台账（beat_coverage）"'
WORLD = 'python scripts/read_reference.py --file references/storyboard.md --section "### 世界事实承接合同（inherited_world_facts）"'
AUDIENCE = 'python scripts/read_reference.py --file references/storyboard.md --section "### 受众执行检查"'
HIGHLIGHT = 'python scripts/read_reference.py --file references/storyboard.md --section "### 亮点绑定检查"'
TABLE15 = 'python scripts/read_reference.py --file references/storyboard.md --section "## 完整分镜表"'
DIRECTOR_CARD = 'python scripts/read_reference.py --file references/storyboard.md --section "## 每集导演总控卡"'

HINT_ALLOCATE = "改 rhythm_input 后必须重跑核算写回派生字度（禁止手填 duration_s/time_range_s）：" + ALLOCATE

FIXES: dict[str, dict] = {
    # ── 派生漂移：修法是重跑引擎，不是手改 JSON ─────────────────────────────
    "timing_output_drift": {
        "what": "shots 的派生时间字段（duration_s/time_range_s/timing_events/duration_basis）与 rhythm_input 重新核算结果不符，或 pack 前未先 allocate。",
        "fields": ["storyboard_ep_N.json: shots[].duration_s|time_range_s|timing_events|duration_basis", "storyboard_ep_N.json: duration_s/timing_input_sha256"],
        "command": ALLOCATE,
        "doc": PIPELINE,
        "hint": HINT_ALLOCATE,
    },
    "timeline_shot_set_mismatch": {
        "what": "storyboard JSON、rhythm_input 与十五列阅读稿三者的镜头集合或正式顺序不一致；引擎拒绝部分写回。",
        "fields": ["rhythm_input_ep_N.json: scenes[].shots[].shot_id", "storyboard_ep_N.json: shots[].shot_id/segment_id", "分镜_完整分镜表_ep_N.md（镜头行）"],
        "command": None,
        "doc": PIPELINE,
        "hint": "先对齐 rhythm_input、storyboard JSON 与十五列表三处的镜头编号/顺序，再重跑 allocate 与 pack --write；三处必须同源：" + PIPELINE,
    },
    "pack_drift": {
        "what": "SEG 派生产物（镜头组覆盖、request_duration_s、tail_handle_s、design_sha256）与导演设计不符；或 rhythm_input 的 beat_groups 非法/不按顺序完整覆盖。",
        "fields": ["rhythm_input_ep_N.json: scenes[].beat_groups[]", "storyboard_ep_N.json: segments[].design_sha256|request_duration_s|tail_handle_s|shot_ids"],
        "command": PACK,
        "doc": PIPELINE,
        "hint": "按报错修正 beat_groups 镜头组设计，SEG 派生字段（design_sha256/请求秒/尾余量）一律重跑 pack，禁止手填：" + PACK,
    },
    "tool_duration_unrepresentable": {
        "what": "某 beat_group 内容秒数（含尾余量）超过真实 h3 能力。保留导演设计，不自动压短/切镜/换模型，返回设计层处理。",
        "fields": ["rhythm_input_ep_N.json: scenes[].shots[].timeline[].duration_s", "beat_groups[].tail_handle"],
        "command": None,
        "doc": PIPELINE,
        "hint": "超能力是设计问题不是数字问题：调整镜头设计/过程拆分后重跑 pack，禁止改预算或自动切镜。" + PIPELINE,
    },
    "technical_handle_unresolved": {
        "what": "beat_group 的技术尾余量没有合法设计：必须是末镜结束处非 speech 过程的延续（continue_existing_process），不能加戏或拉伸前段。",
        "fields": ["rhythm_input_ep_N.json: beat_groups[].tail_handle（mode/source_event_id/description）"],
        "command": None,
        "doc": TAIL,
        "hint": "在该 beat_group 补合法 tail_handle（末镜非 speech 过程延续），再 pack --write；读 " + TAIL,
    },
    "timing_budget_input_forbidden": {
        "what": "时间输入出现 total/target/segment 预算、merge、动作/反应计数、风格时长覆盖或命令行预算参数；核算只接受声明的开始/持续/先后关系。",
        "fields": ["rhythm_input_ep_N.json: 顶层 total/target_duration/merge/预算类未知字段", "CLI: --total/--segment-budgets/--peaks"],
        "command": None,
        "doc": RI_SCHEMA,
        "hint": "删掉 --total/--segment-budgets/--peaks 等命令行预算参数，以及 rhythm_input 里的预算/配额/计数/merge 字段，只保留事件区间与先后关系；schema：" + RI_SCHEMA,
    },
    # ── rhythm_input 时间语义错误（模型 authored，手工修输入） ───────────────
    "timeline_shape_invalid": {
        "what": "rhythm_input 结构不合法：缺 episode_id/scenes/shots/timeline，或 kind/process/utterance 字段形状不对。",
        "fields": ["rhythm_input_ep_N.json: episode_id/utterances/scenes[].shots[].timeline[]"],
        "command": None,
        "doc": RI_SCHEMA,
        "hint": "按 schema 修 rhythm_input 结构后重跑 allocate；schema：" + RI_SCHEMA,
    },
    "timeline_field_unknown": {
        "what": "时间过程带了未知字段：speech 不抄台词文本（只回指 utterance），非 speech 不能携带 utterance 等。",
        "fields": ["rhythm_input_ep_N.json: timeline[] 按 kind 的合法键集合"],
        "command": None,
        "doc": RI_SCHEMA,
        "hint": "按 kind 删掉越权字段（speech 只写 utterance_id/utterance_offset_s，台词不进 timeline）；schema：" + RI_SCHEMA,
    },
    "timeline_id_duplicate": {
        "what": "event_id/line_id/源 beat ID 为空或重复；所有时间过程与源索引 ID 必须全文件唯一。",
        "fields": ["rhythm_input_ep_N.json: timeline[].event_id", "script_contract: events[].event_id/speech_lines[].line_id"],
        "command": None,
        "doc": RI_SCHEMA,
        "hint": "给冲突项改唯一非空 ID（源合同侧改动需重新走剧本确认链），再重跑 allocate。",
    },
    "timeline_number_invalid": {
        "what": "时间数值不合法：start_s 为负、duration_s 非正/非有限、bool/字符串、NaN/Inf；不接受舍入值（最多三位小数）。",
        "fields": ["rhythm_input_ep_N.json: timeline[].start_s/duration_s/after", "storyboard shots[].duration_s"],
        "command": None,
        "doc": RI_SCHEMA,
        "hint": "把时间值改成非负 start、正且有限的 duration（≤3 位小数，内部整数毫秒），再 allocate --write。",
    },
    "timeline_ref_unknown": {
        "what": "source_refs/utterance_id/after 引用了不存在的 beat:/line:/chain:/asset_state: 事实、utterance 或事件。",
        "fields": ["rhythm_input_ep_N.json: timeline[].source_refs/after", "timeline[]（speech）.utterance_id"],
        "command": None,
        "doc": RI_SCHEMA,
        "hint": "先在 script_contract/utterances/causal_ledger 里建立被引用事实，或把引用改成已存在 ID，再重跑 allocate。",
    },
    "timeline_dependency_conflict": {
        "what": "after 声明的先后关系与声明区间冲突（被依赖事件结束晚于本事件开始）。程序不自动移事件，返回导演设计。",
        "fields": ["rhythm_input_ep_N.json: timeline[].start_s/duration_s/after"],
        "command": None,
        "doc": RI_SCHEMA,
        "hint": "按真实先后改声明区间或解除错误 after，再 allocate；程序不自动排程。" + RI_SCHEMA,
    },
    "timeline_dependency_cycle": {
        "what": "after 依赖图存在自依赖或循环。",
        "fields": ["rhythm_input_ep_N.json: timeline[].after"],
        "command": None,
        "doc": RI_SCHEMA,
        "hint": "打断 after 环：保留真实先后、删掉错误回指，再重跑 allocate。",
    },
    "timing_input_invalid": {
        "what": "时间合同整体不可核对（rhythm_input 无法解析或核算前置失败），按随附异常详情修输入。",
        "fields": ["rhythm_input_ep_N.json"],
        "command": None,
        "doc": PIPELINE,
        "hint": "按随附异常修 rhythm_input 后先 allocate --write，再 pack；作业顺序：" + PIPELINE,
    },
    "speech_span_incomplete": {
        "what": "人声分片没有完整、无重叠、无遗漏地按 utterance 顺序逐字覆盖源台词；跨镜/跨 SEG 时各 compilation_map.speech_spans 拼接不回原句。",
        "fields": ["rhythm_input_ep_N.json: utterances[].timeline 分片", "segments[].speech_spans/compilation_map"],
        "command": None,
        "doc": RI_SCHEMA,
        "hint": "按 utterance_offset 顺序重排分片，逐字拼回一次完整源台词，跨 SEG 另补 speech_bridge，再重跑引擎。" + RI_SCHEMA,
    },
    "speech_span_discontinuous": {
        "what": "跨镜连续发声的绝对时间不连续，或缺跨 SEG 的真实实施方式与声音承接审校引用。",
        "fields": ["rhythm_input_ep_N.json: utterances 分片绝对时间", "video.speech_bridge（implementation/review_ref/utterance_spans）"],
        "command": None,
        "doc": RI_SCHEMA,
        "hint": "补齐时间缝隙或在跨 SEG 处写 speech_bridge 实施与审校引用；无可靠实施返回导演层。" + RI_SCHEMA,
    },
    # ── 源与确认 ─────────────────────────────────────────────────────────
    "source_revision_mismatch": {
        "what": "rhythm_input.source_script 不指向当前已确认源剧本（revision/sha256/正文 SHA 不符），或缺绑定该 revision 的真实确认（confirmation_id、source_snapshot、非空 user_message）；也可能是源索引 excerpt/台词对不上正文。",
        "fields": ["rhythm_input_ep_N.json: source_script.file/revision/sha256", "script_contract_ep_N.json: revision/source_sha256/scenes[].events/speech_lines", "00_制作控制/用户确认记录.jsonl: source_snapshot/confirmation_id"],
        "command": None,
        "doc": PIPELINE,
        "hint": "以最新已确认 script_contract 为准回填 source_script 三元与带 source_snapshot 的剧本确认记录（不伪造确认），再 allocate。" + PIPELINE,
    },
    "source_event_uncovered": {
        "what": "剧本源事件（beat）没有在 beat_coverage 中逐条处置，或处置台账结构不合法（未知/重复 beat、缺 summary 等）。",
        "fields": ["storyboard_ep_N.json: beat_coverage[]（beat_id/disposition/scene/summary/target_shots）", "script_contract: scenes[].events[]"],
        "command": None,
        "doc": BEAT,
        "hint": "给每条未覆盖 beat 补 beat_coverage 处置行（kept/compressed/moved/dropped，dropped 需真实确认），再重跑 lint。" + BEAT,
    },
    "source_line_uncovered": {
        "what": "剧本台词（speech_lines）没有经 line_id→utterance→speech 分片完整承接，或源索引结构不合法。",
        "fields": ["rhythm_input_ep_N.json: utterances[] 与 speech 分片", "script_contract: scenes[].speech_lines[].line_id/spoken_text"],
        "command": None,
        "doc": RI_SCHEMA,
        "hint": "为每条 line_id 建 utterance 并在 timeline 用 speech 分片完整承接，台词逐字不改，再 allocate。" + RI_SCHEMA,
    },
    # ── 内容复核盖章 ─────────────────────────────────────────────────────
    "content_review_stale": {
        "what": "content_review 三元指纹（源剧本/分镜设计投影/时间输入）缺失或不匹配当前设计；结构门已过，差的是真人复核盖章。",
        "fields": ["storyboard_ep_N.json: content_review.reviewed_inputs（只由盖章命令写入）"],
        "command": STAMP,
        "doc": REVIEW,
        "hint": "结构 error 清零后真人做五项复核，先无旗标预检 " + STAMP_CHECK + "，再 " + STAMP + "；禁止手填 content_review。",
    },
    "content_review_open_issue": {
        "what": "content_review 缺失，或 open_issues 非空（存在未解决的内容设计问题）；带问题不许盖章。",
        "fields": ["storyboard_ep_N.json: content_review.open_issues"],
        "command": None,
        "doc": REVIEW,
        "hint": "先按五项复核解决并清空 open_issues（改设计后重跑引擎与 lint），再重新盖章；读 " + REVIEW,
    },
    # ── storyboard JSON 与十五列/总控卡 ──────────────────────────────────
    "storyboard_shape_invalid": {
        "what": "storyboard_ep_N.json 缺少 shots 或 segments 数组（pack 后才有 SEG，先跑作业顺序）。",
        "fields": ["storyboard_ep_N.json: shots[]/segments[]"],
        "command": PACK,
        "doc": SB_SCHEMA,
        "hint": "补齐 shots；segments 由 pack 生成后再补模型 authored 字段，不要手写 SEG 骨架。schema：" + SB_SCHEMA,
    },
    "storyboard_fifteen_columns_missing": {
        "what": "source_markdown 指向的完整分镜表里没有十五列表格。",
        "fields": ["分镜_完整分镜表_ep_N.md（表头必须是规定的十五列）"],
        "command": None,
        "doc": TABLE15,
        "hint": "把完整分镜表改成规定十五列后重跑 lint；列要求：" + TABLE15,
    },
    "storyboard_source_markdown_missing": {
        "what": "source_markdown 约定路径下的十五列完整分镜表文件不存在。",
        "fields": ["episodes/ep_N/02_分镜/分镜_完整分镜表_ep_N.md"],
        "command": None,
        "doc": TABLE15,
        "hint": "在约定文件名下落盘十五列完整分镜表（只此一份），再重跑 lint。" + TABLE15,
    },
    "storyboard_source_markdown_invalid": {
        "what": "storyboard.source_markdown 没有指向约定的唯一十五列分镜表路径。",
        "fields": ["storyboard_ep_N.json: source_markdown"],
        "command": None,
        "doc": SB_SCHEMA,
        "hint": "把 source_markdown 改成约定相对路径（episodes/ep_N/02_分镜/分镜_完整分镜表_ep_N.md）。",
    },
    "director_control_card_missing": {
        "what": "分镜阶段必须存在唯一导演总控卡。",
        "fields": ["episodes/ep_N/02_分镜/导演总控卡_ep_N.md"],
        "command": None,
        "doc": DIRECTOR_CARD,
        "hint": "落盘唯一导演总控卡（整场观看关系/视点/调度/摄影/剪辑意图），再重跑 lint。" + DIRECTOR_CARD,
    },
    "director_control_card_invalid": {
        "what": "storyboard.director_control_card 没有指向约定的唯一总控卡路径。",
        "fields": ["storyboard_ep_N.json: director_control_card"],
        "command": None,
        "doc": SB_SCHEMA,
        "hint": "把 director_control_card 改成约定路径 episodes/ep_N/02_分镜/导演总控卡_ep_N.md。",
    },
    # ── SEG 模型 authored 字段（pack 后人工填写，重跑 pack 会身份合并保留） ──
    "segment_shot_mode_invalid": {
        "what": "SEG 的 shot_mode 缺失或不在 edited|true_one_take。",
        "fields": ["storyboard_ep_N.json: segments[].shot_mode"],
        "command": None,
        "doc": SB_SCHEMA,
        "hint": "按片段职责填 shot_mode=edited（默认）或 true_one_take（且只能含 1 个镜头）；schema：" + SB_SCHEMA,
    },
    "segment_tail_mode_invalid": {
        "what": "SEG 的 tail_mode 缺失或不在 continuous_motion|cuttable_completion|stable_hold|loop_continuation。",
        "fields": ["storyboard_ep_N.json: segments[].tail_mode/tail_selection_reason"],
        "command": None,
        "doc": TAIL,
        "hint": "按尾态选择算法给每段填合法 tail_mode 与 tail_selection_reason；读 " + TAIL,
    },
    "intermediate_stable_hold_reason_missing": {
        "what": "中间片段使用 stable_hold 时必须填写 tail_hold_reason 说明稳收依据（最终 SEG 默认 stable_hold 不需要）。",
        "fields": ["storyboard_ep_N.json: segments[].tail_hold_reason"],
        "command": None,
        "doc": TAIL,
        "hint": "中间段要么改用 continuous_motion/cuttable_completion，要么在 tail_hold_reason 写清稳收理由。" + TAIL,
    },
    "segment_density_profile_invalid": {
        "what": "SEG 的 density_profile 取值不在 high_density_short|dialogue_emotional|suspense_build|micro_film|custom。",
        "fields": ["storyboard_ep_N.json: segments[].density_profile/density_rationale"],
        "command": None,
        "doc": SB_SCHEMA,
        "hint": "该字段是可选定性标注；填写时取合法枚举，custom 在 density_rationale 说明，不确定就整字段删除。",
    },
    "true_one_take_shot_count_invalid": {
        "what": "shot_mode=true_one_take 的 SEG 必须且只能引用一个 SHOT，并在总控卡证明无硬切/隐藏切/遮挡伪切/匹配剪辑/时间跳跃。",
        "fields": ["storyboard_ep_N.json: segments[].shot_mode/shot_ids/one_take_route", "导演总控卡_ep_N.md"],
        "command": None,
        "doc": ONE_TAKE,
        "hint": "不是严格一镜到底就改回 edited；确属一镜到底则收敛为单镜头并补 one_take_route 与总控卡证明。" + ONE_TAKE,
    },
    "reference_input_plan_missing": {
        "what": "每个 SEG 都必须有 reference_input_plan 数组（该段无参考图时填 []，不能缺字段）。",
        "fields": ["storyboard_ep_N.json: segments[].reference_input_plan"],
        "command": None,
        "doc": REF_PLAN,
        "hint": "给每个 SEG 补 reference_input_plan：无图参考的段填空数组 []；读 " + REF_PLAN,
    },
    "reference_input_plan_invalid": {
        "what": "reference_input_plan 必须是对象数组，每项含 order/role/planned_source/opening_binding/adopt/exclude。",
        "fields": ["storyboard_ep_N.json: segments[].reference_input_plan[]"],
        "command": None,
        "doc": REF_PLAN,
        "hint": "把计划项改成合法对象（order 从 1 连续、role 合法、planned_source 形如 CHR001_v01（名称））；读 " + REF_PLAN,
    },
    "reference_input_plan_incomplete": {
        "what": "参考计划项缺少 required 字段（opening_binding/adopt/exclude 等）。",
        "fields": ["storyboard_ep_N.json: reference_input_plan[].order/role/planned_source/opening_binding/adopt/exclude"],
        "command": None,
        "doc": REF_PLAN,
        "hint": "逐项补齐缺失字段；opening_binding 必须含同序 <图片N> 标记，adopt/exclude 写清继承与排除。" + REF_PLAN,
    },
    "reference_role_invalid": {
        "what": "参考图 role 不在合法职责枚举内，或与资产类型不匹配。",
        "fields": ["storyboard_ep_N.json: reference_input_plan[].role/planned_source"],
        "command": None,
        "doc": REF_PLAN,
        "hint": "按 planned_source 的资产类型选合法 role（身份图/状态图/场景/道具/风格各有对应职责）；读 " + REF_PLAN,
    },
    "opening_binding_marker_missing": {
        "what": "第 N 张参考图的 opening_binding 缺少同序 <图片N>/<IMGN> 标记，开场首镜旁注与计划顺序对不上。",
        "fields": ["storyboard_ep_N.json: reference_input_plan[].opening_binding", "十五列分镜表开场首镜旁注"],
        "command": None,
        "doc": REF_PLAN,
        "hint": "在 opening_binding 文本里写同序 <图片N> 标记，并在开场首镜对应旁注引用同一标记。" + REF_PLAN,
    },
    # ── 单镜因果与因果链台账 ─────────────────────────────────────────────
    "causal_role_missing": {
        "what": "每个 shot 都必须声明 causal_role（reaction/establish/evidence/result/transition）。",
        "fields": ["storyboard_ep_N.json: shots[].causal_role"],
        "command": None,
        "doc": CAUSAL_SHOT,
        "hint": "按该镜在因果链中的职责逐镜补 causal_role（五选一），transition 也要显式声明；读 " + CAUSAL_SHOT,
    },
    "causal_role_invalid": {
        "what": "shots[].causal_role 不在 reaction/establish/evidence/result/transition 枚举内。",
        "fields": ["storyboard_ep_N.json: shots[].causal_role"],
        "command": None,
        "doc": CAUSAL_SHOT,
        "hint": "改成五个合法枚举之一，并保证配套字段齐（reaction/result 需 responds_to，evidence 需 evidence_visibility）。" + CAUSAL_SHOT,
    },
    "evidence_visibility_invalid": {
        "what": "shots[].evidence_visibility 不在 in_frame/audio_only/partial/occluded。",
        "fields": ["storyboard_ep_N.json: shots[].evidence_visibility"],
        "command": None,
        "doc": CAUSAL_SHOT,
        "hint": "按证据实际呈现方式选四枚举之一；选 occluded 必须在 establishes 写遮挡理由与揭示点。" + CAUSAL_SHOT,
    },
    "occluded_establishes_missing": {
        "what": "evidence_visibility=occluded 的镜头必须在 establishes 写明遮挡理由与揭示点，否则证据链不可核对。",
        "fields": ["storyboard_ep_N.json: shots[].establishes/evidence_visibility"],
        "command": None,
        "doc": CAUSAL_SHOT,
        "hint": "在 establishes 补「为何遮挡 + 在哪一镜揭示」；做不到可见承诺就改 evidence_visibility。" + CAUSAL_SHOT,
    },
    "causal_ledger_missing": {
        "what": "storyboard 必须有 causal_ledger 数组；本集确无反应/证据依赖链时登记空数组。",
        "fields": ["storyboard_ep_N.json: causal_ledger"],
        "command": None,
        "doc": CAUSAL_LEDGER,
        "hint": "补 causal_ledger 字段：有跨镜证据反应链就逐条建链，没有就填空数组 []；读 " + CAUSAL_LEDGER,
    },
    "causal_seam_invariant_unknown": {
        "what": "证据跨 SEG 传递给反应位，但在连续性账本里找不到对应 seam，无法核对 required_invariants 派生。",
        "fields": ["连续性账本/片段衔接卡 seams[].seam_id", "causal_ledger[].visibility_contract"],
        "command": None,
        "doc": CAUSAL_LEDGER,
        "hint": "先在连续性账本为该 SEG 接缝登记 seam（含 required_invariants），再让因果链引用同 seam_id。" + CAUSAL_LEDGER,
    },
    "causal_seam_invariant_missing": {
        "what": "证据跨 SEG 传递时，该 seam 的 required_invariants 必须派生写入因果链 visibility_contract 条款。",
        "fields": ["causal_ledger[].visibility_contract", "seams[].required_invariants"],
        "command": None,
        "doc": CAUSAL_LEDGER,
        "hint": "把 seam.required_invariants 逐条翻译成该链 visibility_contract 里的可见/可听承诺。" + CAUSAL_LEDGER,
    },
    # ── 顶层必填台账 ─────────────────────────────────────────────────────
    "beat_coverage_missing": {
        "what": "storyboard 必须有 beat_coverage：剧本每条动作/事件去向的多对多台账。",
        "fields": ["storyboard_ep_N.json: beat_coverage"],
        "command": None,
        "doc": BEAT,
        "hint": "为 script_contract 每个 event_id 建一条处置行并绑定真实 target_shots；读 " + BEAT,
    },
    "world_facts_missing": {
        "what": "storyboard 必须有 inherited_world_facts：从剧本继承的季节/节日/时辰/天气/地点类世界事实。",
        "fields": ["storyboard_ep_N.json: inherited_world_facts"],
        "command": None,
        "doc": WORLD,
        "hint": "把剧本中的世界事实逐条登记（fact_id/category/statement/source 剧本出处），无出处的感官细节删除。" + WORLD,
    },
    "audience_execution_missing": {
        "what": "storyboard 必须登记 audience_execution：从已确认 audience_plan 四项派生并绑定真实场次/镜头。",
        "fields": ["storyboard_ep_N.json: audience_execution（viewing_focus/emotional_payoff/platform_viewing_context/expression_boundaries）"],
        "command": None,
        "doc": AUDIENCE,
        "hint": "四项各填 source_field（audience_plan.<字段>）、逐字 contract 与 scene_or_shot_ids，不重新画像；读 " + AUDIENCE,
    },
    "highlight_bindings_missing": {
        "what": "storyboard.highlight_bindings 必须是数组并覆盖剧本全部主要亮点（primary）。",
        "fields": ["storyboard_ep_N.json: highlight_bindings[]", "script_contract: highlight_ledger（role=primary）"],
        "command": None,
        "doc": HIGHLIGHT,
        "hint": "为 ledger 中每个 primary 亮点建绑定（SEG/trigger-change-feedback-result/payoff/reaction/执行说明）；读 " + HIGHLIGHT,
    },
}
