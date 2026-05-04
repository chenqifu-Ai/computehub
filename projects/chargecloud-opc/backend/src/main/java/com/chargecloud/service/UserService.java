package com.chargecloud.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.chargecloud.entity.User;

public interface UserService extends IService<User> {
    User getByPhone(String phone);
}