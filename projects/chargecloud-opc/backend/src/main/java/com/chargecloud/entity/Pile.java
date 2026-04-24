package com.chargecloud.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("charging_pile")
public class Pile {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long stationId;
    private String code;
    private String name;
    private Integer type;
    private BigDecimal power;
    private BigDecimal voltage;
    private BigDecimal current;
    private BigDecimal price;
    private BigDecimal serviceFee;
    private Integer status;
    private Integer connectorType;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}