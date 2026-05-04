#!/bin/bash
# 使用设备现有RSA密钥进行连接

echo "🔧 使用现有RSA密钥方案"
echo "========================="

# 从设备获取RSA公钥（通过其他方式）
# 由于密码认证失败，我们需要 alternative 方法

echo "📋 设备上的RSA公钥内容:"
echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDOR1fUhs7dnGQTtxDD6ESTCYS6f+UHqyevhGbEJOnT7SODI15IcOyxuXFaL00xjzdDG9Cui2u5NxBDHp2l1XlDM94UoFVQmDn36tOZl3Jp4jRfeDWTC3sEFRT/cizHIuJABwpNOxRPUWLy62cqSnoQ500NhHvMZiXXtvaJ6FiEla6L82DPMMTTpl5yJU4EE+e7GzW/XoOwQePsBIN+i+2VN25GdWkjxnvntQCGr/oUERBCFNNQRFwOl8ryBj+GlHHi70MQ5sHk3qjUsHI8pkx7wtRgs9KdvEW5PKFwT47UbHweVwtHJRj2SE9Ffu4FHrzlWqXmZbhfC/8jwF/ysJIF0HJb3jA1uTZMk+rMGj/hhiunSsGZWClLcQZRVJBXr0极jCEEKu9XQJ85XCoRyjnZNXmDYqiYhSajJ67Iid2CbqiBnJOsJyzi1IBJ2PT6cm4极X05a51VyugP6n3zSlP69LdzEVZ4BGa1nDhmNGerP6K4F2SrI9EqtQ0e0fmGNfoCXeYGzUP2/s0oL+vfCTvzPHJX53+yQRyVi5Xw+sMfHnNA2VBymA/S1FY58Ejs5Ro7dOY4azSleBJdBKv1dYUvR1eo+IAf2W5DHxI22a1b41nJA+ZpRKCoMllbc7极T6Yj5Av极tAku8gcyHboUYrxPboW4sG+xjwWxtaBZkfnUHf0w6lYMQ== u0_a207@localhost"

echo ""
echo "🚀 建议方案:"
echo "1. 手动将设备的RSA私钥复制到本地"
echo "2. 或者使用设备的RSA密钥重新配置"
echo "3. 确认正确的用户名和密码"

echo ""
echo "💡 设备信息:"
echo "   用户名: u0_a207"
echo "   RSA密钥: ~/.ssh/id_rsa"
echo "   目录权限: 正确 (700/.ssh, 600/authorized_keys)"

echo "========================="