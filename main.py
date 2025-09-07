from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig
from astrbot.api.all import *
import tempfile
import os
import asyncio
import time
import re
import sys
import json
import base64
import aiohttp
import random
from webdav3.client import Client
from datetime import datetime
from typing import List, Dict, Any

@register("WebDAV图库", "Yuki Soffd", "提供图片上传和随机图片功能，通过WebDAV存储图片", "1.0")
class WebDAVGalleryPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.temp_dir = os.path.join(tempfile.gettempdir(), "astrbot_webdav_gallery")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 从配置中读取WebDAV参数
        self.webdav_url = config.get("webdav_url", "")
        self.webdav_username = config.get("webdav_username", "")
        self.webdav_password = config.get("webdav_password", "")
        self.base_path = config.get("base_path", "/astrbot_gallery/")
        
        # 初始化WebDAV客户端
        self.webdav_client = None
        self.init_webdav_client()
        
        # 图片元数据文件
        self.metadata_file = "gallery_metadata.json"
        
        # 确保基础路径存在
        self.ensure_base_path()

    def init_webdav_client(self):
        """初始化WebDAV客户端"""
        if not all([self.webdav_url, self.webdav_username, self.webdav_password]):
            logger.warning("WebDAV配置不完整，请检查配置文件！")
            return
            
        options = {
            'webdav_hostname': self.webdav_url,
            'webdav_login': self.webdav_username,
            'webdav_password': self.webdav_password
        }
        
        try:
            self.webdav_client = Client(options)
            # 测试连接
            self.webdav_client.list()
            logger.info("WebDAV连接成功")
        except Exception as e:
            logger.error(f"WebDAV连接失败: {str(e)}")
            self.webdav_client = None

    def ensure_base_path(self):
        """确保基础路径存在"""
        if self.webdav_client and not self.webdav_client.check(self.base_path):
            try:
                self.webdav_client.mkdir(self.base_path)
                logger.info(f"创建基础路径: {self.base_path}")
            except Exception as e:
                logger.error(f"创建基础路径失败: {str(e)}")

    async def download_image(self, event: AstrMessageEvent, file_id: str) -> str:
        """
        下载图片到临时目录
        返回临时文件路径
        """
        try:
            image_obj = next(
                (msg for msg in event.get_messages() 
                 if isinstance(msg, Image) and msg.file == file_id),  # 修复：直接使用 Image
                None
            )
        
            if not image_obj:
                return ""
        
            # 尝试直接获取文件路径
            file_path = await image_obj.convert_to_file_path()
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    data = f.read()
            else:
                # 通过API获取图片
                client = event.bot
                result = await client.api.call_action("get_image", file_id=file_id)
                file_path = result.get("file")
                if not file_path:
                    return ""
                with open(file_path, "rb") as f:
                    data = f.read()
        
            # 创建插件的临时文件
            temp_path = os.path.join(self.temp_dir, f"gallery_{int(time.time())}_{random.randint(1000, 9999)}.jpg")
            with open(temp_path, "wb") as f:
                f.write(data)
            
            return temp_path
        
        except Exception as e:
            logger.error(f"图片下载失败: {str(e)}", exc_info=True)
            return ""

    async def upload_to_webdav(self, local_path: str, description: str = "") -> bool:
        """上传图片到WebDAV并更新元数据"""
        if not self.webdav_client:
            return False
            
        try:
            # 生成唯一文件名
            timestamp = int(time.time())
            random_str = random.randint(1000, 9999)
            filename = f"image_{timestamp}_{random_str}.jpg"
            remote_path = os.path.join(self.base_path, filename).replace("\\", "/")
            
            # 上传图片
            self.webdav_client.upload(remote_path, local_path)
            
            # 更新元数据
            metadata = await self.get_metadata()
            metadata.append({
                "filename": filename,
                "remote_path": remote_path,
                "description": description,
                "upload_time": datetime.now().isoformat()
            })
            
            # 保存元数据
            metadata_path = os.path.join(self.temp_dir, self.metadata_file)
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                
            # 上传元数据文件
            remote_metadata_path = os.path.join(self.base_path, self.metadata_file).replace("\\", "/")
            self.webdav_client.upload(remote_metadata_path, metadata_path)
            
            # 清理临时元数据文件
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
                
            return True
            
        except Exception as e:
            logger.error(f"上传到WebDAV失败: {str(e)}")
            return False

    async def get_metadata(self) -> List[Dict[str, Any]]:
        """获取图片元数据"""
        if not self.webdav_client:
            return []
            
        try:
            remote_metadata_path = os.path.join(self.base_path, self.metadata_file).replace("\\", "/")
            local_metadata_path = os.path.join(self.temp_dir, self.metadata_file)
            
            # 下载元数据文件
            if self.webdav_client.check(remote_metadata_path):
                self.webdav_client.download(remote_metadata_path, local_metadata_path)
                
                with open(local_metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    
                # 清理临时文件
                if os.path.exists(local_metadata_path):
                    os.remove(local_metadata_path)
                    
                return metadata
            else:
                return []
                
        except Exception as e:
            logger.error(f"获取元数据失败: {str(e)}")
            return []

    async def get_random_image(self) -> Dict[str, Any]:
        """随机获取一张图片信息"""
        metadata = await self.get_metadata()
        if not metadata:
            return None
            
        return random.choice(metadata)

    async def cleanup_files(self, paths: list):
        """异步清理临时文件，支持多个文件路径"""
        await asyncio.sleep(3)
        for path in paths:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                    logger.info(f"已成功删除文件: {path}")
                except Exception as e:
                    logger.warning(f"清理临时文件失败 {path}: {str(e)}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("上传图片")
    async def upload_image(self, event: AstrMessageEvent):
        """上传图片到图库：/上传图片 [描述] [图片]"""
        messages = event.get_messages()
        images = [msg for msg in messages if isinstance(msg, Image)]
        
        if not images:
            yield event.plain_result("请发送一张图片")
            return
        
        # 获取描述文本
        description = ""
        text_messages = [msg for msg in messages if isinstance(msg, Plain)]
        
        if text_messages:
            # 获取完整的文本内容
            full_text = text_messages[0].text.strip()
            
            # 只提取命令后面的部分作为描述
            if full_text.startswith("/上传图片"):
                # 移除命令部分并去除前后空格
                description_part = full_text[5:].strip()
                
                # 只有当有实际内容时才作为描述
                if description_part and description_part != "上传图片":
                    description = description_part
        
        try:
            # 下载图片
            file_id = images[0].file
            temp_path = await self.download_image(event, file_id)
            if not temp_path:
                yield event.plain_result("图片下载失败")
                return
                
            # 上传到WebDAV
            success = await self.upload_to_webdav(temp_path, description)
            
            # 清理临时文件
            if os.path.exists(temp_path):
                asyncio.create_task(self.cleanup_files([temp_path]))
            
            if success:
                yield event.plain_result("图片上传成功")
            else:
                yield event.plain_result("图片上传失败，请检查WebDAV配置")
        
        except Exception as e:
            logger.error(f"图片上传处理失败: {str(e)}", exc_info=True)
            yield event.plain_result(f"图片上传失败: {str(e)}")

    @filter.command("随机图片")
    async def random_image(self, event: AstrMessageEvent):
        """随机获取一张图片：/随机图片"""
        if not self.webdav_client:
            yield event.plain_result("WebDAV未正确配置")
            return
            
        try:
            # 获取随机图片信息
            image_info = await self.get_random_image()
            if not image_info:
                yield event.plain_result("图库中没有图片")
                return
                
            # 下载图片到临时文件
            temp_path = os.path.join(self.temp_dir, f"temp_{int(time.time())}.jpg")
            self.webdav_client.download(image_info["remote_path"], temp_path)
            
            # 构建回复消息
            chain = []
            if image_info.get("description"):
                chain.append(Plain(text=f"图片描述: {image_info['description']}"))
            
            chain.append(Image.fromFileSystem(temp_path))
            
            # 安排清理临时文件
            asyncio.create_task(self.cleanup_files([temp_path]))
            
            yield event.chain_result(chain)
            
        except Exception as e:
            logger.error(f"随机图片获取失败: {str(e)}", exc_info=True)
            yield event.plain_result(f"获取图片失败: {str(e)}")

    async def terminate(self):
        """插件销毁时清理资源"""
        logger.info("WebDAV图库插件已卸载")