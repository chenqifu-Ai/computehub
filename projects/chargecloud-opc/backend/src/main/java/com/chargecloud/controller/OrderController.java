package com.chargecloud.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.chargecloud.common.Result;
import com.chargecloud.entity.Order;
import com.chargecloud.service.OrderService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/orders")
public class OrderController {

    @Autowired
    private OrderService orderService;

    @GetMapping
    public Result<Page<Order>> list(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "20") Integer size,
            @RequestParam(required = false) Long userId,
            @RequestParam(required = false) Long stationId,
            @RequestParam(required = false) Integer status) {
        Page<Order> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<Order> wrapper = new LambdaQueryWrapper<>();
        if (userId != null) wrapper.eq(Order::getUserId, userId);
        if (stationId != null) wrapper.eq(Order::getStationId, stationId);
        if (status != null) wrapper.eq(Order::getStatus, status);
        wrapper.orderByDesc(Order::getCreatedAt);
        return Result.success(orderService.page(pageParam, wrapper));
    }

    @PostMapping
    public Result<Order> create(@RequestBody Order order) {
        order.setOrderNo("C" + System.currentTimeMillis());
        order.setStatus(1);
        order.setStartTime(LocalDateTime.now());
        order.setCreatedAt(LocalDateTime.now());
        orderService.save(order);
        return Result.success(order);
    }

    @GetMapping("/{orderNo}")
    public Result<Order> getByOrderNo(@PathVariable String orderNo) {
        return Result.success(orderService.getOne(
            new LambdaQueryWrapper<Order>().eq(Order::getOrderNo, orderNo)));
    }

    @PutMapping("/{orderNo}/end")
    public Result<Order> endOrder(@PathVariable String orderNo) {
        Order order = orderService.getOne(
            new LambdaQueryWrapper<Order>().eq(Order::getOrderNo, orderNo));
        if (order != null) {
            order.setStatus(2);
            order.setEndTime(LocalDateTime.now());
            orderService.updateById(order);
        }
        return Result.success(order);
    }

    @GetMapping("/stats")
    public Result<Object> stats(@RequestParam(required = false) Long stationId) {
        // TODO: 实现统计逻辑
        return Result.success(null);
    }
}