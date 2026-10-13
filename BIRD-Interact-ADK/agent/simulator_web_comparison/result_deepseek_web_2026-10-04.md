# 网页 simulator 对照原始结果

复制本文件，为每个平台/模式单独保存一份，例如 `result_kimi3_web_2026-10-04.md`。原始回复先保存，再人工评分；不要让被测模型看到评分参考。

- 测试集：web-sim-v1 / 2026-10-04
- 页面显示的模型/模式原文：deepseek（未知具体模型）
- 思考/快速/搜索等开关：深度思考关，联网搜索关
- 自定义指令/记忆：待填；关闭
- 备注/中断/限流：无

## C01 · alien_5 · 错误二选一与结果结构

- 尝试编号：1
- 输入：01_COPYABLE_CASES.md 的 C01 完整 text 块（如有任何改动必须附完整输入）

### 原始回复

````text
Neither A nor B. I want one aggregated row per modulation type, showing the modulation type, signal count, average MCS, and average SNR, plus one JSON object on that row mapping each signal's record ID to its own MCS and SNR.
````

## C02 · alien_5 · 分组对象纠错

- 尝试编号：1
- 输入：01_COPYABLE_CASES.md 的 C02 完整 text 块（如有任何改动必须附完整输入）

### 原始回复

````text
Group by modulation type, not encoding method. The request is about modulation types, and the "complexity measure" refers to the Modulation Complexity Score while the "quality ratio" refers to average SNR.
````

## C03 · alien_5 · 分组和指标同时纠错

- 尝试编号：1
- 输入：01_COPYABLE_CASES.md 的 C03 完整 text 块（如有任何改动必须附完整输入）

### 原始回复

````text
Yes.
````

## C04 · alien_5 · 指标名称澄清

- 尝试编号：1
- 输入：01_COPYABLE_CASES.md 的 C04 完整 text 块（如有任何改动必须附完整输入）

### 原始回复

````text
Average complexity measure means the average Modulation Complexity Score (MCS). Average quality ratio means the average signal-to-noise ratio (SNR).

The intended grouping is by modulation type, and the threshold is at least 5 occurrences — not “several” and not more than 5.
````

## C05 · alien_5 · 纠正此前错误对话

- 尝试编号：1
- 输入：01_COPYABLE_CASES.md 的 C05 完整 text 块（如有任何改动必须附完整输入）

### 原始回复

````text
No — group by modulation type, and the metrics are average Modulation Complexity Score and average signal-to-noise ratio, not ECI or SNQI.
````

## C06 · alien_1 · weather 与 SNQI/SNR

- 尝试编号：1
- 输入：01_COPYABLE_CASES.md 的 C06 完整 text 块（如有任何改动必须附完整输入）

### 原始回复

````text
Weather conditions, and usable signals are those with SNQI greater than zero—not SNR.
````

## C07 · alien_3 · LIF 与类别标签

- 尝试编号：1
- 输入：01_COPYABLE_CASES.md 的 C07 完整 text 块（如有任何改动必须附完整输入）

### 原始回复

````text
Not exactly. I mean events with high lunar interference, based on the lunar interference factor — not a generic “High” label. The grouping should be by observatory and current moon phase, and the count should be of high lunar interference events.
````

## C08 · alien_5 · 拒绝泄漏 SQL

- 尝试编号：1
- 输入：01_COPYABLE_CASES.md 的 C08 完整 text 块（如有任何改动必须附完整输入）

### 原始回复

````text
Sorry, I can clarify my requirements, but cannot provide SQL or database implementation details.
````

## C09 · gaming_7 · DS 求和与平均

- 尝试编号：1
- 输入：01_COPYABLE_CASES.md 的 C09 完整 text 块（如有任何改动必须附完整输入）

### 原始回复

````text
1. DS is calculated from drop height, bend force, twist angle, and USB connector durability — not a stored column.
2. High endurance means PER above 9.0. Correct the premise that PER > 9.0 is just an example; it is the actual threshold.
3. Show the numeric IP rating levels, not the raw IPX codes.
````

## C10 · cybermarket_2 · Trusted Vendor 条件完整性

- 尝试编号：1
- 输入：01_COPYABLE_CASES.md 的 C10 完整 text 块（如有任何改动必须附完整输入）

### 原始回复

````text
Filter by the Trusted Vendor criteria: verification level of Advanced or Premium, a dispute rate under 5%, and more than 90 days of activity, plus a Vendor Trust Index above 80. Sort by Vendor Trust Index descending.
````

