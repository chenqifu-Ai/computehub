package com.chargecloud.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.chargecloud.entity.User;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface UserMapper extends BaseMapper<User> {
}