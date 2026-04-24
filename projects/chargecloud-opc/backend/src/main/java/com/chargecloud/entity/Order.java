package com.chargecloud.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("charging_order")
public class Order {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String orderNo;
    private Long userId;
    private Long pileId;
    private Long stationId;
    private Long operatorId;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private Integer duration;
    private Integer startSoc;
    private Integer endSoc;
    private BigDecimal energy;
    private BigDecimal electricityFee;
    private BigDecimal serviceFee;
    private BigDecimal parkingFee;
    private BigDecimal totalAmount;
    private Integer payMethod;
    private Integer status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}