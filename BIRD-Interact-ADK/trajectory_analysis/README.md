# Trajectory Analysis 目录结构

`trajectory_analysis/` 与 `results/` 同级，均位于工作区根目录。`results/` 保存实验结果，`trajectory_analysis/` 保存对应实验转化后方便人阅读的材料。

两者按相同的模型、simulator、实验名组织，三级目录名称必须与对应的 `results/` 路径完全一致：

```text
results/<agent模型目录>/<simulator目录>/<实验名>/
trajectory_analysis/<agent模型目录>/<simulator目录>/<实验名>/
```

例如：

```text
results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/baseline72_v1_20261028/
trajectory_analysis/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/baseline72_v1_20261028/
```

分析文件放在对应实验目录内；`task_cards/` 与 `trajectory/` 位于该实验目录下，互为同级目录。
