# Academic Calendar

个人日历订阅项目，涵盖学校校历、日本及中国公共假期、垃圾分类提醒、账单提醒与兼职排班。

## 订阅链接

以下链接为 `webcal://` 格式，Apple 设备可直接点击跳转订阅；其他应用请将 `webcal://` 替换为 `https://`。

### 合并版本

**校历 & 日本节假日**
```
webcal://raw.githubusercontent.com/Joewon9/Academic-Calendar/main/ics/school_holidays.ics
```

**生活提醒**（垃圾分类 + 账单 + 兼职排班）
```
webcal://raw.githubusercontent.com/Joewon9/Academic-Calendar/main/ics/life.ics
```

### 单独文件

**学校校历**
```
webcal://raw.githubusercontent.com/Joewon9/Academic-Calendar/main/ics/school.ics
```

**日本节假日**
```
webcal://raw.githubusercontent.com/Joewon9/Academic-Calendar/main/ics/holidays.ics
```

**中国节假日**
```
webcal://raw.githubusercontent.com/Joewon9/Academic-Calendar/main/ics/holidays_cn.ics
```

**垃圾分类提醒**
```
webcal://raw.githubusercontent.com/Joewon9/Academic-Calendar/main/ics/garbage.ics
```

**账单提醒**
```
webcal://raw.githubusercontent.com/Joewon9/Academic-Calendar/main/ics/bills.ics
```

**兼职排班**
```
webcal://raw.githubusercontent.com/Joewon9/Academic-Calendar/main/ics/work.ics
```

## 使用方法

将链接添加到日历应用的「订阅日历」或「通过 URL 添加」功能中：

- **Apple 日历**：文件 → 新建日历订阅
- **Google Calendar**：设置 → 通过网址添加日历
- 其他支持 ICS 订阅的应用同理

## 数据文件

所有数据位于 `data/` 目录，修改后推送即可在次日自动更新：

| 文件 | 内容 |
|------|------|
| `data/school.yaml` | 学校特殊事件（假期、考试、典礼等） |
| `data/garbage.yaml` | 垃圾分类收集规则（按周/隔周） |
| `data/bills.yaml` | 账单到期日及提前提醒天数 |
| `data/parttime.yaml` | 兼职排班（手动逐条添加） |
