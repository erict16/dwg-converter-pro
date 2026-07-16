# DWG Converter Pro — 技术方案与实施计划

> 状态：**仅规划 + 仓库底子**（按你的要求，尚未开始业务开发）  
> 目标：拖入中文 DWG → 图纸内中文（含引线/箭头注释）译成英文 → 下载英文 DWG  
> 前端部署：Vercel

---

## 1. 产品一句话

**专业电力设备图纸（OLTC / SHZV 等）中文 DWG 批量译英**，优先用项目术语表，缺词再用免费机翻，尽量保持原图层、几何、引线不变，只改文字内容。

---

## 2. 已摸清的本地资产

| 类型 | 路径 / 说明 |
|------|-------------|
| 中文样例 | `...\CAD\中文图纸\`：`SHZVIII-1000Y-170D-12233W-L.dwg`、`SHZV工作位置表和接线原理图12233W.dwg`、`外挂板式电位电阻（5根）12233W.dwg`、`钟罩式安装法兰尺寸图...dwg` |
| 英文参考 | `...\CAD\SHZV\`：Outline / Wiring / Head Arrangement 等已译图纸 |
| 术语表 | `...\Attachments\Techincal Brochure\semantic-glossary.xlsx` |
| 术语表结构 | Sheet `Semantic Glossary`：列 `中文术语` / `英文翻译` / `备注`，约 **393 对** 专业词 |

样例用途：

1. **开发期**：从中文 DWG 抽字符串 → 对照术语表 + 机翻 → 写回 → 与 SHZV 英文图「风格/用词」人工 spot-check。  
2. **验收期**：固定 4 张中文图作为回归样例（实体覆盖率、漏译率、几何是否破坏）。

---

## 3. 核心技术难点（必须先认清）

### 3.1 DWG 是闭源二进制

- 开源生态强项在 **DXF**（`ezdxf` 可读写）。  
- **DWG ↔ DXF** 可靠路径：**ODA File Converter**（免费 Guest 工具）+ `ezdxf.addons.odafc`。  
- 纯浏览器 / 纯 Vercel Serverless **跑不了** ODA 与大文件 CAD 处理。

### 3.2 要译的不只是「普通文字」

图纸里中文可能出现在：

| 实体 | 说明 | 是否优先覆盖 |
|------|------|----------------|
| `TEXT` | 单行字 | ✅ MVP |
| `MTEXT` | 多行、带格式码 | ✅ MVP |
| `ATTRIB` / `ATTDEF` | 块属性 | ✅ MVP |
| `MULTILEADER` / `LEADER` | **箭头引线注释**（你特别强调） | ✅ MVP |
| `DIMENSION` | 尺寸文字覆盖 / 后缀 | ✅ Phase 1.5 |
| 块内嵌文字 | Block 定义里的 TEXT/MTEXT | ✅ Phase 1 |
| `TABLE` / 其他 | 表格单元等 | Phase 2 |

原则：**几何、图层、线型、引线路径不动；只替换字符串。**

### 3.3 翻译质量 > 通用机翻

电力分接开关术语（真空泡、切换开关、钟罩式…）通用机翻容易翻错。  
策略必须是：

```
Glossary 精确/最长匹配  →  残留中文再走机翻  →  人工可审预览（可选）
```

---

## 4. 推荐架构（Vercel 前端 + 独立 CAD Worker）

```
┌─────────────────────────────────────────────────────────┐
│  Vercel（Next.js App）                                   │
│  - 拖拽上传 UI                                           │
│  - 任务状态 / 译词预览 / 下载                            │
│  - 可选：术语表在线查看                                  │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTPS (presigned URL 或 multipart)
                        ▼
┌─────────────────────────────────────────────────────────┐
│  CAD Worker（Python FastAPI）                            │
│  建议托管：Railway / Fly.io / 自建 Windows 小机          │
│  （ODA File Converter 在 Windows 上最省心）              │
│                                                          │
│  1. 收 DWG → ODA → DXF                                   │
│  2. ezdxf 遍历可译实体 → 抽中文                          │
│  3. 翻译管线（见 §5）                                    │
│  4. 写回 DXF → ODA → DWG                                 │
│  5. 返回下载链接                                         │
└─────────────────────────────────────────────────────────┘
```

### 为什么不「全放 Vercel」？

| 方案 | 结论 |
|------|------|
| Vercel 纯前端 + 客户端处理 DWG | ❌ 浏览器无可靠 DWG 引擎 |
| Vercel Serverless 函数跑 ODA | ❌ 无 ODA、超时、二进制体积限制 |
| **Vercel UI + 外挂 Worker** | ✅ 符合你「Vercel 作前端 app」的要求 |

### 开发期可先本地一条龙

在 Windows 本机跑 Worker + Next.js，用 4 张中文图打通闭环，再拆部署。

---

## 5. 翻译管线设计

### 5.1 优先级（强制顺序）

1. **项目术语表 `semantic-glossary.xlsx`**  
   - 最长匹配（避免「切换开关」被拆成短词）  
   - 整句完全命中优先  
   - 支持同义词备注列扩展  
2. **图纸内已出现的重复串缓存**（同一图同句只译一次）  
3. **免费机翻兜底**（见下表）  
4. （可选）人工确认表：导出「原文 / 译后 / 来源」CSV 再一键应用  

### 5.2 免费 / 低成本翻译 API 对比

| 方案 | 费用 | 中文→英 | 适合场景 | 注意 |
|------|------|---------|----------|------|
| **术语表（主路径）** | 免费、离线 | 专业准确 | 电力专业词 | 约 393 条，需持续补词 |
| **MyMemory API** | 免费约 5k 词/天（无 key 更低） | 可用 | 兜底 | 质量一般、有日限 |
| **LibreTranslate** | 自建无限；公共实例有限 | 中等 | 隐私 / 本地 | 电力术语仍弱 |
| **DeepL Free API** | 约 50 万字符/月 | 较好 | 兜底升级 | 需注册 key |
| **Google Cloud Translate** | 约 50 万字符/月免费额度 | 较好 | 正式产品 | 需 GCP 账单账号 |
| **不走 API，纯术语表 + 人工补** | 免费 | 最可控 | 内网、小批量 | 覆盖不全时漏中文 |

**MVP 建议：**

- 默认：`Glossary first` + `MyMemory` 或 `LibreTranslate` 兜底。  
- 配置开关：`MT_PROVIDER=none|mymemory|libre|deepl`。  
- 若机翻 API 不稳定：**仅术语表 + 未命中保留中文并在报告中标红**（比胡翻好）。

### 5.3 字符串处理规则（实现时要写死）

- 检测中文：`[\u4e00-\u9fff]` 等。  
- **MTEXT 格式码**（`\P`、`{\f...;}` 等）只译「可见文本段」，不破坏格式。  
- 数字、型号（`12233W`、`SHZV`）、尺寸（`72.5`）默认不译。  
- 混排句：术语替换后再对残留中文机翻。  
- 输出侧统一术语风格，对齐 SHZV 英文图（如 Bell-type、PRD、tap position…）。

---

## 6. 前端模板选型（Vercel）

**推荐脚手架（尚未执行 create，等你确认 plan）：**

| 选项 | 说明 | 推荐度 |
|------|------|--------|
| **A. `create-t3-app` / 官方 `create-next-app` + App Router + Tailwind** | 最干净，Vercel 一键部署 | ⭐ 推荐 |
| **B. Vercel 模板：Next.js + File Upload** | 上传 UX 现成 | 可参考组件 |
| **C. 纯 Vite React** | 也能上 Vercel，但生态略弱于 Next 对 API route | 次选 |

UI 模块（计划中的页面）：

1. **Home / Convert**：拖放 `.dwg`（多文件队列）  
2. **Job 详情**：进度、提取到的中文条数、glossary 命中率、机翻条数  
3. **Preview 表**（可选）：原文 ↔ 译文，可改再生成  
4. **Glossary**：展示/导入 `semantic-glossary`  
5. **Download**：`.dwg` + 可选 `translation-report.csv`

设计方向：深色工程风 / 简洁工具站（后续再定视觉，不阻塞架构）。

---

## 7. 后端 / 处理引擎选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | CAD/文本生态成熟 |
| CAD | `ezdxf` + **ODA File Converter** | 读写 DXF；DWG 经 ODA |
| API | FastAPI | 上传、任务、下载清晰 |
| 队列 | 先同步；量大再 Celery/RQ | MVP 简单 |
| 存储 | 本地 temp；上云用 R2/S3 | 文件大、短时效 |
| 术语 | 仓库内 `data/semantic-glossary.xlsx` 副本 + 构建时转 JSON | 快速匹配 |

**Windows 本机优先**：你已有真实 DWG + OneDrive 样例；ODA 官方 Windows 安装最顺。

---

## 8. 推荐仓库结构（落地时）

```
C:\repo\dwg-converter-pro\
├── PLAN.md                 # 本计划
├── README.md
├── .gitignore
├── apps/
│   └── web/                # Next.js → Vercel
├── services/
│   └── worker/             # FastAPI + ezdxf + ODA 调用
├── packages/
│   └── glossary/           # 术语表 JSON + 匹配库
├── data/
│   └── semantic-glossary.xlsx   # 术语表副本（注意是否可公开）
├── samples/                # 可选：小体积测试 DXF（勿提交大客户 DWG）
└── docs/
    └── entity-coverage.md  # 实体覆盖与已知限制
```

Monorepo 工具：先简单用根目录双 folder；需要再上 pnpm workspace。

---

## 9. 分阶段实施（确认 plan 后再动手）

### Phase 0 — 底子（本次目标）✅ / 进行中

- [x] 本地 `C:\repo\dwg-converter-pro` 初始化  
- [x] 写入 `PLAN.md` / `README.md` / `.gitignore`  
- [ ] 连接 GitHub remote（需你完成 `gh auth login`）  
- [ ] 初始 commit + 空仓库 push  

### Phase 1 — 离线管线 MVP（先 CLI，再 API）

1. 安装 ODA File Converter + `ezdxf`  
2. 脚本：`dwg → dxf → 抽中文清单`  
3. 接入 glossary 最长匹配  
4. 写回 + 导出 DWG  
5. 用 `中文图纸` 4 张 + 对照 `SHZV` 英文图验收  

### Phase 2 — Web UI（Vercel）

1. `create-next-app` 脚手架  
2. 上传 → 调本地 Worker  
3. 下载与简单报告  

### Phase 3 — 部署与加固

1. Worker 上云（Windows 优先或 Linux + ODA）  
2. 鉴权（内网 token / 简单登录）  
3. 文件生命周期与大小限制  
4. 引线/尺寸边界 case、块炸开等边角  

### Phase 4 — 体验增强（可选）

- 在线预览（PDF/PNG 缩略，ezdxf 绘图或打印服务）  
- 术语表在线增补  
- 批量 zip 上传  

---

## 10. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| ODA 无法在 Vercel 运行 | 架构分裂 | UI / Worker 分离（已定） |
| 引线 MULTILEADER 写回异常 | 箭头注释丢字 | 单测样例；必要时只改 content 字段 |
| 机翻术语错误 | 出图事故 | Glossary 优先；报告可审 |
| 大 DWG / 复杂块 | 超时、漏译 | 任务队列 + 块定义遍历 |
| 术语表进公开 GitHub | 知识产权 | private repo；或 git-crypt / 不提交 xlsx 用本地路径 |
| 中文字体缺失 | 显示乱码 | 不改字体名；依赖原图样式 |

**建议：GitHub 仓库设为 Private。**

---

## 11. 验收标准（第一版做完算过）

1. 4 张中文样例图：可见中文标注 **≥95% 被替换或报告未译**（无静默失败）。  
2. 引线/箭头注释中文被处理。  
3. 打开后几何与图层与原图一致（抽查）。  
4. 术语表中已有词 **100% 用表内英文**，不用机翻覆盖。  
5. Vercel 上可打开上传页；本机 Worker 可完成一次端到端。

---

## 12. 已确认决策（2026-07-16）

| 项 | 决定 |
|----|------|
| 仓库 | **Public**，个人账号 |
| 机翻 | **自建 LibreTranslate** |
| 术语表 | **进 git**（xlsx + json） |
| 输出 | **只要 DWG** |
| 节奏 | **先 Vercel 壳子**，再 CAD worker |

见 `docs/decisions.md`。

---

## 13. 框架进度

**已完成**

- [x] 本地仓库 + Plan  
- [x] 术语表入库（393 条）  
- [x] Next.js Vercel UI shell（拖拽队列 + glossary 页）  
- [x] Worker / LibreTranslate 占位  
- [ ] GitHub public repo + push  
- [ ] Vercel 项目连接（在网页 Import 即可）  

**下一步（认真写代码时）**

1. 实现 worker：ODA + ezdxf 抽字/写回  
2. glossary 最长匹配 + LibreTranslate 兜底  
3. Web 上传对接 `NEXT_PUBLIC_WORKER_URL`  
4. 用 `CAD\中文图纸` 4 张样例验收  

---

*文档版本：2026-07-16 — Foundation / Vercel shell.*
