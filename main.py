from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Record, Plain, Image
from pathlib import Path
from openai import OpenAI
import logging
import re
import aiohttp
import json
import random

# 注册插件的装饰器
@register("VITSPlugin", "第九位魔神/Chris95743", "语音合成插件", "1.3.0")
class VITSPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.api_url = config.get('url', '')  # 提取 API URL
        self.api_key = config.get('apikey', '')  # 提取 API Key
        self.api_name = config.get('name', '')  # 提取 模型 名称
        self.api_voice = config.get('voice', '')  # 提取角色名称
        self.skip_tts_keywords = config.get('skip_tts_keywords', [])  # 跳过TTS的关键词
        self.tts_probability = config.get('tts_probability', 100)  # TTS转换概率
        self.enabled = False  # 初始化插件开关为关闭状态

    @filter.command("vits", priority=1)
    async def vits(self, event: AstrMessageEvent):
        """启用/禁用语音插件"""
        # 兼容不同平台获取用户名
        if hasattr(event, 'get_sender_name'):
            user_name = event.get_sender_name()
        elif hasattr(event, 'get_user_id'):
            user_name = str(event.get_user_id())
        else:
            user_name = "用户"
            
        self.enabled = not self.enabled
        if self.enabled:
            yield event.plain_result(f"启用语音插件, {user_name}")
        else:
            yield event.plain_result(f"禁用语音插件, {user_name}")

    @filter.command("voices", priority=1)
    async def vits_voices(self, event: AstrMessageEvent):
        """查看所有可用的音色列表"""
        try:
            # 获取用户自定义音色列表
            custom_voices = []
            try:
                url = f"{self.api_url}/audio/voice/list"
                headers = {"Authorization": f"Bearer {self.api_key}"}
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            response_text = await response.text()
                            voice_list = json.loads(response_text)
                            
                            # 尝试多种可能的数据结构
                            if voice_list and isinstance(voice_list, dict):
                                if 'data' in voice_list:
                                    custom_voices = voice_list['data']
                                elif 'result' in voice_list:
                                    custom_voices = voice_list['result']
                                elif 'voices' in voice_list:
                                    custom_voices = voice_list['voices']
                                elif 'items' in voice_list:
                                    custom_voices = voice_list['items']
                                elif isinstance(voice_list, list):
                                    custom_voices = [voice_list] if voice_list else []
                                else:
                                    custom_voices = [voice_list] if voice_list else []
                            elif isinstance(voice_list, list):
                                custom_voices = voice_list
                                
            except Exception as e:
                logging.warning(f"获取自定义音色列表失败: {e}")
            
            # 构建音色信息
            voice_info = "可用音色列表\n"
            voice_info += "=" * 20 + "\n\n"
            
            # 系统预置音色
            voice_info += "系统预置音色：\n"
            system_voices = [
                ("alex", "沉稳男声"),
                ("benjamin", "低沉男声"), 
                ("charles", "磁性男声"),
                ("david", "欢快男声"),
                ("anna", "沉稳女声"),
                ("bella", "激情女声"),
                ("claire", "温柔女声"),
                ("diana", "欢快女声")
            ]
            
            for voice_id, voice_desc in system_voices:
                voice_info += f"• {voice_id} - {voice_desc}\n"
                voice_info += f"  {self.api_name}:{voice_id}\n\n"
            
            # 用户自定义音色
            if custom_voices and len(custom_voices) > 0:
                voice_info += "用户自定义音色：\n"
                for voice in custom_voices:
                    if isinstance(voice, dict):
                        voice_name = voice.get('name', voice.get('customName', '未知'))
                        voice_uri = voice.get('uri', voice.get('id', '未知'))
                        
                        voice_info += f"• {voice_name}\n"
                        voice_info += f"  {voice_uri}\n\n"
                    else:
                        voice_info += f"• {str(voice)}\n\n"
            else:
                voice_info += "用户自定义音色：暂无\n"
                voice_info += "如需使用自定义音色，请先在硅基流动平台上传音频文件\n\n"
            
            voice_info += "使用说明：\n"
            voice_info += "1. 系统预置音色：在配置中设置 voice 为 '模型名:音色名'\n"
            voice_info += "2. 自定义音色：在配置中设置 voice 为完整的 URI\n"
            voice_info += f"3. 当前配置：模型={self.api_name}, 音色={self.api_voice}\n"
            voice_info += "4. 使用/voice <音色名> 快速切换预置/自定义音色\n"
            
            yield event.plain_result(voice_info)
            
        except Exception as e:
            logging.error(f"获取音色列表失败: {e}")
            yield event.plain_result(f"获取音色列表失败：{str(e)}")

    @filter.command("voice", priority=1)
    async def change_voice(self, event: AstrMessageEvent):
        """快速切换音色"""
        # 获取命令参数
        message_text = event.get_message_str().strip()
        parts = message_text.split()
        
        if len(parts) < 2:
            # 显示当前音色和使用说明
            current_voice = self.api_voice if self.api_voice else "未设置"
            help_text = f"当前音色：{current_voice}\n\n"
            help_text += "使用方法：/voice <音色名>\n\n"
            help_text += "可用的系统预置音色：\n"
            help_text += "• alex - 沉稳男声\n"
            help_text += "• benjamin - 低沉男声\n" 
            help_text += "• charles - 磁性男声\n"
            help_text += "• david - 欢快男声\n"
            help_text += "• anna - 沉稳女声\n"
            help_text += "• bella - 激情女声\n"
            help_text += "• claire - 温柔女声\n"
            help_text += "• diana - 欢快女声\n\n"
            help_text += "示例：/voice alex"
            yield event.plain_result(help_text)
            return
        
        voice_name = parts[1]  # 保持原始大小写，因为自定义音色可能区分大小写
        voice_name_lower = voice_name.lower()
        
        # 预定义的系统音色
        system_voices = {
            "alex": "沉稳男声",
            "benjamin": "低沉男声", 
            "charles": "磁性男声",
            "david": "欢快男声",
            "anna": "沉稳女声",
            "bella": "激情女声",
            "claire": "温柔女声",
            "diana": "欢快女声"
        }
        
        # 获取用户自定义音色列表
        custom_voices = {}
        try:
            url = f"{self.api_url}/audio/voice/list"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        response_text = await response.text()
                        voice_list = json.loads(response_text)
                        
                        # 解析自定义音色数据
                        if voice_list and isinstance(voice_list, dict):
                            if 'data' in voice_list:
                                voices_data = voice_list['data']
                            elif 'result' in voice_list:
                                voices_data = voice_list['result']
                            elif 'voices' in voice_list:
                                voices_data = voice_list['voices']
                            elif 'items' in voice_list:
                                voices_data = voice_list['items']
                            else:
                                voices_data = voice_list if isinstance(voice_list, list) else []
                        elif isinstance(voice_list, list):
                            voices_data = voice_list
                        else:
                            voices_data = []
                        
                        # 构建自定义音色字典
                        for voice in voices_data:
                            if isinstance(voice, dict):
                                voice_name_key = voice.get('name', voice.get('customName', ''))
                                voice_uri = voice.get('uri', voice.get('id', ''))
                                if voice_name_key and voice_uri:
                                    custom_voices[voice_name_key] = voice_uri
        except Exception as e:
            logging.warning(f"获取自定义音色列表失败: {e}")
        
        # 检查是否是系统预置音色
        if voice_name_lower in system_voices:
            # 构建新的音色配置
            new_voice = f"{self.api_name}:{voice_name_lower}"
            self.api_voice = new_voice
            
            voice_desc = system_voices[voice_name_lower]
            yield event.plain_result(f"已切换到系统音色：{voice_name_lower} ({voice_desc})\n配置：{new_voice}")
        
        # 检查是否是自定义音色
        elif voice_name in custom_voices:
            # 使用自定义音色的完整URI
            new_voice = custom_voices[voice_name]
            self.api_voice = new_voice
            
            yield event.plain_result(f"已切换到自定义音色：{voice_name}\n配置：{new_voice}")
        
        else:
            # 不支持的音色
            all_system_voices = ", ".join(system_voices.keys())
            all_custom_voices = ", ".join(custom_voices.keys()) if custom_voices else "无"
            
            error_msg = f"不支持的音色：{voice_name}\n\n"
            error_msg += f"可用系统音色：{all_system_voices}\n"
            error_msg += f"可用自定义音色：{all_custom_voices}"
            
            yield event.plain_result(error_msg)

    @filter.command("vits%", priority=1)
    async def set_tts_probability(self, event: AstrMessageEvent):
        """设置TTS转换概率"""
        # 获取命令参数
        message_text = event.get_message_str().strip()
        parts = message_text.split()
        
        if len(parts) < 2:
            # 显示当前概率设置
            yield event.plain_result(f"当前TTS转换概率：{self.tts_probability}%\n\n使用方法：/vits% <概率值>\n\n示例：\n/vits% 50  # 设置50%概率\n/vits% 100 # 设置100%概率（每次都转换）\n/vits% 0   # 设置0%概率（从不转换）")
            return
        
        try:
            new_probability = int(parts[1])
            
            # 验证概率值范围
            if new_probability < 0 or new_probability > 100:
                yield event.plain_result("概率值必须在0-100之间！\n\n0表示从不转换，100表示每次都转换。")
                return
            
            # 更新概率设置
            self.tts_probability = new_probability
            
            if new_probability == 0:
                yield event.plain_result("已设置TTS转换概率为0%，将不会进行语音转换。")
            elif new_probability == 100:
                yield event.plain_result("已设置TTS转换概率为100%，将每次都进行语音转换。")
            else:
                yield event.plain_result(f"已设置TTS转换概率为{new_probability}%，大约{new_probability}%的消息会转换为语音。")
                
        except ValueError:
            yield event.plain_result("请输入有效的数字！\n\n示例：/vits% 50")

    async def _create_speech_request(self, plain_text: str, output_audio_path: Path):
        """创建语音合成请求"""
        try:
            client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_url
            )

            # 判断音色类型并调用相应API
            if self.api_voice.startswith('speech:'):
                # 用户自定义音色
                with client.audio.speech.with_streaming_response.create(
                        model=self.api_name,
                        voice=self.api_voice,  # 直接使用自定义音色URI
                        input=plain_text,
                        response_format="wav"
                ) as response:
                    response.stream_to_file(output_audio_path)
                    return True
            elif self.api_voice and ':' in self.api_voice:
                # 系统预置音色
                with client.audio.speech.with_streaming_response.create(
                        model=self.api_name,
                        voice=self.api_voice,
                        input=plain_text,
                        response_format="wav"
                ) as response:
                    response.stream_to_file(output_audio_path)
                    return True
            else:
                # 音色配置错误
                raise Exception("音色配置错误，请检查voice字段配置")
                
        except Exception as e:
            logging.error(f"语音转换失败: {e}")
            raise e

    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        # 插件是否启用
        if not self.enabled:
            return

        # 获取事件结果
        result = event.get_result()
        # 初始化plain_text变量
        plain_text = ""
        chain = result.chain

        #遍历组件
        for comp in result.chain:
            if isinstance(comp, Image):  # 检测是否有Image组件
                return  # 静默退出，不添加错误提示
            if isinstance(comp, Plain):
                cleaned_text = re.sub(r'[()《》#%^&*+-_{}]', '', comp.text)
                plain_text += cleaned_text

        # 检测是否包含跳过TTS的关键词
        for keyword in self.skip_tts_keywords:
            if keyword.lower() in plain_text.lower():
                return  # 包含关键词时静默退出，不进行语音转换

        # 概率检测：根据设置的概率决定是否进行TTS转换
        if self.tts_probability < 100:
            # 生成1-100之间的随机数
            random_num = random.randint(1, 100)
            if random_num > self.tts_probability:
                return  # 不满足概率条件，静默退出不进行语音转换

        # 初始化输出音频路径
        output_audio_path = Path(__file__).parent / "miao.wav"

        try:
            success = await self._create_speech_request(plain_text, output_audio_path)
            if success:
                result.chain = [Record(file=str(output_audio_path))]
        except Exception as e:
            logging.error(f"语音转换失败: {e}")
            chain.append(Plain(f"语音转换失败：{str(e)}"))
