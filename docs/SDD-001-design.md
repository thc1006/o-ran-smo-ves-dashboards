# SDD-001 — `o-ran-smo-ves-dashboards` 系統設計文件

- **狀態：** Draft（待 MVP 階段驗證 schema 後進入 Proposed）
- **日期：** 2026-04-19
- **作者：** thc1006 @ NYCU WinLab
- **版本：** 0.1.0 draft
- **前置研究：** `../../RESEARCH_NOTES_2026-04-17.md`、`../../CLAUDE.md`
- **姊妹專案：** `../pytest-ves/ADR-001-design.md`

---

## 1. 引言與動機

### 1.1 問題陳述
到 2026-04 為止：

- O-RAN SC 已有 `nonrtric-plt-ranpm` + `nonrtric-plt-influxlogger` 作為官方 VES → Kafka → InfluxDB 的 PM 收集管線
- Grafana.com dashboards 目錄中已有 **OAI 5G para（ID 22297）** 等走 Prometheus + KPM xApp 路徑的儀表板
- NIST `O-RAN-Testbed-Automation`、OpenRAN Gym、BubbleRAN 等提供 KPM Grafana dashboard 教學
- Aarna AMCOP 有 O-RAN SMO 儀表板但**商業閉源**
- LFN 5G Super Blueprint 的 results dashboard 仍**開發中**

**尚未被佔領的縫隙：** 針對 `nonrtric-plt-influxlogger` 寫入 InfluxDB 的 VES 事件（fault / measurement / heartbeat / stndDefined），**沒有公開可匯入、Flux/InfluxQL query 對齊實際 schema、可直接用於 SMO 觀測性的 Grafana dashboard 包**。

### 1.2 目標
1. 提供 4–6 份可直接匯入 Grafana 的 dashboard JSON，對應 VES 4 個主要 domain
2. 隨附 docker-compose / kind 兩種本地示範環境，讓人 10 分鐘內看到效果
3. 發佈至 grafana.com/grafana/dashboards 獲得社群曝光
4. 以 Git Sync + CI 流程讓 dashboard 本身也做 as-code

### 1.3 非目標
- KPM xApp / Prometheus 路徑的 RAN 效能 dashboard（已被 OAI 5G para / NIST 佔位，進入競爭無意義）
- VoiceQuality / mobileFlow 等不屬於 O-RAN SMO 核心的 VES domain
- AI-driven anomaly detection（可於 v0.3.0+ 再評估是否用本地 NVIDIA GPU 加上 Grafana ML 面板）

---

## 2. 關鍵設計決策總覽

| # | 決策 | 選擇 | 理由簡述 |
|---|---|---|---|
| D1 | Query 語言 | **InfluxQL 為主，Flux 為過渡相容** | InfluxDB 3 核心 2025-04-15 GA 改走 SQL/InfluxQL；2026-05-27 Docker latest 跳 3；Flux 2023 起維護模式；InfluxQL 是 2.x↔3.x 同時最佳解 |
| D2 | Dashboard 架構語言 | **Grafana Dashboard JSON schema v2（Grafana 12+）** | 2025-05 公開預覽，配合 Dynamic Dashboards 與 Git Sync；若要程式化可另供 Foundation SDK (Python) 版本 |
| D3 | 資料來源對齊目標 | **`nonrtric-plt-influxlogger` 預設 schema** | 這是 O-RAN SC 官方 VES→InfluxDB 實作；若改接 Telegraf/Benthos 再提供 alternate query set |
| D4 | 開發/測試環境 | **本地 kind 叢集 + docker-compose 雙軌** | 使用者本地有 kind；docker-compose 作為 contributor 低門檻環境；NVIDIA GPU v1 非關鍵 |
| D5 | 樣本資料來源 | **姊妹專案 `pytest-ves` 作 seeder** | 綜效；避免二次實作事件產生器 |
| D6 | Dashboard 工作流 | **Grafana 12 Git Sync（bidirectional）** | 2025-05 GA；UI 編輯直接回推 repo，PR 審核後合併；符合 GitOps |
| D7 | 發佈管道 | **GitHub repo（canonical） + grafana.com 每個 dashboard 個別 ID + Helm library chart（ConfigMap 封裝）** | 三層覆蓋：開發者從 repo、Grafana 使用者從 grafana.com ID、K8s 使用者從 Helm |

每個決策細節於 §5–§7 展開。

---

## 3. 相關利害關係人

| 角色 | 關心什麼 |
|---|---|
| O-RAN SMO 研究者（學界） | 快速看到 VES 資料；能客製 |
| rApp 開發者 | fault/measurement 事件的時序圖、alarm 列表 |
| SMO SRE | heartbeat 健康、告警高峰、RAN 資源狀況 |
| ranpm Chart 使用者 | 安裝完 chart 後馬上有 dashboard 可用 |
| NYCU WinLab（自用） | 教學與研究平台的可視化 |
| Grafana.com 瀏覽使用者 | 匯入一個 ID 就能用的儀表板 |

---

## 4. 資料模型

### 4.1 `nonrtric-plt-influxlogger` InfluxDB schema（已確認事實）
官方文件：<https://docs.o-ran-sc.org/projects/o-ran-sc-nonrtric-plt-ranpm/en/latest/influxlogger/overview.html>

> Each measured resource is mapped to a measurement in Influx, with the name of the measurement being the Full Distinguished Name of the resource. Each measurement type (counter) is mapped to a field, with the name of the field being the same as the name of the measurement type.

### 4.2 推導的 Line Protocol 範例（v0.1.0 待本地驗證）
```
<full-distinguished-name>[,<tag_key>=<tag_value>...] <counter1>=<v>,<counter2>=<v>... <ts_ns>
```
具體例（推測，**必須用 kind 實測確認**）：
```
SubNetwork=Europe\,ManagedElement=gNB-1\,NRCellDU=1 \
    DRB.PdcpSduVolumeDl_Filter=102400,DRB.PdcpSduVolumeUl_Filter=204800 \
    1713571200000000000
```
- measurement name 含逗號，需 escape（influx line protocol 規則）
- tag 結構**尚未在 v0.1.0 階段確認**—需於 §9.1 MVP step 1 實測

### 4.3 VES → InfluxDB 對映表（已確認 + 待驗證）
| VES domain | 在 influxlogger 中的落點 | 驗證狀態 |
|---|---|---|
| measurement（3GPP perf3gpp） | measurement = FDN；fields = PM counter names；timestamp = `collectionBeginTime` 或 `collectionEndTime` | **已確認（官方 spec）** |
| fault | **不確定**：influxlogger 文件聚焦 PM；fault 走向可能是另一個 bucket 或不落 Influx | **需於 MVP phase 1 實測** |
| heartbeat | 同上 | **需實測** |
| stndDefined | 同上；stndDefinedNamespace 可能作 tag | **需實測** |

### 4.4 若 fault / heartbeat 不落 influxlogger 的備案
- **備案 A：** Design 的 4 份 dashboard 全部以 measurement domain 為主，fault/heartbeat 僅在 measurement 的 Annotations overlay 中出現
- **備案 B：** 寫一個薄轉接 adapter（100–200 LOC）把 fault/heartbeat 事件也寫 InfluxDB，dashboard 對應其 schema
- **備案 C：** 建議使用者對 fault/heartbeat 用 Loki + Grafana logs 面板（不同資料源），本 pack 明確標記「僅 measurement」

§9.1 MVP phase 1 完成後才能決定走哪條。

---

## 5. 系統架構

### 5.1 元件圖（純文字）

```
                   +-------------------+
                   |  pytest-ves CLI   |  (姊妹專案，v0.2.0)
                   |  灌入樣本事件      |
                   +---------+---------+
                             |
                             v  VES POST
                   +-------------------+
                   | nonrtric-plt-ranpm|
                   |  VES Collector    |
                   +---------+---------+
                             |
                             v  Kafka topic
                   +-------------------+
                   | nonrtric-plt-     |
                   | influxlogger      |
                   +---------+---------+
                             |
                             v  InfluxDB line protocol
                   +-------------------+
                   |    InfluxDB       |
                   |  (2.x or 3.x)     |
                   +---------+---------+
                             |
                             v  InfluxQL
                   +-------------------+
                   |    Grafana 12     |  <-- 本專案 dashboards
                   |  + Git Sync        |
                   +-------------------+
```

### 5.2 Repo 佈局

```
o-ran-smo-ves-dashboards/
├── README.md
├── LICENSE                          # Apache-2.0
├── CHANGELOG.md
├── dashboards/                      # canonical source (JSON)
│   ├── fault/
│   │   ├── ves-fault-overview.json
│   │   └── ves-fault-detail.json
│   ├── measurement/
│   │   ├── ves-measurement-nrcell-du.json
│   │   └── ves-measurement-nrcell-cu.json
│   ├── heartbeat/
│   │   └── ves-heartbeat-status.json
│   └── stnddefined/
│       └── ves-stnddefined-overview.json
├── foundation-sdk/                  # Python Foundation SDK 版本（可選 v0.2.0+）
│   └── build_dashboards.py
├── demo/
│   ├── docker-compose.yaml          # 低門檻示範
│   ├── kind-cluster.yaml            # 本地 k8s 示範
│   ├── helm-values.yaml             # ranpm 覆蓋值
│   └── seed-events.sh               # 呼叫 pytest-ves CLI
├── helm/
│   └── ves-dashboards/              # library chart 打包 ConfigMap
│       ├── Chart.yaml
│       └── templates/configmap.yaml
├── scripts/
│   ├── validate-dashboards.sh       # jsonschema + grafana CLI
│   └── publish-grafana-com.sh
├── docs/
│   ├── architecture.md              # link to this SDD
│   ├── queries/                     # 每支 dashboard 的 InfluxQL 註解
│   └── screenshots/
└── .github/workflows/
    ├── lint.yml
    ├── test.yml
    └── release.yml
```

### 5.3 部署模式
| 模式 | 目標受眾 | 入口 |
|---|---|---|
| grafana.com/grafana/dashboards/<id> | Grafana 使用者 | 每份 dashboard 一個 ID |
| `git clone` → 手動 import | Dashboard 客製 | JSON 直接讀 |
| `helm install ves-dashboards` | K8s 使用者 | ConfigMap 被 grafana-operator / sidecar 自動掛載 |
| Grafana 12 Git Sync | dashboard-as-code 團隊 | 將此 repo 設為 Git Sync 目標 |

---

## 6. Dashboard 目錄

### 6.1 `ves-fault-overview`
**問題回答：** 「目前 O-RAN 網路中活躍的告警長什麼樣？」

| Panel | Query 概念（InfluxQL） | Visualization |
|---|---|---|
| Active alarms | 最近 5 min 內 severity != CLEARED 的不重複 `eventName` + `sourceName` | Stat + Table |
| Alarms per severity | `COUNT by severity` 時序 | Pie chart |
| Alarms per source | `COUNT by sourceName` top-10 | Bar gauge |
| Alarm rate over time | `COUNT per 1m` | Time series |
| Alarm aging histogram | (now - startEpochMicrosec) bucket | Histogram |
| Recent alarm log | 最近 50 筆 raw rows | Logs/Table |

### 6.2 `ves-fault-detail`
**問題回答：** 「某一類 alarm condition 在哪些資源上發生？」
- Dropdown variable `alarmCondition`（值 e.g. `28 = CUS Link Failure`）
- Dropdown variable `severity`
- 面板：受影響資源列表、次數時序、first/last seen

### 6.3 `ves-measurement-nrcell-du`
**問題回答：** 「NR cell DU 的 PM counters 如何？」
- Variables：`SubNetwork`, `ManagedElement`, `NRCellDU`（cascading）
- Panels（對齊 3GPP TS 28.552 NR DU counters）：
  - DRB.PdcpSduVolumeDl / Ul_Filter（PDCP throughput）
  - DRB.MeanActiveUeDl（UE concurrency）
  - RRU.PrbUsedDl / Ul（PRB 使用率）
  - HO (handover) success/fail rates
  - L.Attach success/fail

### 6.4 `ves-measurement-nrcell-cu`
**問題回答：** 「NR cell CU 的 PM counters 如何？」
- 類似 §6.3，對齊 TS 28.552 NR CU counters（RRC connection, S1/N2 signaling）

### 6.5 `ves-heartbeat-status`
**問題回答：** 「哪些 NF 最近失聯？」
- `sourceName` 對 `lastEpochMicrosec` 的熱圖
- Missed heartbeat detector（超過 heartbeatInterval × 3 未回）
- Alerting rule（可選）：觸發 Grafana alert

### 6.6 `ves-stnddefined-overview`
**問題回答：** 「3GPP 標準定義事件的分佈？」
- By `stndDefinedNamespace` 分群
- 每個 namespace 的事件頻率時序
- 若 `data` payload 進 Influx，展示最常見的 `eventType` 或 `notificationType`

---

## 7. 工作流與 CI/CD

### 7.1 開發循環
1. Developer 在本地啟 Grafana 12（docker-compose 或 kind）
2. 指向範例 InfluxDB（已被 pytest-ves seed 過）
3. 在 UI 編輯 dashboard
4. Grafana 12 Git Sync 把變更以 "Push to new branch" 推回 repo
5. GitHub Actions 自動跑 `scripts/validate-dashboards.sh`（JSON schema、query lint、螢幕截圖 diff）
6. Code review → merge main
7. Tag `vX.Y.Z` 觸發 release workflow → 推 grafana.com、打包 Helm chart、更新 CHANGELOG

### 7.2 CI Jobs

```yaml
jobs:
  lint:
    steps:
      - check json schema（Grafana v2 schema）
      - ruff / yamllint
  test:
    services:
      influxdb: { image: influxdb:3-core }
      grafana:  { image: grafana/grafana:12 }
    steps:
      - seed via pytest-ves
      - import every dashboard JSON
      - call Grafana HTTP API /api/dashboards/uid/<uid>/ and assert 200 + no query errors
      - headless screenshot diff (optional phase 2)
  release:
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')
    steps:
      - build Helm chart → push OCI Harbor (重用 winlab-o1ves 的 Harbor 座標)
      - publish each dashboard to grafana.com via API
      - update README with grafana.com IDs
```

### 7.3 本地 kind 開發環境（D4）

```bash
# 使用者本地步驟（將寫進 demo/README）
kind create cluster --config demo/kind-cluster.yaml
helm install nonrtric oran-sc/nonrtric-plt-ranpm \
    -f demo/helm-values.yaml
kubectl apply -f demo/grafana.yaml
./demo/seed-events.sh    # 呼叫 pytest-ves CLI 產生並 POST 事件
# 打開 http://localhost:30000 看 dashboard
```

---

## 8. 測試策略

| 層級 | 範圍 | 工具 |
|---|---|---|
| Static | JSON schema valid、InfluxQL 語法、變數命名 | `dashboard-validate`（Grafana CLI）、`influxql-parser` |
| 功能 | 每 panel query 能回傳非空 | Grafana HTTP API `/api/ds/query` + pytest |
| 整合 | 完整 pipeline：pytest-ves → VES Collector → influxlogger → InfluxDB → dashboard | kind + Helm |
| 視覺回歸 | 截圖 diff（phase 2+） | `grafana-image-renderer` + `pixelmatch` |

---

## 9. 執行路線圖

### 9.1 MVP Phase 1（2 週末）— **Schema 實測**（最重要）
- [ ] kind 本地起 nonrtric-plt-ranpm 完整 stack
- [ ] 用 ves-client 或 pytest-ves v0.1.0 送各種 VES 事件進去
- [ ] `influx -token ... query 'SHOW MEASUREMENTS'` 列出所有實際 measurement
- [ ] 對每個 measurement 做 `SHOW FIELD KEYS` / `SHOW TAG KEYS`
- [ ] 紀錄 fault / heartbeat / stndDefined 是否落 Influx；若否，決定走 §4.4 的哪個備案
- [ ] 輸出 `docs/schema-ground-truth-2026-04-XX.md` 給後續 query 對齊

**Exit criterion：** 有文件化、實測確認的 InfluxDB schema。

### 9.2 MVP Phase 2（2 週末）— **First 3 dashboards**
- [ ] `ves-measurement-nrcell-du.json`（最確定能做的）
- [ ] `ves-fault-overview.json`（依 phase 1 結果）
- [ ] `ves-heartbeat-status.json`
- [ ] docker-compose demo 能 `docker compose up` + `open http://localhost:3000`
- [ ] README、LICENSE、CHANGELOG

### 9.3 v0.1.0 發佈（1 週末）
- [ ] GitHub Actions：lint + test
- [ ] 上傳 3 個 dashboard 至 grafana.com，取得 ID
- [ ] 發表 release tag；推到 winlab-o1ves 或新 repo

### 9.4 v0.2.0（之後 1 個月）
- [ ] 剩餘 3 個 dashboard
- [ ] Helm library chart（ConfigMap 封裝）
- [ ] Foundation SDK Python 版本（程式化生 dashboard）
- [ ] Grafana 12 Git Sync 工作流

### 9.5 v0.3.0+（探索性）
- [ ] AI-assisted anomaly annotation：用本地 NVIDIA GPU 跑小模型，把 fault 爆發點自動打 annotation 回 Grafana
- [ ] Prometheus-path 選擇性支援（若 3GPP perf3gpp domain 也走 Prometheus remote-write）
- [ ] 接入 OpenAirInterface + FlexRIC E2E 情境樣本

---

## 10. 風險與開放問題

| 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|
| fault/heartbeat 不落 influxlogger（見 §4.4） | 中 | 中：影響 2 份 dashboard 可行性 | §9.1 phase 1 實測；必要時走備案 A/B/C |
| InfluxDB 3 Docker latest 於 2026-05-27 切換導致既有 Flux query 失效 | **高** | **高** | D1 決策即走 InfluxQL；在 CI 矩陣同跑 2.x 與 3.x 兩版 |
| 3GPP PM counter 命名因版本不同而變（TS 28.552 Rel-16/17/18） | 中 | 中 | variable-ize counter 名稱；文件標註對應 Rel 版本 |
| nonrtric-plt-ranpm Helm chart 安裝失敗（依賴 Istio 等） | 中 | 低 | demo 提供最小 override values；必要時附說明如何 disable |
| grafana.com 發佈需要 Grafana Cloud 帳號審核流程長 | 低 | 低 | 先發 GitHub + Helm，grafana.com 當錦上添花 |
| Grafana 12 Dashboard JSON schema v2 still in public preview，日後可能 breaking | 中 | 中 | 同時保留 v1 JSON export 作 fallback；CHANGELOG 注記相容性 |

---

## 11. 決策紀錄索引（未來 ADR 檔）

本 SDD 預計衍生以下 ADR（於實作期間增修）：
- ADR-002 — InfluxQL vs Flux vs SQL 的最終選擇與 migration strategy
- ADR-003 — Dashboard JSON schema v1 vs v2
- ADR-004 — grafana.com 單個 ID vs 多 ID 發佈策略
- ADR-005 — Helm library chart vs subchart vs standalone chart

---

## 12. 相關上游資產

| 資產 | URL |
|---|---|
| nonrtric-plt-influxlogger 文件 | <https://docs.o-ran-sc.org/projects/o-ran-sc-nonrtric-plt-ranpm/en/latest/influxlogger/overview.html> |
| nonrtric-plt-ranpm 安裝指南 | <https://docs.o-ran-sc.org/projects/o-ran-sc-aiml-fw-aimlfw-dep/en/latest/_sources/ranpm-installation.rst.txt> |
| o-ran-sc/smo-ves | <https://github.com/o-ran-sc/smo-ves> |
| Grafana 12 Git Sync | <https://grafana.com/whats-new/2025-05-06-git-sync-for-grafana-dashboards/> |
| Grafana Foundation SDK | <https://grafana.com/docs/grafana/latest/as-code/observability-as-code/foundation-sdk/> |
| Grafana Dashboard JSON v2 | <https://grafana.com/docs/grafana/latest/as-code/observability-as-code/schema-v2/> |
| InfluxDB 3 Core GA（2025-04-15） | <https://www.influxdata.com/blog/influxdata-announces-influxdb-3-OSS-GA/> |
| 3GPP SA5 MnS | <https://forge.3gpp.org/rep/sa5/MnS> |
| 3GPP TS 28.552（PM counters） | <https://www.3gpp.org/DynaReport/28-series.htm> |
| OAI 5G para（競品參考） | <https://grafana.com/grafana/dashboards/22297-oai-5g-para/> |
| NIST O-RAN-Testbed-Automation（競品參考） | <https://github.com/usnistgov/O-RAN-Testbed-Automation> |

---

## 附錄 A — 與 `pytest-ves` 專案的整合契約

| 介面 | pytest-ves 提供 | o-ran-smo-ves-dashboards 消費 |
|---|---|---|
| Python API | `ves_fault_event`, `ves_measurement_event`, ... | 在整合測試 / demo seeder 中 `import pytest_ves; pytest_ves.seed(...)` |
| CLI（v0.2.0+） | `pytest-ves send --collector http://... --rate 10 --count 1000 --domain fault` | `demo/seed-events.sh` 直接呼叫 |
| Docker image（v0.3.0 規劃） | `ghcr.io/thc1006/pytest-ves:<ver>` | kind demo 中以 Job 執行 |
| Schema 對齊 | `CommonEventFormat_30.2.1_ONAP.json`（vendored） | 文件引用同一 schema；確保 dashboard 預期的欄位都存在 |

**綜效測試場景：**
```bash
# 本地 kind 叢集，一條命令跑通
./demo/e2e.sh
# 1. kind create cluster
# 2. helm install nonrtric-plt-ranpm
# 3. helm install grafana 12 + ves-dashboards
# 4. docker run pytest-ves send --count 1000 --rate 5 --severity=random
# 5. open http://localhost:30000 → 看到 active alarms 圖表隨時間漲
```

---

## 附錄 B — NVIDIA GPU 的保留位置

v0.1.0–v0.2.0 **不使用** GPU。v0.3.0+ 可探索：
- Grafana ML panel + 本地部署的異常偵測（LSTM/transformer）：把 PM counter 的預測區間疊回時序圖
- 歷史事件的自然語言摘要（本地 LLM）顯示在 Grafana 的 Text panel
- 這些都是「錦上添花」，不會進入 dashboard pack 的核心價值主張
