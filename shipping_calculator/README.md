# 美国本土 FedEx / UPS 邮费比价工具

该工具用于根据 FedEx 与 UPS 在美国本土的常见计费规则，快速核算单票包裹的运费。系统会自动判断 AHS 超长/超重、Oversize 超尺寸以及超限包裹等情形，并将附加费、地址派送费、偏远地区费用与燃油附加费统一汇总，方便销售或客服人员在接单前评估成本。

## 功能特点

- 统一输入包裹尺寸、实际重量、计费重量、地址类型（住宅/商业）以及偏远/不规则包装等标记。
- 自动按照 FedEx 规则在触发 AHS 超长或 Oversize 时，将基础运费重量提升到 40 lbs 或 90 lbs。
- 支持配置各类附加费金额（AHS、Oversize、偏远地区等）与燃油附加费比例。
- 输出 FedEx 与 UPS 详细费用拆分，并提示超限包裹等风险，帮助快速比较。

## 安装与运行

无需额外依赖，直接使用 Python 3.10+ 运行即可。

```bash
python -m shipping_calculator --help
```

## 配置文件

所有费率数据来自一个 JSON 文件，可按需调整。示例配置位于 `shipping_calculator/sample_config.json`，结构如下：

```json
{
  "fedex": {
    "name": "FedEx",
    "base_rates": { "10": 28.5, "20": 41.0, "30": 53.0 },
    "address_surcharge": { "residential": 5.15, "commercial": 0.0 },
    "fuel_surcharge": 0.15,
    "surcharges": {
      "ahs_length": 16.0,
      "ahs_overweight": 27.5,
      "ahs_irregular": 18.0,
      "oversize_residential": 120.0,
      "oversize_commercial": 110.0,
      "overlimit": 200.0,
      "remote_area": 14.5
    }
  },
  "ups": {
    "name": "UPS",
    "base_rates": { "10": 27.5, "20": 40.0, "30": 51.5 },
    "address_surcharge": { "residential": 4.95, "commercial": 0.0 },
    "fuel_surcharge": 0.14,
    "surcharges": {
      "ahs_length": 15.5,
      "ahs_overweight": 26.0,
      "ahs_irregular": 16.5,
      "oversize_residential": 115.0,
      "oversize_commercial": 105.0,
      "overlimit": 185.0,
      "remote_area": 13.0
    }
  }
}
```

- `base_rates`：按计费重量（lbs）递增的基础运费表，程序会选择不小于计费重量的阶梯，如果超出表格上限，则使用最大值。
- `address_surcharge`：住宅或商业地址派送费。
- `fuel_surcharge`：燃油附加费比例，以小数表示（0.15 = 15%）。
- `surcharges`：附加费金额，可根据需要增加或调整。若某些费用不适用，可设置为 0 或直接删除对应键。

## 使用示例

```bash
python -m shipping_calculator \
  --config shipping_calculator/sample_config.json \
  --length 97 --width 15 --height 10 \
  --actual-weight 55 --billable-weight 60 \
  --address-type residential \
  --ahs-irregular \
  --remote-area
```

示例输出：

```
=======================
美国本土 FedEx / UPS 邮费比价
=======================
包裹信息: 97.0x15.0x10.0 inch, 实重 55.0 lbs, 计费重 60.0 lbs
地址类型: 住宅, 偏远地区: 是
提示: 包裹使用软包装或不规则包装，已启用AHS不规则费用。

-- UPS --
基础运费重量: 60.00 lbs
基础运费: $86.00
地址派送费: $4.95
偏远地区附加费: $13.00
附加费:
  - AHS超长（需额外人工处理）: $15.50
  - AHS超重: $26.00
  - AHS不规则包装: $16.50
  - Oversize 超尺寸: $115.00
燃油附加费 (14.00%): $38.77
总价: $315.72
注意事项:
  - 包裹触发Oversize附加费，建议确认客户是否接受高额附加成本。

-- FedEx --
基础运费重量: 90.00 lbs
基础运费: $129.50
地址派送费: $5.15
偏远地区附加费: $14.50
附加费:
  - AHS超长（需额外人工处理）: $16.00
  - AHS超重: $27.50
  - AHS不规则包装: $18.00
  - Oversize 超尺寸: $120.00
燃油附加费 (15.00%): $49.60
总价: $380.25
注意事项:
  - 包裹触发Oversize附加费，建议确认客户是否接受高额附加成本。

最低报价: UPS ($315.72)，比下一个报价节省 $64.52
```

> **提示：** 如果包裹触发超限条件（超 150 lbs、最长边超过 108 inch 或者长+2×(宽+高) 大于 165 inch），系统会在输出中给出警示，提醒该票货物可能被承运商拒收，建议提前评估。

## 常见调整

- 若需要新增附加费类型，可在配置文件 `surcharges` 中添加键值对，然后在 `shipping_calculator/calculator.py` 里参照 `_gather_surcharges` 的写法增加输出描述。
- 若需要导入承运商实时费率，可将 `base_rates` 替换成更完整的阶梯表，或在业务系统中生成配置文件再调用该工具。

欢迎根据公司内部费率或 SOP 调整配置文件，使输出更加贴近真实成本。 
