# OpenModelica Demo 演示脚本

## 1. 开场

本 Demo 展示 OpenTwins 数字孪生平台如何与 OpenModelica 机理仿真集成。OpenTwins 负责实时状态镜像和历史数据，OpenModelica 负责从当前状态出发进行未来演化推演和 what-if 分析。

## 2. 启动

```bash
cd /home/teng/programmings/git/opentwins
./deploy_all.sh --demo-only
./watch_demo.sh --status
```

打开：

- `http://<SERVER_IP>:5173`
- `http://<SERVER_IP>:8010/docs`
- `http://<SERVER_IP>:8020/docs`

## 3. 展示实时孪生

1. 打开前端首页。
2. 观察 3 个发酵罐颜色和状态标签。
3. 说明 Python simulator 每 5 秒发布一次 MQTT merge-patch。
4. 说明 Ditto 中的 `wine:tank_01/02/03` Feature 会实时变化。

## 4. 展示 OpenModelica 基线预测

1. 点击 `tank_01`。
2. 切到“仿真”页。
3. 找到“OpenModelica 机理仿真”面板。
4. 说明曲线含义：
   - Brix 下降：糖被酵母消耗。
   - Alcohol 上升：糖转化为酒精。
   - Progress 上升：发酵完成度提升。
   - Quality 基线：由温度阈值和完成度计算。
5. 说明此预测不改变 Ditto 当前状态，是从当前状态复制出一条未来轨迹。

## 5. 展示 tank_02 降温 what-if

1. 点击 `tank_02`。
2. 温度扰动选择 `-5 C`。
3. 点击“运行 OpenModelica What-if”。
4. 对比基线和 what-if 的末端质量分。
5. 说明 tank_02 是红葡萄酒高温异常罐，降温会改善质量评分或防止风险恶化。

## 6. 展示 tank_03 升温敏感性

1. 点击 `tank_03`。
2. 温度扰动选择 `+5 C`。
3. 点击“运行 OpenModelica What-if”。
4. 说明白葡萄酒最适温度是 14 C，warning/critical 阈值低于红葡萄酒。
5. 同样的升温扰动对白葡萄酒更敏感，这体现了 Modelica 参数化模型的差异化能力。

## 7. Swagger 佐证

打开 `http://<SERVER_IP>:8020/docs`，运行 `/api/modelica/simulate`，展示返回 points。

打开 `http://<SERVER_IP>:8010/docs`，运行 `/api/wine/tanks/tank_01/modelica-prediction`，说明 WineTwin Service 已经把 Ditto 当前状态自动映射为 Modelica 请求。

## 8. 结束语

这个集成形成了“实时孪生状态 + 机理模型推演 + what-if 决策建议”的闭环。后续可以把 `WineFermentation.ContinuationFermentation` 替换为更精细的 Monod 动力学、FMU 或经过真实数据标定的模型，而 OpenTwins、WineTwin Service 和前端接口都不需要重写。
