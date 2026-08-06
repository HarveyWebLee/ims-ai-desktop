# 设备变量（var）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                     |
| ------------------ | -------------------------------------------------------- |
| 模块名称（中文）   | 设备变量                                                 |
| 模块名称（英文）   | Device Variable                                          |
| 所属 Group（中文） | 设备变量                                                 |
| 所属 Group（英文） | Device Variable                                          |
| Group ID           | `device_variable`                                        |
| 菜单位置           | 配置管理平台 → 配置管理 → 设备变量 → 设备变量            |
| 路由路径           | `/config_management/config/var`                          |
| 页面目录           | `src/pages/config_management/config/device_variable/var` |

## 1. 模块定位与项目作用

设备变量是综合信息平台「配置管理」域下的核心点位配置模块，位于设备变量配置体系中。它负责定义挂载在监控设备上的每一个可采集、可存储、可监视、可下发的数据点（变量），是连接「物理/逻辑设备」与「业务数据、告警、历史、组态、控制」的关键中间层。

在整个项目中，本模块承担以下作用：

- **点位主数据中心**：统一维护变量名称、英文编码、别名、数据类型、地址、读写属性等点位定义。
- **采集与存储策略配置入口**：定义采集周期、存储频率、存储策略、滤波规则，直接影响数采驱动如何采、如何存。
- **协议解析与数值转换载体**：通过寄存器类型、字节顺序、编码、标定值、值转化参数、Lua 脚本等描述原始报文如何变成业务可读值。
- **运行态监视与控制入口**：支持变量实时监视（WebSocket）与指令下发模拟，便于调试与运维验证。
- **下游业务绑点基础**：变量告警、二次变量、历史查询、实时变量数据、2D 组态、流程自动化、规则引擎、运算组件等，均以本模块变量作为数据源或控制目标。

变量配置变更（尤其是导入、批量修改）后，通常需要到「数采服务器」管理页面对相关驱动执行「更新配置」，变更才会真正生效。

---

## 2. 页面与交互结构

页面采用「左侧树筛选 + 右侧列表/表单」的配置管理通用布局，并附带两个运维弹窗能力。

### 2.1 左侧树筛选

支持按以下维度切换树并过滤变量列表（本模块不提供区域树筛选）：

| 树类型   | 作用                       |
| -------- | -------------------------- |
| 设备分组 | 按设备所属分组筛选其下变量 |
| 设备类型 | 按监控设备类型筛选相关变量 |

树节点选中后，会转换为对应的设备分组 ID、设备类型 ID 或子系统 ID 等查询条件。

### 2.2 列表与表单

- 列表支持分页查询、条件过滤、导入导出、复制、编辑、删除。
- 表单用于新增/编辑变量详情，字段覆盖归属设备、点位标识、协议地址、读写与存储、滤波、映射字典、脚本等。
- 编辑时可按「采集周期 × 存储频率」自动计算并展示「存储周期（秒）」，该计算字段只读，不参与导入导出。

### 2.3 运维弹窗

| 能力     | 作用                                                                               |
| -------- | ---------------------------------------------------------------------------------- |
| 指令下发 | 对当前变量模拟下发指令值，验证写通道与控制链路                                     |
| 监视     | 通过 WebSocket 实时查看该变量采集值、时间戳等内容，支持对象/数组类 JSON 值折叠展示 |

---

## 3. 属性字段说明

以下字段为变量主数据及表单/列表中涉及的核心属性。部分字段成对出现：一端为选择控件提交的 ID，一端为列表展示或导出用的名称。

### 3.1 归属与组织

| 字段名          | 中文含义       | 作用说明                                                             |
| --------------- | -------------- | -------------------------------------------------------------------- |
| id              | 主键 ID        | 变量唯一标识，系统内部引用、更新、删除使用                           |
| deviceId        | 监控设备 ID    | 必填；变量所属监控设备，是变量与设备管理模块的主关联键               |
| deviceName      | 设备名称       | 所属设备展示名；列表默认可展示并支持搜索                             |
| deviceCode      | 设备编码       | 所属设备业务编码；实时监视、指令下发等运行态链路依赖设备编码定位设备 |
| deviceGroupId   | 设备分组 ID    | 按设备分组过滤变量（通常来自所属设备）                               |
| deviceGroupName | 设备分组名称   | 分组展示名                                                           |
| subSystemId     | 所属子系统 ID  | 按子系统维度过滤                                                     |
| subSystemName   | 所属子系统名称 | 子系统展示名                                                         |

### 3.2 变量身份标识

| 字段名      | 中文含义           | 作用说明                                                                            |
| ----------- | ------------------ | ----------------------------------------------------------------------------------- |
| showName    | 变量名称           | 必填；业务可见中文/展示名称，列表默认可展示并支持搜索                               |
| varName     | 变量编码（英文名） | 必填；变量英文标识，长度上限 40；跨模块绑点、指令下发、实时推送普遍以该字段定位变量 |
| alias       | 变量别名           | 必填；辅助识别与检索的别名                                                          |
| varType     | 变量类型           | 必填；来自变量类型枚举，描述变量业务/技术分类，支持列表筛选                         |
| varTypeName | 变量类型名称       | 变量类型展示名                                                                      |
| remark      | 备注               | 自由文本说明                                                                        |

### 3.3 数据类型与值语义

| 字段名               | 中文含义     | 作用说明                                                         |
| -------------------- | ------------ | ---------------------------------------------------------------- |
| dataTypeId           | 数据类型     | 必填；整数、实数、字符、无符号整数、文本等，决定点位数据形态     |
| dataTypeName         | 数据类型名称 | 数据类型展示/导出名                                              |
| valueTypeId          | 值类型       | 必填；底层值类型（由值类型字典接口提供），影响驱动解析与前端展示 |
| valueTypeName        | 值类型名称   | 值类型展示名                                                     |
| showPrecision        | 数据精度     | 小数点后位数；为空表示不处理精度、显示原始数据；0 表示整数       |
| maxValue             | 最大值       | 变量有效值上限，可用于校验或展示量程                             |
| minValue             | 最小值       | 变量有效值下限                                                   |
| unit                 | 单位         | 工程单位，如 ℃、kPa、% 等                                        |
| unitLength           | 单元长度     | 必填；数据单元长度，服务于协议解析与寄存器读写长度               |
| positionValue        | 按位取值     | 按位解析时的位位置/位掩码相关配置                                |
| statisticsCategoryId | 统计分类     | 是否纳入某类统计（是/否类选项），服务于统计分析场景              |

### 3.4 地址、协议与编码

| 字段名           | 中文含义         | 作用说明                                                                                             |
| ---------------- | ---------------- | ---------------------------------------------------------------------------------------------------- |
| varAddress       | 变量地址         | 必填；点位在设备/协议中的地址，列表可展示并支持搜索                                                  |
| blockAddress     | 块地址           | 必填；块或区段地址，配合变量地址定位寄存器范围                                                       |
| subAddress       | 子地址           | 更细粒度地址补充                                                                                     |
| registerTypeId   | 寄存器类型       | 必填；如读线圈、读离散输入、读保持寄存器、读输入寄存器、写单线圈、写单寄存器、写多线圈、写多寄存器等 |
| registerTypeName | 寄存器类型名称   | 寄存器类型展示名                                                                                     |
| byteOrderId      | 字节顺序         | 必填；如 AB、BA、ABCD、CDAB、BADC、DCBA 及 8 字节序组合，决定多字节数据拼装顺序                      |
| byteOrderName    | 字节顺序名称     | 字节顺序展示名                                                                                       |
| varCodeId        | 编码             | 字符串类数据的字符编码，如 BCD、ASCII、UTF8、UNICODE 16LE/16BE、GBK                                  |
| varCodeName      | 编码名称         | 编码展示名                                                                                           |
| calibrationValue | 标定值           | 标定/校准用数值串；需符合约定格式（数值及可选区间段）                                                |
| resolution       | 值转化参数       | 原始值到工程值的转化参数说明/配置文本                                                                |
| luaText          | lua 解析脚本     | 自定义 Lua 脚本，用于复杂报文解析或值处理                                                            |
| convertFormula   | 广播播报文本公式 | 用于广播播报文本生成的表达式；提交前会做表达式合法性校验                                             |

### 3.5 读写与内置/分发属性

| 字段名   | 中文含义 | 作用说明                                                         |
| -------- | -------- | ---------------------------------------------------------------- |
| isWrite  | 是否可写 | 必填；控制是否允许对该变量下发写入/控制                          |
| isRead   | 是否可读 | 必填；控制是否允许采集读取该变量                                 |
| isInside | 是否内置 | 必填；标记是否为系统内置变量（内置变量通常有特殊保护或默认语义） |
| isOut    | 是否分发 | 必填；控制变量值是否向外分发（如推送给其他服务或前端订阅通道）   |

### 3.6 采集、推送与存储

| 字段名           | 中文含义       | 作用说明                                                                                                                       |
| ---------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| timeInterval     | 采集周期（ms） | 必填；驱动对该点位的采集间隔，最小为 1 毫秒级整数                                                                              |
| pushFrequency    | 存储频率       | 与采集周期相乘得到存储周期；为空时默认按 600 作为存储频率                                                                      |
| storeCycle       | 存储周期（秒） | 只读计算字段：采集周期 × 存储频率 / 1000；不参与导入导出                                                                       |
| storeStrategy    | 存储策略       | 必填；默认「周期和变化存储」。可选：周期存储、变化存储、周期和变化存储、不存储、全局定时存储。选择不存储时，存储周期设置不生效 |
| monitorPushCycle | 推送周期（s）  | 监视/推送相关周期配置                                                                                                          |

### 3.7 滤波

| 字段名     | 中文含义     | 作用说明                                                     |
| ---------- | ------------ | ------------------------------------------------------------ |
| filterMode | 滤波模式     | 无、差值绝对值滤波、变化率绝对值滤波；用于抑制噪声或无效抖动 |
| diffValue  | 差值绝对值   | 差值绝对值滤波模式下的阈值                                   |
| changeRate | 变化率绝对值 | 变化率绝对值滤波模式下的阈值                                 |

### 3.8 映射字典与运算

| 字段名          | 中文含义         | 作用说明                                      |
| --------------- | ---------------- | --------------------------------------------- |
| dic1            | 变量显示状态映射 | 键值映射，将原始状态值映射为界面显示文案/状态 |
| dic2            | 变量驱动状态映射 | 字典映射，供驱动侧状态语义转换使用            |
| varRuleInterval | 运算间隔（ms）   | 与二次运算/规则计算相关的执行间隔             |

历史上曾存在「二次变量绑定参数」「二次变量运算公式」等字段能力，当前主表单中相关配置以注释/迁移形态存在；二次变量业务主要由同目录下的二次变量模块承接。

---

## 4. 功能清单

### 4.1 基础 CRUD

- 新建变量（必须先选择监控设备）
- 编辑变量
- 按 ID 拉取详情回填
- 删除变量
- 复制变量
- 按树节点与表单条件查询列表

### 4.2 导入导出

- 导出变量列表（支持前端导出模式）
- 勾选导出
- 导入变量（建议单次不超过约 20000 个）
- 批量修改导入

导入或批量修改成功后，系统会提示前往数采服务器页面执行驱动「更新配置」。

### 4.3 指令下发

- 在列表操作中打开「指令下发」
- 输入指令值并下发
- 以设备编码 + 变量英文名定位目标点，验证写通道是否通畅

适用于调试控制点、核对可写属性与驱动写寄存器配置。

### 4.4 变量监视

- 在列表操作中打开「监视」
- 通过 WebSocket 订阅指定设备编码与变量英文名的实时数据
- 展示采集时间与当前值
- 对对象/数组型 JSON 值提供折叠详情查看

适用于核对采集是否正常、地址与解析是否正确、推送是否及时。

### 4.5 表单联动计算

- 同步监听采集周期与存储频率
- 自动计算并回填存储周期（秒）
- 当任一输入为空时清空存储周期展示

---

## 5. 与其他功能模块的关系

### 5.1 上游依赖

| 关联模块/能力                | 关系说明                                                                                     |
| ---------------------------- | -------------------------------------------------------------------------------------------- |
| 设备管理（equipment_manage） | 变量必须挂载到监控设备；设备选型复用设备管理字段定义与设备列表；设备复制时可连同变量一并复制 |
| 设备分组 / 设备类型 / 子系统 | 提供树筛选与组织维度过滤                                                                     |
| 值类型字典、变量类型枚举     | 提供值类型与变量类型选项                                                                     |
| 表达式校验服务               | 校验广播播报文本公式等表达式合法性                                                           |
| 数采服务器 / 驱动            | 变量地址、周期、策略最终由驱动加载执行；配置变更后需驱动更新配置生效                         |

### 5.2 同目录兄弟模块

| 关联模块                           | 关系说明                                                   |
| ---------------------------------- | ---------------------------------------------------------- |
| 二次变量（second_var）             | 基于一次变量做运算与组合，产出派生点位                     |
| 变量告警配置（var_alarm_config）   | 以设备变量为告警对象，配置阈值与告警规则                   |
| 实时变量数据（real_time_var_data） | 面向多变量实时数据查看与运维，数据源头仍是本模块定义的变量 |

### 5.3 下游消费

| 关联模块               | 关系说明                                                            |
| ---------------------- | ------------------------------------------------------------------- |
| 历史数据查询           | 按设备与变量查询历史曲线/记录，依赖变量存储策略是否落库             |
| 告警查询与统计         | 告警点位追溯到设备变量定义                                          |
| 2D 组态 / 页面编辑     | 图表、控件绑点依赖设备变量；编辑区可接入变量 WebSocket 预览真实数据 |
| 流程自动化（Flowgram） | 节点中配置设备变量，作为条件、读写或动作参数                        |
| 运算/组件逻辑          | 运算代码可读取设备变量；支持设备变量模拟测试输入                    |
| 规则变量列表等通用组件 | 直接查询设备变量列表作为可选点位源                                  |
| 指令控制类业务         | 通过设备编码 + 变量英文名下发控制值                                 |

### 5.4 与设备管理的双向关系

- 设备是变量的容器：没有设备主数据，变量无法建档。
- 变量是设备可观测/可控制的能力清单：设备只有配置了变量，才能采集、告警、展示与控制。
- 「复制设备及变量」由设备管理发起，但结果同时写入设备与变量两套主数据。

---

## 6. 关键业务规则与注意事项

1. **先有设备，后有变量**：新建变量时监控设备为必填。
2. **变量英文名是运行态主键语义**：监视、指令、组态绑点、WebSocket 订阅等普遍使用变量英文名（配合设备编码）。
3. **英文名长度受限**：变量编码最长 40 个字符。
4. **读写属性决定能力边界**：不可读则不应期望正常采集展示；不可写则指令下发无业务意义。
5. **存储策略影响历史可用性**：选择「不存储」后，历史查询将缺少该点数据；存储周期在该策略下不生效。
6. **存储周期是派生值**：由采集周期与存储频率计算得出，配置时关注两者联动，而非单独改存储周期。
7. **滤波阈值需匹配模式**：差值/变化率滤波模式下应配置对应阈值，否则滤波行为不符合预期。
8. **标定值有格式约束**：不符合约定数值格式时表单校验会拒绝提交。
9. **表达式类字段会做服务端校验**：广播播报文本公式提交前需通过表达式检查。
10. **配置生效依赖驱动更新**：导入、批量修改后需到数采服务器管理页更新驱动配置。
11. **导入规模建议**：单次上传变量建议不超过约 20000 个，避免超时或性能问题。
12. **显示映射与驱动映射分工不同**：dic1 偏前端/展示语义，dic2 偏驱动侧状态语义，二者勿混用。

---

## 7. 在配置管理链路中的位置（总结）

设备变量处于「设备主数据」与「运行数据/业务应用」之间：

设备建档 → 变量点位配置 → 驱动采集/存储/分发 → 实时监视、历史、告警、组态展示、控制下发、自动化规则

本模块决定了平台「能看见什么数据、怎样看见、能否控制、是否落历史、如何告警」。它与设备管理共同构成监控配置的双基石：设备管理解决「有哪些设备、如何接入」，设备变量解决「每个设备有哪些点、如何采写与使用」。变更本模块时，应同步评估对驱动配置、告警规则、组态绑点及历史存储的影响。

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 采集单个变量

| 项          | 内容                             |
| ----------- | -------------------------------- |
| 接口路径    | `/device/collectDevVar`          |
| 请求方法    | `POST`                           |
| 前端封装    | `SystemController.collectDevVar` |
| Swagger Tag | deviceManagementApi              |
| 作用说明    | 采集单个变量                     |

**请求参数（Body）：**

| 字段    | 类型     | 说明 |
| ------- | -------- | ---- |
| `devNo` | `string` |      |
| `varNo` | `string` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 下发指令

| 项          | 内容                       |
| ----------- | -------------------------- |
| 接口路径    | `/device/sendCmd`          |
| 请求方法    | `POST`                     |
| 前端封装    | `CommonController.sendCmd` |
| Swagger Tag | deviceManagementApi        |
| 作用说明    | 下发指令                   |

**请求参数（Body）：**

| 字段          | 类型            | 说明 |
| ------------- | --------------- | ---- |
| `dn`          | `string`        |      |
| `before`      | `integer`       |      |
| `after`       | `integer`       |      |
| `vs`          | `array<object>` |      |
| `vs[].vn`     | `string`        |      |
| `vs[].vv`     | `string`        |      |
| `operateName` | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.3 获取广播事件列表

| 项          | 内容                          |
| ----------- | ----------------------------- |
| 接口路径    | `/eventBc/allotEvent`         |
| 请求方法    | `POST`                        |
| 前端封装    | `SystemController.allotEvent` |
| Swagger Tag | eventBroadcastApi             |
| 作用说明    | 获取广播事件列表              |

**请求参数（Body）：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `name`    | `string`  |      |
| `devCode` | `string`  |      |
| `page`    | `integer` |      |
| `size`    | `integer` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.4 获取设备控制事件列表

| 项          | 内容                              |
| ----------- | --------------------------------- |
| 接口路径    | `/eventDc/getEventDcList`         |
| 请求方法    | `POST`                            |
| 前端封装    | `SystemController.getEventDcList` |
| Swagger Tag | eventDeviceControlApi             |
| 作用说明    | 获取设备控制事件列表              |

**请求参数（Body）：**

| 字段   | 类型      | 说明 |
| ------ | --------- | ---- |
| `name` | `string`  |      |
| `dn`   | `string`  |      |
| `page` | `integer` |      |
| `size` | `integer` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.5 获取事件类型

| 项          | 内容                             |
| ----------- | -------------------------------- |
| 接口路径    | `/event/getEventTypes`           |
| 请求方法    | `POST`                           |
| 前端封装    | `SystemController.getEventTypes` |
| Swagger Tag | eventFlowApi                     |
| 作用说明    | 获取事件类型                     |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.6 导出设备变量（选择）

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/device/exportDeviceVariable1`          |
| 请求方法    | `GET`                                    |
| 前端封装    | `SystemController.exportDeviceVariable1` |
| Swagger Tag | deviceManagementApi                      |
| 作用说明    | 导出设备变量（选择）                     |

**Query/Path 参数：**

| 参数名            | 位置  | 必填 | 类型     | 说明                 |
| ----------------- | ----- | ---- | -------- | -------------------- |
| `page`            | query | 是   | `string` |                      |
| `size`            | query | 是   | `string` |                      |
| `search`          | query | 否   | `string` |                      |
| `fieldList[0]`    | query | 否   | `string` |                      |
| `sorter[0].order` | query | 否   | `string` |                      |
| `sorter[0].field` | query | 否   | `string` |                      |
| `deviceName`      | query | 否   | `string` |                      |
| `deviceCode`      | query | 否   | `string` |                      |
| `deviceGroupId`   | query | 否   | `string` |                      |
| `varName`         | query | 否   | `string` |                      |
| `showName`        | query | 否   | `string` |                      |
| `varAddress`      | query | 否   | `string` |                      |
| `deviceCombId`    | query | 否   | `string` | 新增组合设备查询     |
| `subSystemId`     | query | 否   | `string` | 系只能子系统id查询   |
| `containSubLevel` | query | 否   | `string` | 新增是否包含下级查询 |
| `regionId`        | query | 否   | `string` |                      |
| `varType`         | query | 否   | `string` |                      |
| `ids[0]`          | query | 否   | `string` |                      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.7 获取设备变量列表

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/device/getDevicVariableeList`          |
| 请求方法    | `POST`                                   |
| 前端封装    | `SystemController.getDevicVariableeList` |
| Swagger Tag | deviceManagementApi                      |
| 作用说明    | 获取设备变量列表                         |

**请求参数（Body）：**

| 字段              | 类型             | 说明                 |
| ----------------- | ---------------- | -------------------- |
| `page`            | `integer`        |                      |
| `size`            | `integer`        |                      |
| `search`          | `string`         |                      |
| `fieldList`       | `array<string>`  |                      |
| `sorter`          | `array<object>`  |                      |
| `sorter[].order`  | `string`         |                      |
| `sorter[].field`  | `string`         |                      |
| `deviceName`      | `string`         |                      |
| `deviceCode`      | `string`         |                      |
| `deviceGroupId`   | `integer`        |                      |
| `varName`         | `string`         |                      |
| `showName`        | `string`         |                      |
| `varAddress`      | `string`         |                      |
| `deviceCombId`    | `integer`        | 新增组合设备查询     |
| `subSystemId`     | `integer`        | 系只能子系统id查询   |
| `containSubLevel` | `integer`        | 新增是否包含下级查询 |
| `regionId`        | `integer`        |                      |
| `varType`         | `string`         |                      |
| `ids`             | `array<integer>` |                      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.8 导出设备变量(按条件)

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/device/exportDeviceVariable`          |
| 请求方法    | `GET`                                   |
| 前端封装    | `SystemController.exportDeviceVariable` |
| Swagger Tag | deviceManagementApi                     |
| 作用说明    | 导出设备变量(按条件)                    |

**Query/Path 参数：**

| 参数名            | 位置  | 必填 | 类型     | 说明                 |
| ----------------- | ----- | ---- | -------- | -------------------- |
| `page`            | query | 是   | `string` |                      |
| `size`            | query | 是   | `string` |                      |
| `search`          | query | 否   | `string` |                      |
| `fieldList[0]`    | query | 否   | `string` |                      |
| `sorter[0].order` | query | 否   | `string` |                      |
| `sorter[0].field` | query | 否   | `string` |                      |
| `deviceName`      | query | 否   | `string` |                      |
| `deviceCode`      | query | 否   | `string` |                      |
| `deviceGroupId`   | query | 否   | `string` |                      |
| `varName`         | query | 否   | `string` |                      |
| `showName`        | query | 否   | `string` |                      |
| `varAddress`      | query | 否   | `string` |                      |
| `deviceCombId`    | query | 否   | `string` | 新增组合设备查询     |
| `subSystemId`     | query | 否   | `string` | 系只能子系统id查询   |
| `containSubLevel` | query | 否   | `string` | 新增是否包含下级查询 |
| `regionId`        | query | 否   | `string` |                      |
| `varType`         | query | 否   | `string` |                      |
| `ids[0]`          | query | 否   | `string` |                      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.9 添加设备变量

| 项          | 内容                                 |
| ----------- | ------------------------------------ |
| 接口路径    | `/device/addDeviceVariable`          |
| 请求方法    | `POST`                               |
| 前端封装    | `SystemController.addDeviceVariable` |
| Swagger Tag | deviceManagementApi                  |
| 作用说明    | 添加设备变量                         |

**请求参数（Body）：**

| 字段                   | 类型             | 说明                       |
| ---------------------- | ---------------- | -------------------------- |
| `id`                   | `integer`        |                            |
| `deviceCode`           | `string`         |                            |
| `deviceId`             | `integer`        |                            |
| `deviceName`           | `string`         |                            |
| `deviceGroupId`        | `integer`        | private String deviceType; |
| `dataTypeId`           | `integer`        |                            |
| `varName`              | `string`         |                            |
| `showName`             | `string`         |                            |
| `valueTypeId`          | `integer`        |                            |
| `showPrecision`        | `integer`        |                            |
| `maxValue`             | `string`         |                            |
| `minValue`             | `string`         |                            |
| `varAddress`           | `string`         |                            |
| `blockAddress`         | `string`         |                            |
| `byteOrderId`          | `integer`        |                            |
| `varCodeId`            | `integer`        |                            |
| `subAddress`           | `string`         |                            |
| `calibrationValue`     | `string`         |                            |
| `isWrite`              | `integer`        |                            |
| `isRead`               | `integer`        |                            |
| `convertFormula`       | `string`         |                            |
| `timeInterval`         | `integer`        |                            |
| `storeStrategy`        | `string`         |                            |
| `isInside`             | `integer`        |                            |
| `isOut`                | `integer`        |                            |
| `registerTypeId`       | `integer`        |                            |
| `statisticsCategoryId` | `integer`        |                            |
| `unitLength`           | `integer`        |                            |
| `unit`                 | `string`         | 新增变量单位               |
| `resolution`           | `string`         | 分辨率                     |
| `positionValue`        | `string`         |                            |
| `remark`               | `string`         |                            |
| `ids`                  | `array<integer>` |                            |
| `dic1`                 | `string`         | 新增两个字典               |
| `dic2`                 | `string`         |                            |
| `alias`                | `string`         | 新增变量别名，只供展示使用 |
| `pushFrequency`        | `integer`        | 新增推送频率字段           |
| `varType`              | `string`         | 新增变量类型字段           |
| `varParam`             | `string`         |                            |
| `oldVarParam`          | `string`         |                            |
| `varRule`              | `string`         |                            |
| `varRuleInterval`      | `integer`        |                            |
| `luaText`              | `string`         | 新增lua脚本                |
| `filterMode`           | `integer`        | 新增数据过滤字段           |
| `diffValue`            | `string`         |                            |
| `changeRate`           | `string`         |                            |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.10 获取设备变量详情

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/device/getDeviceVariableById`          |
| 请求方法    | `POST`                                   |
| 前端封装    | `SystemController.getDeviceVariableById` |
| Swagger Tag | deviceManagementApi                      |
| 作用说明    | 获取设备变量详情                         |

**请求参数（Body）：**

| 字段                   | 类型             | 说明                       |
| ---------------------- | ---------------- | -------------------------- |
| `id`                   | `integer`        |                            |
| `deviceCode`           | `string`         |                            |
| `deviceId`             | `integer`        |                            |
| `deviceName`           | `string`         |                            |
| `deviceGroupId`        | `integer`        | private String deviceType; |
| `dataTypeId`           | `integer`        |                            |
| `varName`              | `string`         |                            |
| `showName`             | `string`         |                            |
| `valueTypeId`          | `integer`        |                            |
| `showPrecision`        | `integer`        |                            |
| `maxValue`             | `string`         |                            |
| `minValue`             | `string`         |                            |
| `varAddress`           | `string`         |                            |
| `blockAddress`         | `string`         |                            |
| `byteOrderId`          | `integer`        |                            |
| `varCodeId`            | `integer`        |                            |
| `subAddress`           | `string`         |                            |
| `calibrationValue`     | `string`         |                            |
| `isWrite`              | `integer`        |                            |
| `isRead`               | `integer`        |                            |
| `convertFormula`       | `string`         |                            |
| `timeInterval`         | `integer`        |                            |
| `storeStrategy`        | `string`         |                            |
| `isInside`             | `integer`        |                            |
| `isOut`                | `integer`        |                            |
| `registerTypeId`       | `integer`        |                            |
| `statisticsCategoryId` | `integer`        |                            |
| `unitLength`           | `integer`        |                            |
| `unit`                 | `string`         | 新增变量单位               |
| `resolution`           | `string`         | 分辨率                     |
| `positionValue`        | `string`         |                            |
| `remark`               | `string`         |                            |
| `ids`                  | `array<integer>` |                            |
| `dic1`                 | `string`         | 新增两个字典               |
| `dic2`                 | `string`         |                            |
| `alias`                | `string`         | 新增变量别名，只供展示使用 |
| `pushFrequency`        | `integer`        | 新增推送频率字段           |
| `varType`              | `string`         | 新增变量类型字段           |
| `varParam`             | `string`         |                            |
| `oldVarParam`          | `string`         |                            |
| `varRule`              | `string`         |                            |
| `varRuleInterval`      | `integer`        |                            |
| `luaText`              | `string`         | 新增lua脚本                |
| `filterMode`           | `integer`        | 新增数据过滤字段           |
| `diffValue`            | `string`         |                            |
| `changeRate`           | `string`         |                            |

**响应体：**

| 字段                          | 类型      | 说明                       |
| ----------------------------- | --------- | -------------------------- |
| `code`                        | `integer` |                            |
| `message`                     | `string`  |                            |
| `data`                        | `object`  |                            |
| `data.id`                     | `integer` |                            |
| `data.deviceId`               | `integer` |                            |
| `data.deviceName`             | `string`  |                            |
| `data.deviceCode`             | `string`  |                            |
| `data.deviceGroupId`          | `integer` |                            |
| `data.dataTypeId`             | `integer` |                            |
| `data.dataTypeName`           | `string`  |                            |
| `data.varName`                | `string`  |                            |
| `data.showName`               | `string`  |                            |
| `data.valueTypeId`            | `integer` |                            |
| `data.valueTypeName`          | `string`  |                            |
| `data.showPrecision`          | `integer` |                            |
| `data.maxValue`               | `string`  |                            |
| `data.minValue`               | `string`  |                            |
| `data.varAddress`             | `string`  |                            |
| `data.blockAddress`           | `string`  |                            |
| `data.byteOrderId`            | `integer` |                            |
| `data.byteOrderName`          | `string`  |                            |
| `data.varCodeId`              | `integer` |                            |
| `data.varCodeName`            | `string`  |                            |
| `data.subAddress`             | `string`  |                            |
| `data.calibrationValue`       | `string`  |                            |
| `data.isWrite`                | `integer` |                            |
| `data.isRead`                 | `integer` |                            |
| `data.convertFormula`         | `string`  |                            |
| `data.timeInterval`           | `integer` |                            |
| `data.storeStrategy`          | `string`  |                            |
| `data.isInside`               | `integer` |                            |
| `data.isOut`                  | `integer` |                            |
| `data.registerTypeId`         | `integer` |                            |
| `data.registerTypeName`       | `string`  |                            |
| `data.statisticsCategoryId`   | `integer` |                            |
| `data.statisticsCategoryName` | `string`  |                            |
| `data.unit`                   | `string`  | 新增变量单位               |
| `data.resolution`             | `string`  |                            |
| `data.unitLength`             | `integer` |                            |
| `data.positionValue`          | `string`  |                            |
| `data.remark`                 | `string`  |                            |
| `data.alias`                  | `string`  | 新增变量别名，只供展示使用 |
| `data.pushFrequency`          | `integer` | 新增推送频率字段           |
| `data.varType`                | `string`  | 新增变量类型字段           |
| `data.varTypeName`            | `string`  |                            |
| `data.varParam`               | `string`  |                            |
| `data.varRule`                | `string`  |                            |
| `data.varRuleInterval`        | `integer` |                            |
| `data.dic1`                   | `string`  | 新增两个字典               |
| `data.dic2`                   | `string`  |                            |
| `data.luaText`                | `string`  | 新增lua脚本                |
| `data.filterMode`             | `integer` | 新增数据过滤字段           |
| `data.diffValue`              | `string`  |                            |
| `data.changeRate`             | `string`  |                            |
| `data.createdTime`            | `string`  |                            |
| `data.updatedTime`            | `string`  |                            |

---

### 8.11 更新设备变量

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/device/updateDeviceVariable`          |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.updateDeviceVariable` |
| Swagger Tag | deviceManagementApi                     |
| 作用说明    | 更新设备变量                            |

**请求参数（Body）：**

| 字段                   | 类型             | 说明                       |
| ---------------------- | ---------------- | -------------------------- |
| `id`                   | `integer`        |                            |
| `deviceCode`           | `string`         |                            |
| `deviceId`             | `integer`        |                            |
| `deviceName`           | `string`         |                            |
| `deviceGroupId`        | `integer`        | private String deviceType; |
| `dataTypeId`           | `integer`        |                            |
| `varName`              | `string`         |                            |
| `showName`             | `string`         |                            |
| `valueTypeId`          | `integer`        |                            |
| `showPrecision`        | `integer`        |                            |
| `maxValue`             | `string`         |                            |
| `minValue`             | `string`         |                            |
| `varAddress`           | `string`         |                            |
| `blockAddress`         | `string`         |                            |
| `byteOrderId`          | `integer`        |                            |
| `varCodeId`            | `integer`        |                            |
| `subAddress`           | `string`         |                            |
| `calibrationValue`     | `string`         |                            |
| `isWrite`              | `integer`        |                            |
| `isRead`               | `integer`        |                            |
| `convertFormula`       | `string`         |                            |
| `timeInterval`         | `integer`        |                            |
| `storeStrategy`        | `string`         |                            |
| `isInside`             | `integer`        |                            |
| `isOut`                | `integer`        |                            |
| `registerTypeId`       | `integer`        |                            |
| `statisticsCategoryId` | `integer`        |                            |
| `unitLength`           | `integer`        |                            |
| `unit`                 | `string`         | 新增变量单位               |
| `resolution`           | `string`         | 分辨率                     |
| `positionValue`        | `string`         |                            |
| `remark`               | `string`         |                            |
| `ids`                  | `array<integer>` |                            |
| `dic1`                 | `string`         | 新增两个字典               |
| `dic2`                 | `string`         |                            |
| `alias`                | `string`         | 新增变量别名，只供展示使用 |
| `pushFrequency`        | `integer`        | 新增推送频率字段           |
| `varType`              | `string`         | 新增变量类型字段           |
| `varParam`             | `string`         |                            |
| `oldVarParam`          | `string`         |                            |
| `varRule`              | `string`         |                            |
| `varRuleInterval`      | `integer`        |                            |
| `luaText`              | `string`         | 新增lua脚本                |
| `filterMode`           | `integer`        | 新增数据过滤字段           |
| `diffValue`            | `string`         |                            |
| `changeRate`           | `string`         |                            |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.12 删除设备变量

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/device/deleteDeviceVariable`          |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.deleteDeviceVariable` |
| Swagger Tag | deviceManagementApi                     |
| 作用说明    | 删除设备变量                            |

**请求参数（Body）：**

| 字段                   | 类型             | 说明                       |
| ---------------------- | ---------------- | -------------------------- |
| `id`                   | `integer`        |                            |
| `deviceCode`           | `string`         |                            |
| `deviceId`             | `integer`        |                            |
| `deviceName`           | `string`         |                            |
| `deviceGroupId`        | `integer`        | private String deviceType; |
| `dataTypeId`           | `integer`        |                            |
| `varName`              | `string`         |                            |
| `showName`             | `string`         |                            |
| `valueTypeId`          | `integer`        |                            |
| `showPrecision`        | `integer`        |                            |
| `maxValue`             | `string`         |                            |
| `minValue`             | `string`         |                            |
| `varAddress`           | `string`         |                            |
| `blockAddress`         | `string`         |                            |
| `byteOrderId`          | `integer`        |                            |
| `varCodeId`            | `integer`        |                            |
| `subAddress`           | `string`         |                            |
| `calibrationValue`     | `string`         |                            |
| `isWrite`              | `integer`        |                            |
| `isRead`               | `integer`        |                            |
| `convertFormula`       | `string`         |                            |
| `timeInterval`         | `integer`        |                            |
| `storeStrategy`        | `string`         |                            |
| `isInside`             | `integer`        |                            |
| `isOut`                | `integer`        |                            |
| `registerTypeId`       | `integer`        |                            |
| `statisticsCategoryId` | `integer`        |                            |
| `unitLength`           | `integer`        |                            |
| `unit`                 | `string`         | 新增变量单位               |
| `resolution`           | `string`         | 分辨率                     |
| `positionValue`        | `string`         |                            |
| `remark`               | `string`         |                            |
| `ids`                  | `array<integer>` |                            |
| `dic1`                 | `string`         | 新增两个字典               |
| `dic2`                 | `string`         |                            |
| `alias`                | `string`         | 新增变量别名，只供展示使用 |
| `pushFrequency`        | `integer`        | 新增推送频率字段           |
| `varType`              | `string`         | 新增变量类型字段           |
| `varParam`             | `string`         |                            |
| `oldVarParam`          | `string`         |                            |
| `varRule`              | `string`         |                            |
| `varRuleInterval`      | `integer`        |                            |
| `luaText`              | `string`         | 新增lua脚本                |
| `filterMode`           | `integer`        | 新增数据过滤字段           |
| `diffValue`            | `string`         |                            |
| `changeRate`           | `string`         |                            |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.13 导入设备变量

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/device/importDeviceVariable`          |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.importDeviceVariable` |
| Swagger Tag | deviceManagementApi                     |
| 作用说明    | 导入设备变量                            |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.14 批量更新设备变量

| 项          | 内容                                   |
| ----------- | -------------------------------------- |
| 接口路径    | `/device/batchUpdateVariable`          |
| 请求方法    | `POST`                                 |
| 前端封装    | `SystemController.batchUpdateVariable` |
| Swagger Tag | deviceManagementApi                    |
| 作用说明    | 批量更新设备变量                       |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.15 checkAviatorScript

| 项       | 内容                                  |
| -------- | ------------------------------------- |
| 接口路径 | `/aviator/checkAviatorScript`         |
| 请求方法 | `POST`                                |
| 前端封装 | `SystemController.checkAviatorScript` |
| 作用说明 | 见模块业务逻辑                        |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.16 获取设备分组树

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/device/getDeviceGroupTree`          |
| 请求方法    | `POST`                                |
| 前端封装    | `SystemController.getDeviceGroupTree` |
| Swagger Tag | deviceManagementApi                   |
| 作用说明    | 获取设备分组树                        |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段         | 类型            | 说明 |
| ------------ | --------------- | ---- |
| `code`       | `integer`       |      |
| `message`    | `string`        |      |
| `data`       | `array<object>` |      |
| `data[].key` | `object`        |      |

---

### 8.17 获取菜单树

| 项          | 内容                           |
| ----------- | ------------------------------ |
| 接口路径    | `/menu/getMenuTree`            |
| 请求方法    | `POST`                         |
| 前端封装    | `SystemController.getMenuTree` |
| Swagger Tag | menuManagementApi              |
| 作用说明    | 获取菜单树                     |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.18 查询组合设备和关联列表

| 项          | 内容                                 |
| ----------- | ------------------------------------ |
| 接口路径    | `/deviceComb/getDeviceCombList`      |
| 请求方法    | `POST`                               |
| 前端封装    | `SystemController.getDeviceCombList` |
| Swagger Tag | deviceCombinationApi                 |
| 作用说明    | 查询组合设备和关联列表               |

**请求参数（Body）：**

| 字段        | 类型            | 说明 |
| ----------- | --------------- | ---- |
| `page`      | `integer`       |      |
| `size`      | `integer`       |      |
| `search`    | `string`        |      |
| `fieldList` | `array<string>` |      |
| `name`      | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.19 获取设备列表

| 项          | 内容                             |
| ----------- | -------------------------------- |
| 接口路径    | `/device/getDeviceList`          |
| 请求方法    | `POST`                           |
| 前端封装    | `SystemController.getDeviceList` |
| Swagger Tag | deviceManagementApi              |
| 作用说明    | 获取设备列表                     |

**请求参数（Body）：**

| 字段              | 类型             | 说明                                       |
| ----------------- | ---------------- | ------------------------------------------ |
| `page`            | `integer`        |                                            |
| `size`            | `integer`        |                                            |
| `search`          | `string`         |                                            |
| `fieldList`       | `array<string>`  |                                            |
| `sorter`          | `array<object>`  |                                            |
| `sorter[].order`  | `string`         |                                            |
| `sorter[].field`  | `string`         |                                            |
| `deviceCode`      | `string`         |                                            |
| `deviceName`      | `string`         |                                            |
| `deviceGroupId`   | `integer`        |                                            |
| `subSystemId`     | `integer`        |                                            |
| `regionId`        | `integer`        |                                            |
| `deviceStatus`    | `integer`        |                                            |
| `onlineStatus`    | `integer`        |                                            |
| `commDeviceId`    | `integer`        |                                            |
| `collectServerId` | `integer`        |                                            |
| `deviceCombId`    | `integer`        | 新增组合设备查询                           |
| `isTemplate`      | `integer`        | 新增是否模板设备查询                       |
| `containSubLevel` | `integer`        | 新增是否包含下级查询                       |
| `commModel`       | `array<integer>` | 新增通信模式字段（1-直接，2-间接，3-网关） |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.20 getValueTypeList

| 项       | 内容                                |
| -------- | ----------------------------------- |
| 接口路径 | `/dic/getValueTypeList`             |
| 请求方法 | `GET`                               |
| 前端封装 | `SystemController.getValueTypeList` |
| 作用说明 | 见模块业务逻辑                      |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.21 变量类型枚举

| 项          | 内容                              |
| ----------- | --------------------------------- |
| 接口路径    | `/device/getVarTypeEnum`          |
| 请求方法    | `GET`                             |
| 前端封装    | `SystemController.getVarTypeEnum` |
| Swagger Tag | deviceManagementApi               |
| 作用说明    | 变量类型枚举                      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段         | 类型            | 说明 |
| ------------ | --------------- | ---- |
| `code`       | `integer`       |      |
| `message`    | `string`        |      |
| `data`       | `array<object>` |      |
| `data[].key` | `string`        |      |

---
