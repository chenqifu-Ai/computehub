package com.chargecloud.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.chargecloud.entity.Order;
import com.chargecloud.mapper.OrderMapper;
import com.chargecloud.service.OrderService;
import org.springframework.stereotype.Service;

@Service
public class OrderServiceImpl extends ServiceImpl<OrderMapper, Order> implements OrderService {
}