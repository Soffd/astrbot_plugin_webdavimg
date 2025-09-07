# astrbot_plugin_webdavimg
## 简介
WebDAV 图库插件是一个基于 AstrBot 框架的插件，提供图片上传和随机图片功能，通过 WebDAV 服务存储图片。
## 功能特点
* 支持上传图片到 WebDAV 服务器，并可添加描述信息
* 支持从 WebDAV 服务器随机获取一张图片
* 自动管理图片元数据和临时文件
* 仅管理员可上传图片，普通用户可获取随机图片。**为防止有人上传不适合存进网盘里的图片，将上传设置为了仅管理可用，如果你有需求可以自行修改放开上传权限**
## 配置说明
使用前需要在 AstrBot 配置文件中添加以下 WebDAV 相关配置：
```json
{
  "webdav_url": "https://example.com/webdav",
  "webdav_username": "your-username",
  "webdav_password": "your-password",
  "base_path": "/astrbot_gallery/"
}
```
配置项说明：
* `webdav_url`: WebDAV 服务器地址
* `webdav_username`: WebDAV 登录用户名
* `webdav_password`: WebDAV 登录密码
* `base_path`: 存储图片的基础路径，默认为`/astrbot_gallery/`
## 使用方法
* 指令：`上传图片` [描述] [图片]
* 指令：`随机图片`
说明：描述为可选参数，用于记录图片信息，指令与图片在同一消息中。如果上传时未添加描述，那随机发送到这张图时也不会发送描述文本信息
## 注意事项
* 确保 WebDAV 服务器配置正确且可访问，可在控制台查看相关报告
* 上传图片大小受 WebDAV 服务器和机器人的服务器限制
* 请确保你的服务器和网盘有足够的存储空间用于文件处理
* 保持网络畅通

WabDAV服务可以使用：`坚果云`，`123云盘`，`Cloudreve`等支持WebDAV协议的网盘或自建网盘
