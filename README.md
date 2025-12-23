# auto_subtitle

auto_subtitle 是一个实时音频字幕生成工具，能够将电脑播放的音频实时转录并翻译成目标语言，在屏幕上显示字幕。

<img width="2560" height="454" alt="image" src="https://github.com/user-attachments/assets/eddb7e4e-3a54-4c16-875d-c050b24b1c93" />

https://github.com/user-attachments/assets/812a98eb-f1b8-4df7-85e8-46bd92869157

## 环境要求
- Windows 10/11 (需要 WASAPI 支持)

## 使用方法
### 配置说明
使用前需要先配置模型, 程序配置文件为根目录下 `.config.yaml`，示例如下：
```yaml
translator:
#  api_key: 模型 API 密钥
  model: qwen 
  source_language: auto
  target_language: zh

subtitle:
  font_size: 24
  suspend_time: 5
```
**translator.model** 配置翻译模型\
当前已接入模型

| 枚举 | 模型 | 评价 |
| --- | --- | --- |
| qwen | qwen3-livetranslate-flash-realtime | 翻译质量较好，有免费quota，收费部分价格较贵 |
|gummy | gummy-realtime-v1 | 效果一般，有免费quota，价格便宜 |
有其他推荐的模型需求可提issue，作者会根据情况添加

**translator.api_key** 配置模型 API 密钥\
目前已接入模型均为阿里百炼平台模型,可遵循文档获取 [获取API Key](https://bailian.console.aliyun.com/cn-beijing/?utm_content=se_1021228171&gclid=EAIaIQobChMIq4qKw_vVkgMVOB6DAx1wQxg7EAAYASAAEgK3jPD_BwE&tab=api#/api/?type=model&url=2712195)

### 操作界面
<img width="813" height="319" alt="main" src="https://github.com/user-attachments/assets/84f0c569-0ffd-43f4-b157-7255f7fc839b" />

   1. **开始/停止**：点击界面左侧的播放/暂停按钮开始/停止字幕生成
   2. **选择语言**：在界面右侧选择源语言和目标语言，源语言默认auto，可自动识别语言类型\
<img width="175" height="60" alt="subtitle_btn" src="https://github.com/user-attachments/assets/0cbdfda1-2ab3-480f-a00a-317069667087" />
   3. **拖动字幕**：鼠标拖动`✥`按钮，可以调整字幕窗口位置
   3. **隐藏字幕**：点击`隐藏`按钮可以切换字幕窗口的显示状态
