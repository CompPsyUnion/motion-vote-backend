# Debate Timer API 调用演示

## 概述

Debate Timer API 提供了辩论赛计时器的配置和控制功能。该API允许前端获取辩论赛各个阶段的计时配置，包括单侧和双侧计时、铃声提示等。

## API 端点

### 获取计时器配置

**端点**: `GET /screen/{activityId}/timer`

**描述**: 获取指定活动的计时器配置数据

**路径参数**:
- `activityId` (string): 活动ID

**响应格式**:
```json
{
  "success": true,
  "data": {
    "activityName": "辩论赛活动",
    "debateTitle": "是否应该取消高考？",
    "stages": [
      {
        "stageName": "开场陈词",
        "isDualSide": false,
        "sides": [
          {
            "name": "主持人",
            "duration": 60
          }
        ],
        "bellTimings": [
          {
            "time": 0,
            "type": "start"
          },
          {
            "time": 60,
            "type": "end"
          }
        ],
        "hideTimer": true
      },
      {
        "stageName": "立论阶段 - 正方",
        "isDualSide": false,
        "sides": [
          {
            "name": "正方一辩",
            "duration": 180
          }
        ],
        "bellTimings": [
          {
            "time": 0,
            "type": "start"
          },
          {
            "time": 150,
            "type": "warning"
          },
          {
            "time": 180,
            "type": "end"
          }
        ]
      },
      {
        "stageName": "攻辩环节",
        "isDualSide": true,
        "sides": [
          {
            "name": "正方二辩",
            "duration": 90
          },
          {
            "name": "反方二辩",
            "duration": 90
          }
        ],
        "bellTimings": [
          {
            "time": 0,
            "type": "start"
          },
          {
            "time": 75,
            "type": "warning"
          },
          {
            "time": 90,
            "type": "end"
          }
        ]
      }
    ]
  },
  "message": "获取计时器配置成功"
}
```

## 数据结构说明

### TimerData
```typescript
interface TimerData {
  activityName: string;    // 活动名称
  debateTitle: string;     // 辩题标题
  stages: TimerStage[];    // 计时阶段配置数组
}
```

### TimerStage
```typescript
interface TimerStage {
  stageName: string;           // 阶段名称（如"立论阶段"、"攻辩环节"）
  isDualSide: boolean;         // 是否为双侧计时（true=正反方同时计时）
  sides: TimerSide[];          // 计时器侧面配置（1个或2个）
  bellTimings: BellTiming[];   // 铃声提示配置
  hideTimer?: boolean;         // 是否隐藏计时器显示（用于主持人阶段）
}
```

### TimerSide
```typescript
interface TimerSide {
  name: string;        // 发言者名称（如"正方一辩"、"主持人"）
  duration: number;    // 计时时长（秒）
  currentTime?: number; // 当前剩余时间（可选，用于状态同步）
}
```

### BellTiming
```typescript
interface BellTiming {
  time: number;                    // 播放铃声的时间点（从开始算起的秒数）
  type: 'start' | 'warning' | 'end'; // 铃声类型
}
```

## 调用示例

### 使用 curl 调用

```bash
# 获取活动ID为 "debate-2024-001" 的计时器配置
curl -X GET "http://localhost:8000/screen/debate-2024-001/timer" \
  -H "Content-Type: application/json"
```

### 使用 Python 调用

```python
import requests

def get_timer_config(activity_id: str):
    """获取计时器配置"""
    url = f"http://localhost:8000/screen/{activity_id}/timer"

    try:
        response = requests.get(url)
        response.raise_for_status()

        result = response.json()
        if result['success']:
            return result['data']
        else:
            print(f"API调用失败: {result['message']}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None

# 使用示例
if __name__ == "__main__":
    activity_id = "debate-2024-001"
    timer_config = get_timer_config(activity_id)

    if timer_config:
        print(f"活动名称: {timer_config['activityName']}")
        print(f"辩题: {timer_config['debateTitle']}")
        print(f"阶段数量: {len(timer_config['stages'])}")

        for i, stage in enumerate(timer_config['stages'], 1):
            print(f"\n阶段 {i}: {stage['stageName']}")
            print(f"  双侧计时: {stage['isDualSide']}")
            print(f"  发言者: {[side['name'] for side in stage['sides']]}")
```

### 使用 JavaScript/TypeScript 调用

```typescript
// src/api/screen.ts 中的实现
import { HttpClient } from '@/utils/http';
import type { ApiResponse } from '@/types/api';
import type { TimerData } from '@/types/screen';

export class ScreenApi {
  /**
   * 获取计时器配置数据
   * @param activityId 活动 ID
   * @returns 计时器配置数据
   */
  static async getTimerConfig(activityId: string): Promise<ApiResponse<TimerData>> {
    return HttpClient.get<TimerData>(`/screen/${activityId}/timer`);
  }
}

// 在 Vue 组件中使用
import { ref } from 'vue';
import { ScreenApi } from '@/api/screen';
import type { TimerData } from '@/types/screen';

const timerData = ref<TimerData | null>(null);

const loadTimerConfig = async (activityId: string) => {
  try {
    const response = await ScreenApi.getTimerConfig(activityId);
    if (response.success && response.data) {
      timerData.value = response.data;
      console.log('计时器配置加载成功:', response.data);
    } else {
      console.error('获取计时器配置失败:', response.message);
    }
  } catch (error) {
    console.error('API调用出错:', error);
  }
};

// 使用示例
await loadTimerConfig('debate-2024-001');
```

## 前端集成示例

### Vue 组件使用

```vue
<template>
  <div v-if="timerData" class="timer-container">
    <h1>{{ timerData.activityName }}</h1>
    <h2>{{ timerData.debateTitle }}</h2>

    <div class="stages">
      <div
        v-for="(stage, index) in timerData.stages"
        :key="index"
        class="stage"
      >
        <h3>{{ stage.stageName }}</h3>
        <div class="speakers">
          <div
            v-for="side in stage.sides"
            :key="side.name"
            class="speaker"
          >
            <span class="name">{{ side.name }}</span>
            <span class="duration">{{ formatTime(side.duration) }}</span>
          </div>
        </div>
        <div v-if="stage.bellTimings.length > 0" class="bell-timings">
          <h4>铃声提示:</h4>
          <ul>
            <li v-for="bell in stage.bellTimings" :key="bell.time">
              {{ bell.time }}秒 - {{ bell.type }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
  <div v-else>
    <p>加载计时器配置中...</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ScreenApi } from '@/api/screen';
import type { TimerData } from '@/types/screen';

const props = defineProps<{
  activityId: string;
}>();

const timerData = ref<TimerData | null>(null);

const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

onMounted(async () => {
  try {
    const response = await ScreenApi.getTimerConfig(props.activityId);
    if (response.success) {
      timerData.value = response.data;
    }
  } catch (error) {
    console.error('Failed to load timer config:', error);
  }
});
</script>
```

## 错误处理

API 调用可能出现的错误情况：

### 活动不存在
```json
{
  "success": false,
  "data": null,
  "message": "活动不存在"
}
```

### 服务器错误
```json
{
  "success": false,
  "data": null,
  "message": "服务器内部错误"
}
```

### 前端容错处理
```typescript
// 在前端实现容错
const loadTimerConfig = async (activityId: string) => {
  try {
    const response = await ScreenApi.getTimerConfig(activityId);
    if (response.success && response.data) {
      timerData.value = response.data;
    } else {
      // API 失败时使用默认配置
      console.warn('API调用失败，使用默认配置');
      timerData.value = getDefaultTimerConfig();
    }
  } catch (error) {
    // 网络错误或其他异常
    console.error('加载计时器配置失败:', error);
    timerData.value = getDefaultTimerConfig();
  }
};

const getDefaultTimerConfig = (): TimerData => {
  return {
    activityName: '辩论赛活动',
    debateTitle: '辩题',
    stages: [
      {
        stageName: '立论阶段',
        isDualSide: false,
        sides: [{ name: '发言者', duration: 180 }],
        bellTimings: [
          { time: 0, type: 'start' },
          { time: 150, type: 'warning' },
          { time: 180, type: 'end' }
        ]
      }
    ]
  };
};
```

## 计时器功能特性

### 支持的计时模式
1. **单侧计时**: 一个发言者单独计时（如开场陈词、立论阶段）
2. **双侧计时**: 正反方同时计时（如攻辩环节、自由辩论）

### 铃声提示系统
- **start**: 阶段开始时的提示音
- **warning**: 即将结束的警告提示（通常在最后30秒）
- **end**: 阶段结束时的提示音

### 键盘快捷键支持
- `空格键`: 开始/暂停计时
- `S键`: 切换计时侧面（双侧模式）
- `R键`: 重置计时器
- `←/→键`: 切换上下阶段

## 部署和测试

### 启动后端服务
```bash
cd backend
python run.py
```

### 测试 API
```bash
# 使用示例活动ID测试
curl "http://localhost:8000/screen/test-activity/timer"
```

### 前端集成测试
1. 启动前端开发服务器
2. 访问大屏幕页面
3. 选择 "Timer" 模式
4. 验证计时器配置是否正确加载

## 注意事项

1. **API状态**: 该API当前标记为"待后端实现"，前端使用模拟数据
2. **数据验证**: 前端应验证API返回的数据结构完整性
3. **性能考虑**: 计时器配置数据相对稳定，适合前端缓存
4. **时区处理**: 确保服务器和客户端时区设置一致
5. **并发控制**: 多用户同时访问时注意数据一致性

---

*本文档由系统自动生成，最后更新时间: 2025年10月22日*</content>
<parameter name="filePath">d:\Code\motion-vote\backend\DebateTimer_API_Demo.md